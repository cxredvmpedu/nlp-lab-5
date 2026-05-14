import pandas as pd
import matplotlib.pyplot as plt


class Analyzer:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def get_comparative_stats(self) -> pd.DataFrame:
        # Групуємо за категорією та рахуємо середню вартість за кв.м.
        stats = self.df.groupby('Category')[
            'Price_per_sqm'].mean().reset_index()
        stats = stats.rename(
            columns={'Price_per_sqm': 'Average_Price_per_Sqm'})
        stats['Average_Price_per_Sqm'] = stats['Average_Price_per_Sqm'].round(
            2)
        return stats

    def plot_bar_chart(self, stats: pd.DataFrame):
        plt.figure(figsize=(10, 6))

        # Побудова стовпчастої діаграми
        bars = plt.bar(stats['Category'], stats['Average_Price_per_Sqm'], color=[
                       '#3498db', '#2ecc71', '#e74c3c'])

        # Налаштування графіка
        plt.title(
            'Середня вартість 1 м² нерухомості в Києві за категоріями', fontsize=14, pad=15)
        plt.xlabel('Категорія нерухомості', fontsize=12)
        plt.ylabel('Ціна за 1 м² (USD)', fontsize=12)
        plt.grid(axis='y', linestyle='--', alpha=0.7)

        # Додавання значень над стовпцями
        for bar in bars:
            yval = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2, yval + 10,
                     f"${yval}", ha='center', va='bottom', fontsize=11, fontweight='bold')

        plt.tight_layout()
        plt.savefig('comparative_analysis.png', dpi=300)
        plt.show()
