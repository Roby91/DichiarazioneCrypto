import pandas as pd
from tabulate import tabulate

def parse_movements(csv_path):
    """
    Legge il file CSV (esportato da Coinbase) e restituisce un DataFrame
    con le colonne più importanti (data, tipo operazione, quantità, ecc.)
    """
    try:

        # Leggo il file CSV
        df = pd.read_csv(
            csv_path,
            encoding="cp1252",          # o altra codifica corretta
            parse_dates=["Timestamp"]   # parse automatico delle date
        )

        # Trasformo la colonna Timestamp in datetime con timezone UTC (se necessario)
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], utc=True, errors="coerce")

        # Converto le colonne monetarie in float
        cols_with_euro = [
            "Price at Transaction",
            "Subtotal",
            "Total (inclusive of fees and/or spread)",
            "Fees and/or Spread"
        ]

        for col in cols_with_euro:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace("â‚¬", "", regex=False)
                .str.replace("€", "", regex=False)
                .str.replace(",", "", regex=False)
                .str.strip()
                .replace(r"^-?$", "0", regex=True)
                .astype(float)
            )

        # Esempio: filtra/rinomina colonne, convalida dati, ecc.
        return df
    
    except Exception as e:
        raise ValueError(f"Errore nella lettura del file CSV: {e}")

# Funzione per stampare il DataFrame in maniera formattata
def print_formatted_table(dataframe, num_rows=10):
    """
    Stampa il DataFrame in formato tabellare.
    
    :param dataframe: pandas DataFrame da stampare
    :param num_rows: numero di righe da mostrare (default 10)
    """
    # Definiamo un sottoinsieme di colonne che vogliamo visualizzare:
    columns_to_print = [
        "Timestamp", 
        "Transaction Type", 
        "Asset", 
        "Quantity Transacted", 
        "Price at Transaction", 
        "Total (inclusive of fees and/or spread)"
    ]

    print(tabulate(dataframe[columns_to_print].head(num_rows), headers='keys', tablefmt='psql', showindex=False))


def calculate_taxes(df):
    """
    Calcolo di base (semplificato) per plusvalenze / giacenze / etc.
    """
    # Implementa la logica fiscale specifica per il 2025
    results = {
        "plusvalenze": 0.0,
        "giacenza_media": 0.0
    }
    # ... logica di calcolo ...
    return results

def generate_report(results, output_path="report.pdf"):
    """
    Genera un report PDF/HTML/etc. con i risultati di calcolo.
    """
    with open(output_path, "w") as f:
        f.write("=== REPORT FISCALE 2025 ===\n")
        for k, v in results.items():
            f.write(f"{k}: {v}\n")
