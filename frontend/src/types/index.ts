// These types mirror the ACTUAL FastAPI response shapes.
// Source of truth: backend/app/api/dashboard.py, payouts.py, deals.py,
// admin.py and backend/app/services/commission_runner.py.

export type UserRole = 'Admin' | 'Manager' | 'AE';

export interface User {
  email: string;
  name?: string;
  role: UserRole;
  manager_email?: string | null;
  active: boolean;
  _id?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface AeRevenue {
  owner: string;
  revenue: number;
  deals: number;
}

// GET /api/dashboard/summary
export interface DashboardSummary {
  role: UserRole;
  user_name?: string;
  total_revenue: number;
  total_arr: number;
  total_commission: number;
  total_payouts: number;
  deal_count: number;
  closed_won_deals: number;
  average_deal_value: number;
  top_ae: AeRevenue | null;
  lowest_ae: AeRevenue | null;
  revenue_by_ae: AeRevenue[];
  target: {
    target_amount: number;
    attainment_pct: number;
    target_note: string;
  };
}

// GET /api/dashboard/performance -> PerformanceItem[]
export interface PerformanceItem {
  owner: string;
  revenue: number;
  arr: number;
  deals: number;
  commission: number;
  payout: number;
  target: number;
  target_attainment: number;
  target_note: string;
}

// GET /api/dashboard/trends -> TrendItem[]
export interface TrendItem {
  month: string;
  revenue: number;
  arr: number;
  commission: number;
  payouts: number;
  deals: number;
}

export interface Deal {
  deal_id: string;
  deal_name?: string;
  customer_name?: string;
  customer_id?: string;
  deal_owner?: string;
  deal_type?: string;
  deal_status?: string;
  close_date?: string;
  tcv_year1?: number;
  arr?: number;
  commission?: number;
}

export interface DealsResponse {
  deals: Deal[];
  total: number;
  limit: number;
  offset: number;
}

// Persisted payout document (backend/app/services/commission_runner.py)
export interface Payout {
  deal_id: string;
  deal_owner?: string;
  component: string;
  payout_date?: string | null;
  amount: number;
  sequence?: number;
}

export interface PayoutsResponse {
  payouts: Payout[];
  total: number;
  limit: number;
  offset: number;
}

export interface RowError {
  row?: number;
  row_number?: number;
  deal_id?: string;
  error?: string;
  errors?: unknown;
  [key: string]: unknown;
}

// POST /api/admin/upload
export interface ImportResponse {
  import_id: string;
  total_rows: number;
  successful_rows: number;
  failed_rows: number;
  errors: RowError[];
}

// POST /api/admin/calculate
export interface CalculateResponse {
  calculation_id: string;
  plan: { start_date: string; end_date: string };
  deals_calculated: number;
  deals_failed: number;
  payouts_generated: number;
  stale_payouts_removed: number;
  errors: RowError[];
  totals: {
    deals: number;
    commissions: number;
    payouts: number;
  };
}
