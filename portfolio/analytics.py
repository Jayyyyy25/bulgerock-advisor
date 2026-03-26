"""
Portfolio analytics: allocations, concentrations, risk metrics, and summary.
"""
from typing import Any, Dict
import pandas as pd


class PortfolioAnalytics:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.df["market_value"] = pd.to_numeric(
            self.df["market_value"], errors="coerce"
        ).fillna(0.0)
        self.total_value = self.df["market_value"].sum()

    def get_total_value(self) -> float:
        return self.total_value

    def get_asset_allocation(self) -> Dict[str, float]:
        if "asset_class" not in self.df.columns or self.total_value == 0:
            return {}
        return (
            (self.df.groupby("asset_class")["market_value"].sum() / self.total_value * 100)
            .round(2)
            .to_dict()
        )

    def get_sector_concentration(self) -> Dict[str, float]:
        if "sector" not in self.df.columns or self.total_value == 0:
            return {}
        valid = self.df[self.df["sector"].notna()]
        valid = valid[
            ~valid["sector"].astype(str).str.strip().str.upper()
            .isin(["N/A", "NAN", "NONE", "NULL", ""])
        ]
        if valid.empty:
            return {}
        return (
            (valid.groupby("sector")["market_value"].sum() / valid["market_value"].sum() * 100)
            .round(2)
            .to_dict()
        )

    def get_geographic_exposure(self) -> Dict[str, float]:
        if "geography" not in self.df.columns or self.total_value == 0:
            return {}
        valid = self.df[self.df["geography"].notna()]
        valid = valid[
            ~valid["geography"].astype(str).str.strip().str.upper()
            .isin(["N/A", "NAN", "NONE", "NULL", ""])
        ]
        if valid.empty:
            return {}
        return (
            (valid.groupby("geography")["market_value"].sum() / valid["market_value"].sum() * 100)
            .round(2)
            .to_dict()
        )

    def get_top_10_holdings(self) -> pd.DataFrame:
        if self.df.empty:
            return self.df
        return self.df.nlargest(10, "market_value")[["security_name", "market_value"]]

    def get_risk_metrics(self) -> Dict[str, float]:
        equity_weight = self.get_asset_allocation().get("Equities", 0) / 100
        return {
            "estimated_volatility_pct": round(5.0 + equity_weight * 15.0, 2),
            "estimated_sharpe_ratio":   round(1.0 + equity_weight * 0.4,  2),
        }

    def generate_summary(self) -> Dict[str, Any]:
        return {
            "total_value":          self.total_value,
            "asset_allocation":     self.get_asset_allocation(),
            "sector_concentration": self.get_sector_concentration(),
            "geographic_exposure":  self.get_geographic_exposure(),
            "top_10_holdings":      self.get_top_10_holdings().to_dict(orient="records"),
            "risk_metrics":         self.get_risk_metrics(),
        }
