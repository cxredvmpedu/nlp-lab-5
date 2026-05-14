import time
import logging
import requests
import re
from bs4 import BeautifulSoup
from typing import List, Optional, Tuple
from dataclasses import dataclass

from model import PropertyItem


def parse_price(price_str: str) -> float:
    if not price_str:
        return 0.0
    clean_str = re.sub(r"[^\d]", "", price_str)
    return float(clean_str) if clean_str else 0.0


def parse_area(params: str) -> float:
    # Шукаємо число, після якого йде позначка площі
    match = re.search(r"(\d+[\.,]?\d*)\s*(кв\.м|м²|м2|м\.кв)", params)
    if match:
        val = match.group(1).replace(",", ".")
        return float(val)
    return 0.0


@dataclass
class Page:
    url: str
    soup: BeautifulSoup


class PlatformLoggerAdapter(logging.LoggerAdapter):
    """Додає назву платформи перед логом."""

    def process(self, msg, kwargs):
        return f"[{self.extra['platform']}] {msg}", kwargs


class BaseScraper:
    platform = "Base"

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        }

        base_logger = logging.getLogger(self.__class__.__name__)
        self.logger = PlatformLoggerAdapter(base_logger, {"platform": self.platform})

    def fetch_html(self, url: str) -> Optional[Page]:
        try:
            time.sleep(1)
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            return Page(url=url, soup=soup)
        except Exception as e:
            self.logger.error(f"Помилка завантаження {url}: {e}")
            return None


@dataclass
class OLXAd:
    url: str
    price: str
    params: str
    desc: str

    def json(self):
        return {
            "url": self.url,
            "price": self.price,
            "params": self.params,
            "desc": self.desc,
        }

    def to_property_item(self, category: str) -> Optional[PropertyItem]:
        price_usd = parse_price(self.price)
        area_sqm = parse_area(self.params)

        if price_usd > 0 and area_sqm > 0:
            return PropertyItem(
                platform="OLX",
                category=category,
                price_usd=price_usd,
                area_sqm=area_sqm,
                link=self.url,
            )
        return None


class OLXScraper(BaseScraper):
    platform = "OLX"

    def div_to_text(self, soup, attribute: Tuple[str, str]) -> Optional[str]:
        div = soup.find("div", {attribute[0]: attribute[1]})
        if div:
            text = div.get_text(separator="\n", strip=True)
            return text
        else:
            self.logger.warning(f"Блок {attribute[0]}={attribute[1]} не знайдено.")
            return None

    def parse(self, url: str, soup: BeautifulSoup) -> Optional[OLXAd]:
        """
        Витягує релевантний текст зі сторінки оголошення OLX.
        Повертає OLXAd.
        """
        if not soup:
            return None

        price = self.div_to_text(soup, ("data-testid", "ad-price-container"))
        params = self.div_to_text(soup, ("data-testid", "ad-parameters-container"))
        desc = self.div_to_text(soup, ("data-testid", "ad_description"))

        return OLXAd(url, price, params, desc)

    def scrape_category(self, url: str, limit: int = 5) -> List[OLXAd]:
        """
        Заходить на сторінку категорії, знаходить посилання на оголошення,
        переходить по них і повертає список OLXAd.
        """
        self.logger.info(f"Завантаження списку категорії: {url}")

        category_page = self.fetch_html(url)

        if not category_page:
            self.logger.warning("Не вдалося завантажити сторінку категорії.")
            return []

        ad_results = []

        cards = category_page.soup.find_all("div", {"data-cy": "l-card"})
        self.logger.info(
            f"Знайдено оголошень на сторінці: {len(cards)}. Обмеження збору: {limit}"
        )

        for card in cards[:limit]:
            try:
                a_tag = card.find("a", href=True)
                if not a_tag:
                    continue

                href = a_tag["href"]
                ad_url = f"https://www.olx.ua{href}" if href.startswith("/") else href

                self.logger.info(f"Завантаження сторінки оголошення: {ad_url}")

                ad_page = self.fetch_html(ad_url)

                if ad_page:
                    processed_ad = self.parse(ad_page.url, ad_page.soup)
                    if processed_ad:
                        ad_results.append(processed_ad)

            except Exception as e:
                self.logger.error(f"Помилка під час обробки посилання: {e}")

        return ad_results


@dataclass
class DIMRIAAd:
    url: str
    price: str
    address: str
    params: str
    desc: str

    def json(self):
        return {
            "url": self.url,
            "price": self.price,
            "address": self.address,
            "params": self.params,
            "desc": self.desc,
        }

    def to_property_item(self, category: str) -> Optional[PropertyItem]:
        price_usd = parse_price(self.price)
        area_sqm = parse_area(self.params)

        if price_usd > 0 and area_sqm > 0:
            return PropertyItem(
                platform="DOM.RIA",
                category=category,
                price_usd=price_usd,
                area_sqm=area_sqm,
                link=self.url,
            )
        return None


class DIMRIAScrapper(BaseScraper):
    platform = "DIMRIA"
    base_domain = "https://dom.ria.com"

    def parse_card(self, card: BeautifulSoup) -> Optional[DIMRIAAd]:
        """
        Витягує інформацію безпосередньо з HTML-картки оголошення.
        """
        try:
            # 1. URL оголошення
            link_tag = card.find("a", class_="realty-link")
            url = ""
            if link_tag and "href" in link_tag.attrs:
                href = link_tag["href"]
                url = f"{self.base_domain}{href}" if href.startswith("/") else href
            if not url:
                return None

            # 2. Ціна
            price_tag = card.find("b", class_="size22")
            price = price_tag.get_text(strip=True) if price_tag else ""

            # 3. Адреса
            # Адреса знаходиться в тезі <a> з класом size22
            address_tag = card.find("a", class_="size22")
            address = ""
            if address_tag:
                address = address_tag.get_text(strip=True)

            # 4. Параметри (кімнати, площа, сотки, поверхи)
            params_div = card.find("div", class_="realty-chars")
            params = ""
            if params_div:
                params_list = [
                    span.get_text(strip=True)
                    for span in params_div.find_all("span", class_="point-before")
                ]
                params = ", ".join(params_list)

            # 5. Опис
            desc_tag = card.find("div", class_="desc-hidden")
            desc = desc_tag.get_text(strip=True) if desc_tag else ""

            return DIMRIAAd(
                url=url, price=price, address=address, params=params, desc=desc
            )

        except Exception as e:
            self.logger.error(f"Помилка під час обробки картки оголошення: {e}")
            return None

    def scrape_category(self, url: str, limit: int = 5) -> List[DIMRIAAd]:
        """
        Завантажує сторінку категорії та парсить інформацію одразу з карток оголошень.
        """
        self.logger.info(f"Завантаження сторінки списку: {url}")

        category_page = self.fetch_html(url)

        if not category_page:
            self.logger.warning("Не вдалося завантажити сторінку списку.")
            return []

        ad_results = []

        cards = category_page.soup.find_all("section", class_="realty-item")

        self.logger.info(
            f"Знайдено карток на сторінці: {len(cards)}. Обмеження збору: {limit}"
        )

        for card in cards[:limit]:
            processed_ad = self.parse_card(card)
            if processed_ad:
                ad_results.append(processed_ad)

        return ad_results
