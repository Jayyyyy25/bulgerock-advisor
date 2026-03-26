"""
Custodian A CSV parser.

Expected columns:
    AccountID, ClientRef, Symbol, SecurityName, AssetType, Sector,
    AccountCategory, Shares, MarketValue, Date
"""
import pandas as pd
from .base_parser import BaseCustodianParser


class CustodianAParser(BaseCustodianParser):
    CUSTODIAN_NAME = "custodian_a"

    ASSET_CLASS_MAP = {
        "Equity":        "Equity",
        "Fixed Income":  "Fixed Income",
        "Cash":          "Cash",
        "Alternatives":  "Alternatives",
    }

    def parse(self, filepath: str) -> pd.DataFrame:
        df = pd.read_csv(filepath)

        df = df.rename(columns={
            "ClientRef":       "client_id",
            "Symbol":          "ticker",
            "SecurityName":    "security_name",
            "AssetType":       "asset_class",
            "Sector":          "sector",
            "AccountCategory": "account_type",
            "Shares":          "quantity",
            "MarketValue":     "market_value",
        })

        df["isin"] = None
        df["custodian"] = self.CUSTODIAN_NAME
        df["as_of_date"] = pd.to_datetime(df["Date"]).dt.date
        df["asset_class"] = df["asset_class"].map(self.ASSET_CLASS_MAP).fillna(df["asset_class"])

        return self.validate(df)
