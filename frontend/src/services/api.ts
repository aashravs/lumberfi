import type {
  AuthResponse,
  CalculateResponse,
  DashboardSummary,
  DealsResponse,
  ImportResponse,
  PayoutsResponse,
  PerformanceItem,
  TrendItem,
  User,
} from '../types';

const rawApiUrl = import.meta.env.VITE_API_URL;
const API_BASE =
  typeof rawApiUrl === 'string' && rawApiUrl.trim() !== '' && rawApiUrl !== 'undefined'
    ? rawApiUrl.trim().replace(/\/+$/, '')
    : '';

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

function getAuthHeader(): Record<string, string> {
  const token = localStorage.getItem('lumberfi_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const headers: Record<string, string> = {
    ...getAuthHeader(),
    ...(options.headers as Record<string, string>),
  };

  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    localStorage.removeItem('lumberfi_token');
    localStorage.removeItem('lumberfi_user');
    window.dispatchEvent(new Event('auth:unauthorized'));
    throw new ApiError('Session expired or unauthorized. Please log in again.', 401);
  }

  if (!response.ok) {
    let errorDetail = `Request failed (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson && errJson.detail) {
        errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore json parse error
    }
    throw new ApiError(errorDetail, response.status);
  }

  return response.json() as Promise<T>;
}

export const api = {
  // Auth
  async login(email: string, password: string): Promise<AuthResponse> {
    return request<AuthResponse>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  },

  async getMe(): Promise<User> {
    return request<User>('/api/auth/me');
  },

  // Dashboard
  async getDashboardSummary(): Promise<DashboardSummary> {
    return request<DashboardSummary>('/api/dashboard/summary');
  },

  async getDashboardPerformance(): Promise<PerformanceItem[]> {
    return request<PerformanceItem[]>('/api/dashboard/performance');
  },

  async getDashboardTrends(): Promise<TrendItem[]> {
    return request<TrendItem[]>('/api/dashboard/trends');
  },

  // Deals
  async getDeals(params: {
    start_date?: string;
    end_date?: string;
    deal_status?: string;
    deal_type?: string;
    owner?: string;
    sort?: string;
    limit?: number;
    offset?: number;
  }): Promise<DealsResponse> {
    const searchParams = new URLSearchParams();
    if (params.start_date) searchParams.append('start_date', params.start_date);
    if (params.end_date) searchParams.append('end_date', params.end_date);
    if (params.deal_status) searchParams.append('deal_status', params.deal_status);
    if (params.deal_type) searchParams.append('deal_type', params.deal_type);
    if (params.owner) searchParams.append('owner', params.owner);
    if (params.sort) searchParams.append('sort', params.sort);
    if (params.limit !== undefined) searchParams.append('limit', params.limit.toString());
    if (params.offset !== undefined) searchParams.append('offset', params.offset.toString());

    const qs = searchParams.toString();
    return request<DealsResponse>(`/api/deals${qs ? `?${qs}` : ''}`);
  },

  // Payouts
  async getPayouts(params: {
    owner?: string;
    component?: string;
    start_date?: string;
    end_date?: string;
    limit?: number;
    offset?: number;
  }): Promise<PayoutsResponse> {
    const searchParams = new URLSearchParams();
    if (params.owner) searchParams.append('owner', params.owner);
    if (params.component) searchParams.append('component', params.component);
    if (params.start_date) searchParams.append('start_date', params.start_date);
    if (params.end_date) searchParams.append('end_date', params.end_date);
    if (params.limit !== undefined) searchParams.append('limit', params.limit.toString());
    if (params.offset !== undefined) searchParams.append('offset', params.offset.toString());

    const qs = searchParams.toString();
    return request<PayoutsResponse>(`/api/payouts${qs ? `?${qs}` : ''}`);
  },

  // Admin
  async uploadDataset(file: File): Promise<ImportResponse> {
    const formData = new FormData();
    formData.append('file', file);
    return request<ImportResponse>('/api/admin/upload', {
      method: 'POST',
      body: formData,
    });
  },

  async calculateCommissions(planStartDate?: string, planEndDate?: string): Promise<CalculateResponse> {
    return request<CalculateResponse>('/api/admin/calculate', {
      method: 'POST',
      body: JSON.stringify({
        plan_start_date: planStartDate || '2026-07-01',
        plan_end_date: planEndDate || '2026-09-30',
      }),
    });
  },
};
