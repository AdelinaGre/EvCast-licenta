import matplotlib.pyplot as plt
import pandas as pd

def plot_features(df, x_feature, y_feature, x_label=None, y_label=None, title=None, show=True):
    """
    Creează un scatter plot pentru orice două coloane din DataFrame.
    - df: DataFrame-ul cu datele
    - x_feature: numele coloanei pentru axa X
    - y_feature: numele coloanei pentru axa Y
    - x_label, y_label, title: etichete opționale
    - show: dacă True, afișează graficul; altfel, îl salvează ca PNG
    """
    if x_feature not in df.columns or y_feature not in df.columns:
        raise ValueError(f"Coloanele {x_feature} și/sau {y_feature} nu există în DataFrame.")
    plt.figure(figsize=(8,5))
    plt.scatter(df[x_feature], df[y_feature])
    plt.xlabel(x_label if x_label else x_feature)
    plt.ylabel(y_label if y_label else y_feature)
    plt.title(title if title else f"{y_feature} vs {x_feature}")
    plt.grid(True)
    if show:
        plt.show()
    else:
        plt.savefig(f"{y_feature}_vs_{x_feature}.png")

# Exemplu de utilizare (doar pentru test):
if __name__ == "__main__":
    # Exemplu de date
    data = {
        'energy_consumed': [10, 20, 30, 40, 50],
        'durata_estimata_ore': [1, 2, 2.5, 3, 4],
        'charging_rate': [5, 7, 8, 10, 12]
    }
    df = pd.DataFrame(data)
    plot_features(df, 'energy_consumed', 'durata_estimata_ore', x_label='Energy Consumed (kWh)', y_label='Durata Estimată (ore)') 