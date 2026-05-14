import csv
import pandas as pd


class Storage:
    def __init__(self, filename: str = 'real_estate_kyiv.csv'):
        self.filename = filename

    def save_to_csv(self, data):
        with open(self.filename, mode='w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(
                ['Platform', 'Category', 'Price_USD', 'Area_sqm', 'Link'])
            for item in data:
                writer.writerow([item.platform, item.category,
                                item.price_usd, item.area_sqm, item.link])
        print(f"\nДані успішно збережено у файл: {self.filename}")

    def load_and_process(self) -> pd.DataFrame:
        df = pd.read_csv(self.filename)
        # Рахуємо вартість за квадратний метр
        df['Price_per_sqm'] = df['Price_USD'] / df['Area_sqm']
        return df
