import argparse
import sys
from core.utils import print_banner
from fiscal_years.utils import get_rules_module

def main():
    parser = argparse.ArgumentParser(
        description="DichiarazioneCrypto – Calcolo ai fini fiscali (730, ISEE) da movimenti crypto."
    )
    parser.add_argument("--anno", type=str, required=False, default="2025",
                        help="Anno fiscale di riferimento (default: 2025)")
    parser.add_argument("--file", type=str, required=False,
                        help="Path del file CSV con i movimenti crypto (es. Coinbase).")
    parser.add_argument("--output", type=str, required=False,
                        help="Path per il report di output (PDF o altro).")
    args = parser.parse_args()

    print_banner()

    # Carica il modulo con le regole specifiche dell'anno
    rules = get_rules_module(args.anno)

    if not args.file:
        print("❌ Errore: devi specificare il file CSV dei movimenti con --file\n")
        parser.print_help()
        sys.exit(1)

    # Esegui la logica principale
    data = rules.parse_movements(args.file)

    print("\n\n\n▶ Primi 10 movimenti letti:")
    rules.print_formatted_table(data)

    assets = rules.get_assets(data)
    print("\n\n\n▶ Asset trovati:", assets)

    daily_asset_balances = rules.get_daily_asset_balances(data)
    print("\n\n\n▶ Saldo giornaliero per asset:")
    rules.print_daily_asset_balances(daily_asset_balances)

    results = rules.calculate_taxes(data)

    print("\n\n\n▶ Risultati calcolo:", results)

    # Genera un report
    if args.output:
        rules.generate_report(results, output_path=args.output)
        print(f"✅ Report generato: {args.output}")
    else:
        print("▶ Risultati calcolo:", results)


if __name__ == "__main__":
    main()
