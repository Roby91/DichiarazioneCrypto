import datetime
import decimal
import pandas as pd
from decimal import Decimal, InvalidOperation, getcontext
from tabulate import tabulate
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from pathlib import Path


YEAR = 2024 # Anno a cui si riferiscono le transazioni

# folder where this file lives:
BASE_DIR = Path(__file__).parent

# — set max precision high enough for all your CSV values —
getcontext().prec = 50


def parse_movements(csv_path):
    """
    Legge il file CSV (esportato da Coinbase) e restituisce un DataFrame
    con le colonne più importanti (data, tipo operazione, quantità, ecc.)
    """
    try:

        def parse_decimal(x):
            """Strip out currency symbols/commas and return a Decimal, defaulting to 0."""
            try:
                if pd.isna(x):
                    return Decimal("0")
                s = str(x).replace("â‚¬", "").replace("€", "").replace(",", "").strip()
                if s in ("", "-", "-"):
                    return Decimal("0")
                return Decimal(s)
            except InvalidOperation:
                return Decimal("0")
            
        # List of columns that require precise parsing
        money_cols = [
            "Price at Transaction",
            "Subtotal",
            "Total (inclusive of fees and/or spread)",
            "Fees and/or Spread"
        ]
        all_decimal_cols = money_cols + ["Quantity Transacted"]
        converters = {col: parse_decimal for col in all_decimal_cols}

        # Leggo il file CSV
        df = pd.read_csv(
            csv_path,
            encoding="cp1252",           # o altra codifica corretta
            parse_dates=["Timestamp"],   # parse automatico delle date
            converters=converters,       # converto le colonne monetarie
        )

        # Trasformo la colonna Timestamp in datetime con timezone UTC (se necessario)
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], utc=True, errors="coerce")

        # TODO: validazione che ogni "Price Currency" sia in EUR

        # riordina per timestamp crescente:
        df = df.sort_values("Timestamp", ascending=True)

        return df
    
    except Exception as e:
        raise ValueError(f"Errore nella lettura del file CSV: {e}")

def print_formatted_table(dataframe, num_rows=10):
    """
    Stampa il DataFrame in formato tabellare.
    Stampa *esattamente* ogni Decimal come stringa completa,
    senza alcuna formattazione in virgola mobile.
    
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

    to_print = dataframe[columns_to_print].head(num_rows).copy()

    # Per ogni colonna Decimal, sostituisci l'oggetto con la sua rappresentazione testuale
    for c in ["Quantity Transacted", "Price at Transaction", "Total (inclusive of fees and/or spread)"]:
        to_print[c] = to_print[c].apply(lambda x: str(x) if isinstance(x, Decimal) else x)

    # Per riuscire a stampare a piena precisione è importante disabilitare il parsing automatico dei numeri (disable_numparse=True)
    print(tabulate(to_print, headers="keys", tablefmt="psql", disable_numparse=True, showindex=False))

def get_assets(dataframe):
    """
    Estrae le tipologie di asset presenti nel DataFrame.
    """
    # Individuazione delle tipologie di asset presenti
    asset_types = dataframe["Asset"].unique()

    return asset_types

def get_daily_asset_balances(dataframe):
    """
    Per ogni asset presente in 'dataframe' restituisce un DataFrame indicizzato sui
    giorni dell'anno con quattro colonne:
    - 'Date': la data normalizzata (senza ora/minuti/secondi)
    - 'Price': il prezzo in EUR dell'asset (forward filled)
    - 'Balance': la giacenza cumulativa calcolata giorno per giorno
    - 'Controvalore': il valore in EUR della giacenza giornaliera, basato sul prezzo
    """
    # normalizzo Timestamp → Date e Quantity, con sell = negative
    df = dataframe.copy()
    df['Date'] = (
        pd.to_datetime(df['Timestamp'], utc=True)
          .dt.normalize()
    )
    df['Quantity Transacted'] = (
        pd.to_numeric(df['Quantity Transacted'], errors='coerce')
    )

    # invertiamo le quantità per tutte le transaction types che contengono "sell"
    sell = df['Transaction Type'].str.lower().str.contains('sell', na=False)
    df.loc[sell, 'Quantity Transacted'] *= -1
    
    # TODO: vanno gestitie eventuali tipi di transazione al momento non note

    # calendario dell'anno (assumo YEAR e BASE_DIR definiti a livello di modulo)
    dates = pd.date_range(f"{YEAR}-01-01", f"{YEAR}-12-31", freq='D', tz='UTC')

    out = {}
    for asset, grp in df.groupby('Asset'):
        # cumulativi dei delta giornalieri
        balance = (
            grp.groupby('Date')['Quantity Transacted']
               .sum()
               .reindex(dates, fill_value=0)
               .cumsum()
        )

        # quotazioni EUR forward‑filled
        price_df = pd.read_csv(
            Path(BASE_DIR) / 'data' / f"{asset.lower()}_prices_{YEAR}.csv",
            parse_dates=['Date'], index_col='Date'
        )['Price']
        prices = (
            price_df
              .tz_localize('UTC')
              .reindex(dates, method='ffill')
        )

        # DataFrame con le 4 colonne
        out[asset] = pd.DataFrame({
            'Date':         dates,
            'Price':        prices.values,
            'Balance':      balance.values,
            'Controvalore': balance.values * prices.values
        })

    return out

def print_daily_asset_balances(balances):
    """
    Stampa le giacenze giornaliere e il relativo controvalore per ogni asset.

    :param balances: dict[str, pd.DataFrame] con colonne ['Date', 'Price', 'Balance', 'Controvalore']
    """
    for asset, df in balances.items():
        print(f"\nAsset: {asset}")
        # tabulate su DataFrame, senza mostrare l'indice (Date è colonna)
        print(tabulate(df, headers="keys", tablefmt="psql", showindex=False))

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

def generate_report_original(results: dict[str, pd.Series],
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
    # Prepariamo lo "Story" Platypus
    doc   = SimpleDocTemplate(output_path, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    h1, h2, normal = styles["Heading1"], styles["Heading2"], styles["BodyText"]

    # === HEADER generale ====================================================
    story.append(Paragraph(f"REPORT FISCALE CRYPTO {YEAR + 1}", h1))
    story.append(Paragraph(f"Riferito alle attività del {YEAR}", h2))
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
        #df_bal = serie.to_frame(name="Qty").reset_index(names="Date")
        #df_bal["Date"] = df_bal["Date"].dt.strftime("%Y-%m-%d")
        #top   = df_bal.head(10).values.tolist()
        #bottom = df_bal.tail(10).values.tolist()
        #table_data = top + [["...", "..."]] + bottom
        #story.append(_make_table(table_data, ["Data", "Quantità"]))
        #story.append(Spacer(1, 6))

        # ------- tabella giornaliera completa (per ogni giorno dell'anno)
        df_bal = serie.to_frame(name="Qty").reset_index(names="Date")
        df_bal["Date"] = df_bal["Date"].dt.strftime("%Y-%m-%d")
        story.append(_make_table(df_bal.values.tolist(), ["Data", "Quantità"]))
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

def generate_report(results: dict[str, pd.DataFrame],
                    df_tx: pd.DataFrame | None = None,
                    output_path: str = f"report_crypto_{YEAR + 1}.pdf"):
    """
    Crea un PDF con:
      • saldo giorno-per-giorno di ogni asset (Balance e Controvalore)
      • giacenza media annua
      • plusvalenza stimata
    :param results:  dict {asset: DataFrame con colonne ['Date','Balance','Controvalore']}
    :param df_tx:    DataFrame originale delle transazioni (per ricavare il prezzo ultimo)
    :param output_path: path del file PDF in uscita
    """
    # Preparazione document
    doc   = SimpleDocTemplate(output_path, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    h1, h2, normal = styles["Heading1"], styles["Heading2"], styles["BodyText"]

    # HEADER
    story.append(Paragraph(f"REPORT FISCALE CRYPTO {YEAR + 1}", h1))
    story.append(Paragraph(f"Riferito alle attività del {YEAR}", h2))
    story.append(Spacer(1, 12))

    # riepilogo finale
    summary_rows = []

    for asset, df_bal in results.items():
        story.append(Paragraph(asset, h2))

        # ultimo prezzo da df_tx (se disponibile)
        last_price = None
        if df_tx is not None:
            sel = df_tx.loc[df_tx["Asset"] == asset, "Price at Transaction"]
            if not sel.empty:
                last_price = pd.to_numeric(sel, errors="coerce").dropna().iloc[-1]

        # -- Preparo la tabella completa con Balance e Controvalore
        # Assicuro che 'Date' sia stringa formattata
        # Get the first day of the year value before converting to string
        first_day = df_bal[df_bal['Date'].dt.date == datetime.date(YEAR, 1, 1)]

        # ---------------------------------------------------------------------
        # Quadro W: calcolo valore iniziale/finale (unità + controvalore EUR)
        # ---------------------------------------------------------------------
        valore_iniziale = valore_iniziale_controvalore = None
        valore_finale   = valore_finale_controvalore   = None

        if df_tx is not None:
            tx = df_tx[df_tx["Asset"] == asset].copy()
            if not tx.empty:
                # uniformo timestamp
                tx["Timestamp"] = pd.to_datetime(tx["Timestamp"], utc=True)
                tx_year = tx[tx["Timestamp"].dt.year == YEAR]

                # -- VALORE INIZIALE --
                if not first_day.empty and first_day["Balance"].iloc[0] != 0:
                    # già saldo al 1° gennaio
                    valore_iniziale = first_day["Balance"].iloc[0]
                    valore_iniziale_controvalore = first_day["Controvalore"].iloc[0]
                else:
                    # primo acquisto (Quantity Transacted > 0)
                    qty = pd.to_numeric(tx_year["Quantity Transacted"], errors="coerce")
                    ingoing = tx_year[tx_year["Transaction Type"].str.lower().str.contains("buy|in")]
                    if not ingoing.empty:
                        first_tx = ingoing.sort_values("Timestamp").iloc[0]
                        d0 = first_tx["Timestamp"].date()
                        row0 = df_bal[df_bal["Date"].dt.date == d0]
                        if not row0.empty:
                            valore_iniziale = first_tx["Quantity Transacted"]
                            # per coerenza utilizzo il tasso di cambio dal file statico
                            valore_iniziale_controvalore = abs(first_tx["Quantity Transacted"] * decimal.Decimal(float(row0["Price"].iloc[0])))

                # -- VALORE FINALE --
                qty = pd.to_numeric(tx_year["Quantity Transacted"], errors="coerce")
                outgoing = tx_year[tx_year["Transaction Type"].str.lower().str.contains("sell|withdraw|out")]
                if not outgoing.empty:
                    last_tx = outgoing.sort_values("Timestamp").iloc[-1]
                    d1 = last_tx["Timestamp"].date()
                    row1 = df_bal[df_bal["Date"].dt.date == d1]
                    if not row1.empty:
                        valore_finale = last_tx["Quantity Transacted"]
                        # per coerenza utilizzo il tasso di cambio dal file statico
                        valore_finale_controvalore = abs(last_tx["Quantity Transacted"] * decimal.Decimal(float(row1["Price"].iloc[0])))


        # fallback: se nessuna uscita, prendo 31/12
        if valore_finale is None:
            mask_eoy = df_bal["Date"].dt.date == datetime.date(YEAR, 12, 31)
            if mask_eoy.any():
                valore_finale = df_bal.loc[mask_eoy, "Balance"].iloc[0]
                valore_finale_controvalore = df_bal.loc[mask_eoy, "Controvalore"].iloc[0]
        # ---------------------------------------------------------------------

        # Now convert Date to string format for display
        df_display = df_bal.copy()
        df_display["Date"] = pd.to_datetime(df_display["Date"], utc=True).dt.strftime("%Y-%m-%d")
        # colonne in ordine desiderato
        cols = ["Date", "Balance", "Controvalore"]
        #table_data = [cols] + df_display[cols].values.tolist()
        #story.append(_make_table(table_data, cols))
        rows = df_display[cols].values.tolist()
        story.append(_make_table(rows, cols))
        story.append(Spacer(1, 18))

        if not first_day.empty:
            story.append(Paragraph(f"Giacenza al 01/01/{YEAR}: <b>{first_day['Balance'].iloc[0]:,.8f} {asset}</b>",normal))
            story.append(Paragraph(f"Controvalore al 01/01/{YEAR}: <b>{first_day['Controvalore'].iloc[0]:,.2f} EUR</b>",normal))
        else:
            story.append(Paragraph(f"Giacenza al 01/01/{YEAR}: <i>nessun dato per il 01/01</i>",normal))
            story.append(Paragraph(f"Controvalore al 01/01/{YEAR}: <i>nessun dato per il 01/01</i>",normal))

        # saldo al 31/12
        mask_31 = df_bal["Date"].dt.date == datetime.date(YEAR, 12, 31)
        if mask_31.any():
            eoy_bal = df_bal.loc[mask_31, "Balance"].iloc[0]
            story.append(Paragraph(f"Giacenza al 31/12/{YEAR}: <b>{eoy_bal:,.8f} {asset}</b>",normal))
            eoy_con = df_bal.loc[mask_31, "Controvalore"].iloc[0]
            story.append(Paragraph(f"Controvalore al 31/12/{YEAR}: <b>{eoy_con:,.2f} EUR</b>",normal))
        else:
            story.append(Paragraph(f"Giacenza al 31/12/{YEAR}: <i>nessun dato per il 31/12</i>",normal))
            story.append(Paragraph(f"Controvalore al 31/12/{YEAR}: <i>nessun dato per il 31/12</i>",normal))
 
        story.append(Paragraph(f"Valore iniziale *: <b>{valore_iniziale_controvalore:,.2f} EUR</b>",normal))
        story.append(Paragraph(f"Valore finale *: <b>{valore_finale_controvalore:,.2f} EUR</b>",normal))

        
        # -- metriche di sintesi sulla colonna 'Balance'
        avg_bal, gain_eur = _compute_summary(df_bal["Balance"], last_price)
        story.append(Paragraph(f"Giacenza media annua: <b>{avg_bal:,.8f} {asset}</b>", normal))

        if last_price is not None:
            story.append(Paragraph(f"Plusvalenza stimata: <b>{gain_eur:,.2f} €</b>", normal))
        else:
            story.append(Paragraph("Plusvalenza stimata: <i>prezzo mancante - non calcolata</i>", normal))
        story.append(Spacer(1, 12))
        
        #story.append(PageBreak())

        summary_rows.append([
            asset,
            f"{avg_bal:,.8f}",
            f"{gain_eur:,.2f}" if last_price is not None else "n/d"
        ])

        story.append(Spacer(1, 22))

        text = (
            "<b>* Quadro W del Modello 730/2025</b>: i campi “<b>valore iniziale</b>” e “<b>valore finale</b>” "
            "si riferiscono al valore complessivo delle criptovalute detenute, non al valore unitario di ciascuna. "
            "Pertanto, anche se hai acquistato frazioni (es. 0,1 Bitcoin), devi indicare il valore totale di quella frazione."
            "<br/><br/>"
            "<b>Valore iniziale:</b><br/>"
            "&#8226; Se l'attività era già detenuta al <b>1 gennaio 2024</b>: indica il valore di mercato dell'asset a quella data.<br/>"
            "&#8226; Se l'attività è stata acquisita durante il 2024: indica il valore di mercato al momento del primo acquisto.<br/>"
            "Il valore deve essere espresso in <b>euro</b>, usando il tasso di cambio ufficiale alla data di riferimento se l'attività è denominata in valuta estera."
            "<br/><br/>"
            "<b>Valore finale:</b><br/>"
            "&#8226; Se l'attività è ancora detenuta al <b>31 dicembre 2024</b>: indica il valore di mercato dell'asset a quella data.<br/>"
            "&#8226; Se l'attività è stata completamente venduta o dismessa durante il 2024: indica il valore di mercato al momento dell'ultima vendita o dismissione.<br/>"
            "Anche in questo caso, il valore deve essere espresso in <b>euro</b>, utilizzando il tasso di cambio ufficiale alla data di riferimento se necessario."
        )

        story.append(Paragraph(text, normal))

        story.append(Spacer(1, 22))



    # RIEPILOGO FINALE
    story.append(Paragraph("Riepilogo annuale", h2))
    story.append(_make_table(
        [["Asset", "Giacenza media", "Plusvalenza (€)"]] + summary_rows,
        ["Asset", "Giacenza media", "Plusvalenza (€)"],
        h_align="CENTER"
    ))
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "NB: la plusvalenza è calcolata come differenza di quantità "
        "tra 1 gennaio e 31 dicembre moltiplicata per l'ultimo prezzo disponibile "
        "nel file CSV. Se desideri il calcolo FIFO/LIFO delle plusvalenze realizzate, "
        "occorre un'analisi più approfondita delle singole operazioni di vendita.",
        normal
    ))

    # BUILD
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
