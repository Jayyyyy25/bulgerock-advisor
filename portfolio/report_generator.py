"""
One-page Markdown portfolio summary generator.
"""
from datetime import datetime

from config import REPORTS_DIR


class ReportGenerator:
    def generate_markdown(self, client_data: dict, output_filename: str = None) -> str:
        client_id            = client_data.get("client_id", "Unknown_Client")
        total_value          = client_data.get("total_value", 0)
        asset_allocation     = client_data.get("asset_allocation", {})
        sector_concentration = client_data.get("sector_concentration", {})
        geographic_exposure  = client_data.get("geographic_exposure", {})
        top_holdings         = client_data.get("top_10_holdings", [])
        risk_metrics         = client_data.get("risk_metrics", {})
        timestamp            = datetime.now().strftime("%B %d, %Y")

        lines = [
            f"# Portfolio Summary — {client_id}",
            f"*Generated: {timestamp} | SAMPLE / ANONYMISED DATA*",
            "", "---", "",
            "## Net Portfolio Value", "",
            f"### ${total_value:,.2f}", "", "---", "",
            "## Asset Allocation", "",
            "| Asset Class | Allocation |",
            "|:------------|----------:|",
        ]
        for asset, pct in sorted(asset_allocation.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"| {asset} | {pct:.1f}% |")

        lines += ["", "---", "", "## Sector Concentration", "",
                  "| Sector | Weight |", "|:-------|-------:|"]
        for sector, pct in sorted(sector_concentration.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"| {sector} | {pct:.1f}% |")

        lines += ["", "---", "", "## Geographic Exposure", "",
                  "| Region | Weight |", "|:-------|-------:|"]
        for geo, pct in sorted(geographic_exposure.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"| {geo} | {pct:.1f}% |")

        lines += ["", "---", "", "## Top 10 Holdings", "",
                  "| # | Security | Market Value |",
                  "|:-:|:---------|-------------:|"]
        for i, h in enumerate(top_holdings[:10], 1):
            lines.append(f"| {i} | {h.get('security_name', '')} | ${h.get('market_value', 0):,.2f} |")

        lines += [
            "", "---", "", "## Risk Metrics *(Estimated Proxy)*", "",
            "| Metric | Value |", "|:-------|------:|",
            f"| Estimated Volatility | {risk_metrics.get('estimated_volatility_pct', 'N/A')}% |",
            f"| Estimated Sharpe Ratio | {risk_metrics.get('estimated_sharpe_ratio', 'N/A')} |",
            "", "---", "",
            "*AI-assisted assessment only — not financial advice.*",
        ]

        if not output_filename:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"{client_id}_summary_{ts}.md"

        output_path = REPORTS_DIR / output_filename
        output_path.write_text("\n".join(lines))
        return str(output_path)
