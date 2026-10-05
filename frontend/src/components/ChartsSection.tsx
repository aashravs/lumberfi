import React from 'react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from 'recharts';
import type { PerformanceItem, TrendItem } from '../types';

interface ChartsSectionProps {
  trends: TrendItem[];
  performance: PerformanceItem[];
  userRole?: string;
  loading: boolean;
}

export const ChartsSection: React.FC<ChartsSectionProps> = ({
  trends,
  performance,
  userRole,
  loading,
}) => {
  const isAE = userRole === 'AE';

  const formatCurrency = (val: number) => {
    if (val >= 1_000_000) return `$${(val / 1_000_000).toFixed(1)}M`;
    if (val >= 1_000) return `$${(val / 1_000).toFixed(0)}k`;
    return `$${val}`;
  };

  const formatFullCurrency = (val: number) =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(val);

  if (loading) {
    return (
      <div className="charts-grid">
        <div className="chart-card skeleton-card">
          <div className="skeleton-line skeleton-title"></div>
          <div className="skeleton-line skeleton-chart"></div>
        </div>
        <div className="chart-card skeleton-card">
          <div className="skeleton-line skeleton-title"></div>
          <div className="skeleton-line skeleton-chart"></div>
        </div>
      </div>
    );
  }

  const trendsList = Array.isArray(trends) ? trends : [];

  return (
    <div className="charts-grid">
      {/* Chart 1: Revenue by AE (Manager/Admin) OR Monthly Revenue vs Deals (AE) */}
      <div className="chart-card">
        <div className="chart-header">
          <div>
            <h3 className="chart-title">
              {isAE ? 'Your Monthly Revenue Performance' : 'Revenue by Account Executive'}
            </h3>
            <span className="chart-subtitle">
              {isAE
                ? 'Your revenue booked across active months'
                : 'Top revenue producers sorted descending'}
            </span>
          </div>
        </div>
        <div className="chart-body" style={{ width: '100%', height: 300 }}>
          {isAE ? (
            // AE view: own monthly revenue
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={trendsList} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="month" stroke="#64748b" />
                <YAxis tickFormatter={formatCurrency} stroke="#64748b" />
                <Tooltip
                  formatter={(val: any) => [formatFullCurrency(Number(val)), 'Revenue']}
                  contentStyle={{ backgroundColor: '#1e293b', color: '#fff', borderRadius: 8, border: 'none' }}
                />
                <Legend />
                <Bar dataKey="revenue" name="Revenue ($)" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            // Manager / Admin view: Horizontal bar chart by AE
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                layout="vertical"
                data={performance}
                margin={{ top: 10, right: 30, left: 40, bottom: 10 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis type="number" tickFormatter={formatCurrency} stroke="#64748b" />
                <YAxis dataKey="owner" type="category" stroke="#64748b" width={110} tick={{ fontSize: 12 }} />
                <Tooltip
                  formatter={(val: any) => [formatFullCurrency(Number(val)), 'Revenue']}
                  contentStyle={{ backgroundColor: '#1e293b', color: '#fff', borderRadius: 8, border: 'none' }}
                />
                <Bar dataKey="revenue" name="TCV Revenue" fill="#0ea5e9" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Chart 2: Monthly Revenue & ARR Trends */}
      <div className="chart-card">
        <div className="chart-header">
          <div>
            <h3 className="chart-title">Monthly Revenue & ARR Trend</h3>
            <span className="chart-subtitle">Historical closed-won trajectory</span>
          </div>
        </div>
        <div className="chart-body" style={{ width: '100%', height: 300 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={trendsList} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="month" stroke="#64748b" />
              <YAxis tickFormatter={formatCurrency} stroke="#64748b" />
              <Tooltip
                formatter={(val: any, name: any) => [formatFullCurrency(Number(val)), name]}
                contentStyle={{ backgroundColor: '#1e293b', color: '#fff', borderRadius: 8, border: 'none' }}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="revenue"
                name="TCV Revenue"
                stroke="#3b82f6"
                strokeWidth={3}
                dot={{ r: 5, fill: '#3b82f6' }}
                activeDot={{ r: 7 }}
              />
              <Line
                type="monotone"
                dataKey="arr"
                name="ARR"
                stroke="#10b981"
                strokeWidth={2}
                strokeDasharray="4 4"
                dot={{ r: 4, fill: '#10b981' }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Chart 3: Commission vs Payout Comparison */}
      <div className="chart-card full-width-chart">
        <div className="chart-header">
          <div>
            <h3 className="chart-title">Commission Accrual vs. Net Payouts</h3>
            <span className="chart-subtitle">
              Calculated commission obligations versus scheduled cash payouts by month
            </span>
          </div>
        </div>
        <div className="chart-body" style={{ width: '100%', height: 260 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={trendsList} margin={{ top: 10, right: 30, left: 10, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="month" stroke="#64748b" />
              <YAxis tickFormatter={formatCurrency} stroke="#64748b" />
              <Tooltip
                formatter={(val: any, name: any) => [formatFullCurrency(Number(val)), name]}
                contentStyle={{ backgroundColor: '#1e293b', color: '#fff', borderRadius: 8, border: 'none' }}
              />
              <Legend />
              <Bar dataKey="commission" name="Gross Commission" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
              <Bar dataKey="payouts" name="Scheduled Payouts" fill="#f59e0b" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};
