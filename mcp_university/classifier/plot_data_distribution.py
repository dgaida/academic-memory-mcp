"""Skript zur Visualisierung der Datenverteilung pro Klasse und Ordner (Inbox/SentItems)."""
import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def count_emails(root_dir: str) -> pd.DataFrame:
    """Zählt die .msg Dateien in Inbox und SentItems für jede Klasse.

    Args:
        root_dir: Pfad zum Wurzelverzeichnis der Daten.

    Returns:
        DataFrame mit den Spalten 'Klasse', 'Inbox', 'SentItems'.
    """
    root_path = Path(root_dir)
    data = []

    if not root_path.exists():
        print(f"Warnung: Verzeichnis {root_dir} existiert nicht.")
        return pd.DataFrame()

    # Klassenordner iterieren
    class_dirs = sorted([d for d in root_path.iterdir() if d.is_dir()])

    for class_dir in class_dirs:
        class_name = class_dir.name
        # Inbox und SentItems zählen
        inbox_count = len(list(class_dir.glob("Inbox/*.msg")))
        sent_count = len(list(class_dir.glob("SentItems/*.msg")))

        data.append({
            "Klasse": class_name,
            "Inbox": inbox_count,
            "SentItems": sent_count
        })

    return pd.DataFrame(data)

def plot_distribution(df: pd.DataFrame, title: str, output_path: Path) -> None:
    """Erstellt einen stacked bar plot und speichert ihn als PNG.

    Args:
        df: DataFrame mit den Daten.
        title: Titel des Plots.
        output_path: Pfad zum Speichern des PNGs.
    """
    if df.empty:
        print(f"Keine Daten für '{title}' zum Plotten gefunden.")
        return

    # Index für das Plotten setzen
    plot_df = df.set_index("Klasse")

    # Seaborn Style
    sns.set_theme(style="whitegrid")

    # Plot erstellen
    # Wir nutzen pandas plot für stacked bars, da es für diesen Zweck sehr einfach ist
    ax = plot_df.plot(kind='bar', stacked=True, figsize=(14, 8), color=['#4C72B0', '#DD8452'])

    plt.title(title, fontsize=18, pad=20)
    plt.xlabel("Klasse", fontsize=14, labelpad=10)
    plt.ylabel("Anzahl E-Mails", fontsize=14, labelpad=10)
    plt.xticks(rotation=45, ha='right')
    plt.legend(title="Ordner", fontsize=12)

    # Werte auf die Balken schreiben (optional, aber hilfreich)
    for p in ax.patches:
        width, height = p.get_width(), p.get_height()
        if height > 0:
            x, y = p.get_xy()
            ax.text(x + width/2,
                    y + height/2,
                    f'{int(height)}',
                    horizontalalignment='center',
                    verticalalignment='center',
                    color='white',
                    fontweight='bold')

    # Summe oben drüber schreiben
    totals = plot_df.sum(axis=1)
    for i, total in enumerate(totals):
        ax.text(i, total + 0.5, f'{int(total)}', ha='center', va='bottom', fontweight='bold')

    plt.tight_layout()

    # Speichern
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Plot erfolgreich gespeichert unter: {output_path}")

def main() -> None:
    """Haupteinstiegspunkt für das Skript zum Plotten der Datenverteilung."""
    parser = argparse.ArgumentParser(description="Plottet die Verteilung der E-Mail-Klassen (Inbox vs. SentItems).")
    parser.add_argument("--train-dir", type=str, default=r"D:\TH_Koeln\MailTrainingData",
                        help="Pfad zum Trainingsdatenverzeichnis.")
    parser.add_argument("--test-dir", type=str, default=r"D:\TH_Koeln\MailTestData",
                        help="Pfad zum Testdatenverzeichnis.")
    parser.add_argument("--output-dir", type=str, default="data",
                        help="Verzeichnis zum Speichern der Plots.")

    args = parser.parse_args()

    output_dir = Path(args.output_dir)

    # Trainingsdaten
    print(f"Analysiere Trainingsdaten: {args.train_dir}")
    train_df = count_emails(args.train_dir)
    plot_distribution(train_df, "Datenverteilung Trainingsdaten pro Klasse",
                      output_dir / "train_data_distribution.png")

    # Testdaten
    print(f"Analysiere Testdaten: {args.test_dir}")
    test_df = count_emails(args.test_dir)
    plot_distribution(test_df, "Datenverteilung Testdaten pro Klasse",
                      output_dir / "test_data_distribution.png")

if __name__ == "__main__":
    main()
