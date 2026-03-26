"""
Custodian B CSV parser.

Expected columns:
    cust_client_id, ISIN, security_name, category, sector,
    sub_account, units, value_usd, report_date

Note: Uses ISIN as the primary identifier; ticker is derived from ISIN for MVP.
      In production, this would use a reference data service (Bloomberg/Refinitiv).
"""
import pandas as pd
from .base_parser import BaseCustodianParser


class CustodianBParser(BaseCustodianParser):
    CUSTODIAN_NAME = "custodian_b"

    CATEGORY_TO_ASSET_CLASS = {
        "EQ": "Equity",
        "FI": "Fixed Income",
        "CA": "Cash",
        "AL": "Alternatives",
    }

    def parse(self, filepath: str) -> pd.DataFrame:
        df = pd.read_csv(filepath)

        df = df.rename(columns={
            "cust_client_id": "client_id",
            "ISIN":           "isin",
            "security_name":  "security_name",
            "sector":         "sector",
            "sub_account":    "account_type",
            "units":          "quantity",
            "value_usd":      "market_value",
        })

        # Map category codes to human-readable asset classes
        df["asset_class"] = df["category"].map(self.CATEGORY_TO_ASSET_CLASS).fillna("Other")

        # Use ISIN as ticker for MVP (no reference data lookup)
        df["ticker"] = df["isin"]

        df["custodian"] = self.CUSTODIAN_NAME
        df["as_of_date"] = pd.to_datetime(df["report_date"]).dt.date

        return self.validate(df)
