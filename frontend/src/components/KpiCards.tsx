import React from 'react';
import type { DashboardSummary } from '../types';
import { DollarSign, TrendingUp, Award, CreditCard, Layers, Target } from 'lucide-react';

interface KpiCardsProps {
  summary: DashboardSummary | null;
  loading: boolean;
}

export const KpiCards: React.FC<KpiCardsProps> = ({ summary, loading }) => {
  const formatCurrency = (val?: number) => {
    if (val === undefined || val === null) return '$0';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(val);
  };

  if (loading) {
    return (
      <div className="kpi-grid">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} className="kpi-card skeleton-card">
            <div className="skeleton-line skeleton-title"></div>
            <div className="skeleton-line skeleton-value"></div>
            <div className="skeleton-line skeleton-sub"></div>
          </div>
        ))}
      </div>
    );
  }

  if (!summary) return null;

  return (
    <div className="kpi-grid">
      {/* 1. Revenue / TCV */}
      <div className="kpi-card card-revenue">
        <div className="kpi-header">
          <span className="kpi-title">Revenue (TCV Year 1)</span>
          <div className="kpi-icon-wrap icon-green">
            <DollarSign size={18} />
          </div>
        </div>
        <div className="kpi-value">{formatCurrency(summary.total_revenue)}</div>
        <div className="kpi-subtext">
          <span>Avg deal value: </span>
          <strong>{formatCurrency(summary.average_deal_value)}</strong>
        </div>
      </div>

      {/* 2. Total ARR */}
      <div className="kpi-card card-arr">
        <div className="kpi-header">
          <span className="kpi-title">Total ARR</span>
          <div className="kpi-icon-wrap icon-blue">
            <TrendingUp size={18} />
          </div>
        </div>
        <div className="kpi-value">{formatCurrency(summary.total_arr)}</div>
        <div className="kpi-subtext">
          <span>Recurring annual value booked</span>
        </div>
      </div>

      {/* 3. Total Commission */}
      <div className="kpi-card card-commission">
        <div className="kpi-header">
          <span className="kpi-title">Total Commission</span>
          <div className="kpi-icon-wrap icon-purple">
            <Award size={18} />
          </div>
        </div>
        <div className="kpi-value">{formatCurrency(summary.total_commission)}</div>
        <div className="kpi-subtext">
          <span>Formula-verified commission earned</span>
        </div>
      </div>

      {/* 4. Total Payouts */}
      <div className="kpi-card card-payout">
        <div className="kpi-header">
          <span className="kpi-title">Total Payouts</span>
          <div className="kpi-icon-wrap icon-amber">
            <CreditCard size={18} />
          </div>
        </div>
        <div className="kpi-value">{formatCurrency(summary.total_payouts)}</div>
        <div className="kpi-subtext">
          <span>Net scheduled payouts across milestones</span>
        </div>
      </div>

      {/* 5. Deals Count */}
      <div className="kpi-card card-deals">
        <div className="kpi-header">
          <span className="kpi-title">Total Deals</span>
          <div className="kpi-icon-wrap icon-indigo">
            <Layers size={18} />
          </div>
        </div>
        <div className="kpi-value">{summary.deal_count}</div>
        <div className="kpi-subtext">
          <span className="badge-closed-won">{summary.closed_won_deals} Closed Won</span>
        </div>
      </div>

      {/* 6. Target Attainment */}
      <div className="kpi-card card-target">
        <div className="kpi-header">
          <span className="kpi-title">Target Attainment</span>
          <div className="kpi-icon-wrap icon-teal">
            <Target size={18} />
          </div>
        </div>
        <div className="kpi-value">
          {(summary.target?.attainment_pct ?? 0).toFixed(1)}%
        </div>
        <div className="kpi-subtext target-note">
          <span className="target-label">MVP target: $100K/month</span>
          <span className="target-disclaimer" title={summary.target?.target_note}>
            {formatCurrency(summary.target?.target_amount)} for the Q3 plan period (display only)
          </span>
        </div>
      </div>
    </div>
  );
};
