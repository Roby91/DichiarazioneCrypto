import pandas as pd
from tabulate import tabulate
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet


YEAR = 2024 # Anno a cui si riferiscono le transazioni


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

def get_assets(dataframe):
    """
    Estrae le tipologie di asset presenti nel DataFrame.
    """
    # Individuazione delle tipologie di asset presenti
    asset_types = dataframe["Asset"].unique()

    return asset_types

def get_daily_asset_balances(dataframe):
    """
    Per ogni asset presente in 'df' restituisce una Serie indicizzata sui
    giorni dell'anno con la giacenza cumulativa calcolata giorno per giorno.
    """
    # --- preparazione colonne utili ----------------------------------
    df = dataframe.copy()
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], utc=True, errors="coerce")
    df["Date"] = df["Timestamp"].dt.normalize()           # tronco a mezzanotte
    df["Quantity Transacted"] = pd.to_numeric(
        df["Quantity Transacted"], errors="coerce"
    )
    
    # calendario completo dell'anno                                   
    calendar = pd.date_range(f"{YEAR}-01-01", f"{YEAR}-12-31", freq="D", tz="UTC")
    
    balances = {}
    for asset, g in df.groupby("Asset"):
        # sommo le transazioni avvenute lo stesso giorno
        daily_delta = g.groupby("Date")["Quantity Transacted"].sum()
        # "esplodo" i giorni mancanti riempiendoli di 0
        daily_delta = daily_delta.reindex(calendar, fill_value=0)
        # running total → giacenza giorno per giorno
        balances[asset] = daily_delta.cumsum()
    
    return balances

def print_daily_asset_balances(balances):
    """
    Stampa le giacenze giornaliere per ogni asset in formato tabellare.
    
    :param balances: dizionario con giacenze giornaliere per asset
    """
    for asset, balance in balances.items():
        print(f"Asset: {asset}")
        print(tabulate(balance.items(), headers=["Date", "Balance"], tablefmt="psql"))

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

def generate_report(results: dict[str, pd.Series],
                    df_tx: pd.DataFrame | None = None,
                    output_path: str = f"report_crypto_{YEAR + 1}.pdf"):
    """
    Crea un PDF con:
      • saldo giorno-per-giorno di ogni asset
      • giacenza media annua
      • plusvalenza stimata
    :param results:  dict {asset: Serie (index=datetime, values=quantità)}
    :param df_tx:    DataFrame originale delle transazioni (necessario per i prezzi)
    :param output_path: path del file PDF in uscita
    """
    # Prepariamo lo “Story” Platypus
    doc   = SimpleDocTemplate(output_path, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    h1, h2, normal = styles["Heading1"], styles["Heading2"], styles["BodyText"]

    # === HEADER generale ====================================================
    story.append(Paragraph(f"REPORT FISCALE CRYPTO - Anno {YEAR + 1}", h1))
    story.append(Spacer(1, 12))

    # contieni i riepiloghi finali
    summary_rows = []

    # === UN CAPITOLO PER OGNI ASSET =========================================
    for asset, serie in results.items():
        story.append(Paragraph(asset, h2))

        # ------- ricavo l'ultimo prezzo disponibile dall'eventuale DataFrame
        last_price = None
        if df_tx is not None:
            sel = df_tx.loc[df_tx["Asset"] == asset, "Price at Transaction"]
            if not sel.empty:
                # to_numeric nel dubbio + prendo l'ultimo valore non‑NaN
                last_price = pd.to_numeric(sel, errors="coerce").dropna().iloc[-1]

        # ------- tabella giornaliera (mostriamo solo le prime/ultime 10 righe)
        df_bal = serie.to_frame(name="Qty").reset_index(names="Date")
        df_bal["Date"] = df_bal["Date"].dt.strftime("%Y-%m-%d")
        top   = df_bal.head(10).values.tolist()
        bottom = df_bal.tail(10).values.tolist()
        table_data = top + [["...", "..."]] + bottom
        story.append(_make_table(table_data, ["Data", "Quantità"]))
        story.append(Spacer(1, 6))

        # ------- metriche di sintesi
        avg_bal, gain_eur = _compute_summary(serie, last_price)
        story.append(Paragraph(
            f"Giacenza media annua: <b>{avg_bal:,.8f} {asset}</b>", normal))
        if last_price is not None:
            story.append(Paragraph(
                f"Plusvalenza stimata: <b>{gain_eur:,.2f} €</b>", normal))
        else:
            story.append(Paragraph(
                "Plusvalenza stimata: <i>prezzo mancante - non calcolata</i>", normal))
        story.append(Spacer(1, 12))

        # arricchiamo il riepilogo finale
        summary_rows.append([asset,
                             f"{avg_bal:,.8f}",
                             f"{gain_eur:,.2f}" if last_price is not None else "n/d"])

        story.append(PageBreak())

    # === RIEPILOGO FINALE ===================================================
    story.append(Paragraph("Riepilogo annuale", h2))
    story.append(_make_table(summary_rows,
                             ["Asset", "Giacenza media", "Plusvalenza (€)"],
                             h_align="CENTER"))
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "NB: la plusvalenza è calcolata come differenza di quantità "
        "tra 1 gennaio e 31 dicembre moltiplicata per l'ultimo prezzo disponibile "
        "nel file CSV. Se desideri il calcolo FIFO/LIFO delle plusvalenze realizzate, "
        "occorre un'analisi più approfondita delle singole operazioni di vendita.", normal))

    # === BUILD ==============================================================
    doc.build(story)
    print(f"Report generato in: {output_path}")




def _compute_summary(series: pd.Series, last_price: float | None) -> tuple[float, float]:
    """
    Ritorna (giacenza_media, plusvalenza_eur).
    La plusvalenza è calcolata come (q_finale - q_iniziale) * last_price.
    """
    avg_balance = series.mean()                                          # media annua
    if last_price is None:
        gain_eur = float("nan")  # se manca il prezzo non possiamo stimare in €
    else:
        gain_eur = (series.iloc[-1] - series.iloc[0]) * last_price
    return avg_balance, gain_eur

def _make_table(data, col_names, h_align="LEFT"):
    """
    Rende più leggibile la creazione di tabelle Platypus.
    """
    tbl = Table([col_names] + data, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID",       (0, 0), (-1, -1), 0.25, colors.grey),
        ("ALIGN",      (0, 0), (-1, -1), h_align),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold")
    ]))
    return tbl
