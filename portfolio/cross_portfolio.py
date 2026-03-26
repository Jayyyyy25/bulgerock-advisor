"""
Cross-portfolio screening — pure pandas math, no Claude calls.
"""
import json
from typing import Dict, List, Optional

import pandas as pd

from config import PROCESSED_DIR

VALID_DIMENSIONS = {"asset_class", "sector", "geography"}
VALID_OPERATORS  = {">", "<", ">=", "<=", "=="}


class CrossPortfolioAnalyzer:
    def __init__(self):
        self._flat_df: pd.DataFrame = pd.DataFrame()
        self._client_index: Dict[str, dict] = {}
        self.reload()

    def reload(self) -> None:
        """Reload all client JSONs from disk. Call after new PDFs are processed."""
        if not PROCESSED_DIR.exists():
            self._flat_df = pd.DataFrame()
            self._client_index = {}
            return

        records = []
        self._client_index = {}

        for json_file in sorted(PROCESSED_DIR.iterdir()):
            if json_file.suffix != ".json":
                continue
            data = json.loads(json_file.read_text())
            client_id  = data.get("client_id", json_file.stem)
            total_value = float(data.get("total_value", 0))
            self._client_index[client_id] = data

            for category, pct in data.get("asset_allocation", {}).items():
                records.append({"client_id": client_id, "total_value": total_value,
                                 "dimension": "asset_class", "category": str(category).strip(),
                                 "percentage": float(pct)})
            for category, pct in data.get("sector_concentration", {}).items():
                records.append({"client_id": client_id, "total_value": total_value,
                                 "dimension": "sector", "category": str(category).strip(),
                                 "percentage": float(pct)})
            for category, pct in data.get("geographic_exposure", {}).items():
                records.append({"client_id": client_id, "total_value": total_value,
                                 "dimension": "geography", "category": str(category).strip(),
                                 "percentage": float(pct)})

        self._flat_df = (
            pd.DataFrame(records) if records
            else pd.DataFrame(columns=["client_id", "total_value", "dimension", "category", "percentage"])
        )

    def query_exposure(
        self,
        dimension: str,
        threshold: float,
        operator: str = ">",
        category: Optional[str] = None,
    ) -> List[Dict]:
        if dimension not in VALID_DIMENSIONS:
            raise ValueError(f"Invalid dimension '{dimension}'. Choose from: {sorted(VALID_DIMENSIONS)}")
        if operator not in VALID_OPERATORS:
            raise ValueError(f"Invalid operator '{operator}'. Choose from: {sorted(VALID_OPERATORS)}")
        if self._flat_df.empty:
            return []

        df = self._flat_df[self._flat_df["dimension"] == dimension].copy()
        if category:
            df = df[df["category"].str.strip().str.upper() == category.strip().upper()]

        ops = {
            ">":  df["percentage"] > threshold,
            "<":  df["percentage"] < threshold,
            ">=": df["percentage"] >= threshold,
            "<=": df["percentage"] <= threshold,
            "==": df["percentage"] == threshold,
        }
        filtered = df[ops[operator]]
        if filtered.empty:
            return []

        results = []
        for client_id, group in filtered.groupby("client_id"):
            matches = (
                group[["category", "percentage"]]
                .sort_values("percentage", ascending=False)
                .to_dict(orient="records")
            )
            results.append({
                "client_id":   client_id,
                "total_value": float(group["total_value"].iloc[0]),
                "matches":     matches,
            })

        results.sort(key=lambda x: max(m["percentage"] for m in x["matches"]), reverse=True)
        return results

    def get_all_clients_summary(self) -> List[Dict]:
        return [
            {
                "client_id":      data.get("client_id"),
                "total_value":    data.get("total_value", 0),
                "asset_allocation": data.get("asset_allocation", {}),
                "risk_metrics":   data.get("risk_metrics", {}),
            }
            for data in self._client_index.values()
        ]
