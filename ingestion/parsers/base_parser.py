"""
Abstract base class for all custodian CSV parsers.
All parsers must return a DataFrame with the canonical column set.
"""
from abc import ABC, abstractmethod
import pandas as pd


class BaseCustodianParser(ABC):
    CANONICAL_COLUMNS = [
        "client_id",
        "ticker",
        "security_name",
        "isin",
        "asset_class",
        "sector",
        "account_type",
        "quantity",
        "market_value",
        "custodian",
        "as_of_date",
    ]

    @abstractmethod
    def parse(self, filepath: str) -> pd.DataFrame:
        """Parse a custodian CSV file and return a canonical DataFrame."""
        ...

    def validate(self, df: pd.DataFrame) -> pd.DataFrame:
        missing = set(self.CANONICAL_COLUMNS) - set(df.columns)
        if missing:
            raise ValueError(f"Parser output is missing required columns: {missing}")
        df = df[self.CANONICAL_COLUMNS].copy()
        df["market_value"] = pd.to_numeric(df["market_value"], errors="coerce").fillna(0)
        df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)
        df = df.dropna(subset=["client_id", "ticker", "as_of_date"])
        return df
