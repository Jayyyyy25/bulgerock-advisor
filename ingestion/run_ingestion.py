"""
CLI entry point for the data ingestion engine.

Usage:
    python -m ingestion.run_ingestion --custodian custodian_a --file path/to/file.csv
    python -m ingestion.run_ingestion --custodian custodian_b --file path/to/file.csv
"""
import argparse
import sys
from .parsers.custodian_a import CustodianAParser
from .parsers.custodian_b import CustodianBParser
from .upsert import upsert_holdings
from .aum_calculator import recalculate_aum

PARSERS = {
    "custodian_a": CustodianAParser(),
    "custodian_b": CustodianBParser(),
}


def main():
    parser = argparse.ArgumentParser(description="Pocket IA: Custodian CSV Ingestion Engine")
    parser.add_argument(
        "--custodian",
        required=True,
        choices=list(PARSERS.keys()),
        help="Which custodian format to parse",
    )
    parser.add_argument(
        "--file",
        required=True,
        help="Path to the custodian CSV file",
    )
    args = parser.parse_args()

    print(f"[ingestion] Parsing {args.file} as {args.custodian}...")
    try:
        df = PARSERS[args.custodian].parse(args.file)
        print(f"[ingestion] Parsed {len(df)} rows. Upserting into holdings...")
        count = upsert_holdings(df)
        print(f"[ingestion] Upserted {count} holdings records.")

        updated = recalculate_aum()
        print(f"[ingestion] Recalculated AUM for {updated} clients.")
    except Exception as e:
        print(f"[ingestion] ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
