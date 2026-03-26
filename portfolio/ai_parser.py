"""
PDF portfolio extraction using pdfplumber + Claude.
Produces a clean pandas DataFrame of all holdings.
"""
import os
import json
import re
import pandas as pd
import pdfplumber
from anthropic import Anthropic

CANONICAL_COLUMNS = [
    "security_name", "isin", "quantity", "market_value",
    "asset_class", "sector", "geography",
]

ASSET_CLASS_MAP = {
    "CASH": "Cash",
    "CASH & DEPOSITS": "Cash",
    "CASH & DEPOSITS (SGD)": "Cash",
    "CASH & EQUIVALENTS": "Cash",
    "CASH TOTAL": "Cash",
    "FIXED INCOME": "Fixed Income",
    "BONDS & FIXED INCOME": "Fixed Income",
    "BONDS": "Fixed Income",
    "EQUITY": "Equities",
    "LISTED EQUITIES": "Equities",
    "REITS": "Real Estate",
    "REAL ESTATE": "Real Estate",
    "HEDGE FUNDS": "Alternatives",
    "COMMODITIES": "Alternatives",
}

SUMMARY_PATTERNS = [
    r"TOTAL$", r"^TOTAL$", r"^BONDS & FIXED INCOME$",
    r"^LISTED EQUITIES$", r"^EQUITIES$", r"^STRUCTURED PRODUCTS$",
    r"^CASH & DEPOSITS", r"^CASH TOTAL$", r"^CASH & EQUIVALENTS$", r"^REITS$",
]
SUMMARY_REGEX = "|".join(SUMMARY_PATTERNS)
COVERAGE_THRESHOLD = 0.80


class AIPortfolioParser:
    def __init__(self):
        self.client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    def process_pdf(self, file_path: str) -> pd.DataFrame:
        all_dfs = []
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                print(f"  Parsing page {i + 1}...")
                page_text = page.extract_text()
                if page_text:
                    df = self._parse_page_with_claude(page_text)
                    if not df.empty:
                        all_dfs.append(df)

        if not all_dfs:
            return pd.DataFrame(columns=CANONICAL_COLUMNS)

        master_df = pd.concat(all_dfs, ignore_index=True)
        master_df["market_value"] = pd.to_numeric(
            master_df["market_value"], errors="coerce"
        ).fillna(0)
        master_df["clean_name"] = (
            master_df["security_name"].astype(str).str.strip().str.upper()
        )

        master_df["asset_class"] = master_df["asset_class"].apply(
            lambda x: ASSET_CLASS_MAP.get(str(x).strip().upper(), x)
        )

        is_summary = master_df["clean_name"].str.contains(
            SUMMARY_REGEX, na=False, regex=True
        )
        summary_df = master_df[is_summary].copy()
        detail_df = master_df[~is_summary].copy()

        def is_redundant(row):
            ac = str(row.get("asset_class", "") or "").strip().upper()
            sv = abs(row.get("market_value", 0) or 0)
            if not ac or sv == 0:
                return False
            mask = detail_df["asset_class"].astype(str).str.strip().str.upper() == ac
            return abs(detail_df.loc[mask, "market_value"].sum()) / sv >= COVERAGE_THRESHOLD

        rows_to_drop = summary_df.apply(is_redundant, axis=1)
        master_df = pd.concat(
            [detail_df, summary_df[~rows_to_drop]], ignore_index=True
        )

        is_liability = master_df["market_value"] < 0
        master_df = pd.concat([
            master_df[~is_liability].drop_duplicates(subset=["security_name", "market_value"]),
            master_df[is_liability].drop_duplicates(subset=["market_value"]),
        ], ignore_index=True)

        return master_df.drop(columns=["clean_name"], errors="ignore")

    def _parse_page_with_claude(self, page_text: str) -> pd.DataFrame:
        prompt = f"""You are a strict data extraction pipeline. Extract EVERY individual asset holding.

RULES:
1. Extract every stock, bond, fund, or asset row. Do NOT skip items.
2. Do NOT extract category summary rows (e.g., "EQUITY TOTAL").
3. EXCEPTION: DO extract "Cash & Equivalents", "Structured Products", "Liabilities".
4. Infer 'sector' and 'geography' using ONLY the allowed values below.

ALLOWED SECTORS (11 GICS + Diversified):
Information Technology, Health Care, Financials, Consumer Discretionary,
Communication Services, Industrials, Consumer Staples, Energy, Utilities,
Real Estate, Materials, Diversified, N/A

ALLOWED GEOGRAPHIES:
USA, China, Europe, India, Japan, Global, N/A

OUTPUT — JSON array only, no markdown:
[{{
    "security_name": "String",
    "isin": "String or null",
    "quantity": <float, use 1.0 if unknown>,
    "market_value": <float, negative for liabilities>,
    "asset_class": "Equities | Fixed Income | Alternatives | Cash | Structured Products | Liabilities",
    "sector": "<from allowed sectors>",
    "geography": "<from allowed geographies>"
}}]

Page text:
{page_text}"""

        try:
            response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=4000,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text
            match = re.search(r"\[.*\]", raw, re.DOTALL)
            if not match:
                return pd.DataFrame(columns=CANONICAL_COLUMNS)

            data = json.loads(match.group(0))
            df = pd.DataFrame(data)
            for col in CANONICAL_COLUMNS:
                if col not in df.columns:
                    df[col] = None
            return df[CANONICAL_COLUMNS]

        except Exception as e:
            print(f"  Page parse error: {e}")
            return pd.DataFrame(columns=CANONICAL_COLUMNS)
