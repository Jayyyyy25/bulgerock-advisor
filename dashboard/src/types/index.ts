export interface Client {
  client_id: string;
  full_name: string;
  email?: string;
  phone?: string;
  risk_profile?: "conservative" | "moderate" | "aggressive";
  advisor_id?: string;
  aum?: number;
  updated_at?: string;
}

export interface AllocationItem {
  asset_class: string;
  total_value: number;
  pct: number;
}

export interface HoldingItem {
  ticker: string;
  security_name?: string;
  isin?: string;
  asset_class?: string;
  sector?: string;
  account_type?: string;
  quantity?: number;
  market_value: number;
}

export interface Portfolio {
  client_id: string;
  as_of_date?: string;
  total_aum_usd: number;
  allocation: AllocationItem[];
  top_holdings: HoldingItem[];
}

export interface Policy {
  policy_id: string;
  client_id: string;
  full_name?: string;
  policy_type?: string;
  insurer?: string;
  coverage_amount?: number;
  premium?: number;
  renewal_date?: string;
  days_until_renewal?: number;
  status?: string;
}
