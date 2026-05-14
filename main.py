import logging
import json
import os
import pandas as pd
import dataclasses

from storage import Storage
from analyzer import Analyzer
from scraper import OLXScraper, DIMRIAScrapper


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # 1. Визначення джерел
    sources = pd.read_csv("sources.csv")

    # 2. Ініціалізація компонентів
    olx_scraper = OLXScraper()
    dimria_scraper = DIMRIAScrapper()
    storage = Storage()

    all_properties = []

    # 3. Збір даних
    logging.info("Збір даних...")
    for source in sources.to_dict("records"):
        platform = source["platform"]
        category = source["category"]
        url = source["url"]

        if platform == "OLX":
            scraper = olx_scraper
        elif platform == "DOM.RIA":
            scraper = dimria_scraper
        else:
            continue

        scraped_ads = scraper.scrape_category(url, limit=5)

        if not scraped_ads:
            logging.warning(f"Немає даних для збереження з {platform}/{category}")
            continue

        # Підготовка директорії
        save_dir = os.path.join("data", category, platform)
        os.makedirs(save_dir, exist_ok=True)

        # Збереження сирих JSON
        json_filepath = os.path.join(save_dir, "cleaned_pages.json")
        json_data = [ad.json() for ad in scraped_ads]
        with open(json_filepath, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=4)

        # Конвертація в PropertyItem
        local_properties = []
        for ad in scraped_ads:
            prop_item = ad.to_property_item(category)
            if prop_item:
                local_properties.append(prop_item)
                all_properties.append(prop_item)

        # Збереження в цільову папку
        prop_filepath = os.path.join(save_dir, "properties.csv")
        if local_properties:
            df_local = pd.DataFrame([dataclasses.asdict(p) for p in local_properties])
            df_local.to_csv(prop_filepath, index=False, encoding="utf-8")

        logging.info(
            f"Успішно збережено {len(scraped_ads)} сирих сторінок та {
                len(local_properties)
            } PropertyItems у {save_dir}\n"
        )

    if not all_properties:
        logging.error("Жодного об'єкта не було успішно розпарсено.")
        return

    # 4. Збереження у файл загальної бази
    storage.save_to_csv(all_properties)

    # 5. Обробка та Аналіз
    logging.info("Проведення порівняльного аналізу...")
    df = storage.load_and_process()
    proc = Analyzer(df)

    stats = proc.get_comparative_stats()
    print("\nРезультати аналізу (Середня ціна за м²):")
    print(stats.to_string(index=False))

    # 6. Візуалізація
    logging.info("Генерація графіка...")
    proc.plot_bar_chart(stats)


if __name__ == "__main__":
    main()
