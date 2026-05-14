from dataclasses import dataclass


@dataclass
class PropertyItem:
    platform: str
    category: str
    price_usd: float
    area_sqm: float
    link: str
