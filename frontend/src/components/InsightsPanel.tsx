import React from 'react';
import type { DashboardSummary } from '../types';
import { Sparkles, Trophy, ArrowUpRight, CheckCircle2 } from 'lucide-react';

interface InsightsPanelProps {
  summary: DashboardSummary | null;
  userRole?: string;
}

const formatCurrency = (val: number | undefined | null) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(val ?? 0);

export const scopeLabel = (role?: string) =>
  role === 'Admin'
    ? 'Company-wide scope'
    : role === 'Manager'
    ? 'Your team scope'
    : 'Your personal scope';

export const InsightsPanel: React.FC<InsightsPanelProps> = ({ summary, userRole }) => {
  if (!summary) return null;

  const isAE = userRole === 'AE';
  const isManager = userRole === 'Manager';
  const isAdmin = userRole === 'Admin';

  const targetAmount = summary.target?.target_amount ?? 0;
  const attainment = summary.target?.attainment_pct ?? 0;
  const targetGap = Math.max(0, targetAmount - summary.total_revenue);
  const targetSurplus = Math.max(0, summary.total_revenue - targetAmount);

  return (
    <div className="insights-container">
      <div className="insights-header">
        <div className="insights-title-row">
          <Sparkles size={18} className="insight-sparkle-icon" />
          <h3>Insights</h3>
        </div>
        <span className="insights-scope-tag">{scopeLabel(userRole)}</span>
      </div>

      <div className="insights-grid">
        {isAE && (
          <>
            <div className="insight-card highlight-card">
              <div className="insight-icon"><Trophy size={20} /></div>
              <div className="insight-body">
                <h4>Target Progress</h4>
                <p>
                  You have achieved <strong>{attainment.toFixed(1)}%</strong> of your target
                  ({formatCurrency(targetAmount)} for the plan period at $100K/month).
                </p>
                {targetGap > 0 ? (
                  <span className="insight-sub">
                    You need <strong>{formatCurrency(targetGap)}</strong> more revenue to reach target.
                  </span>
                ) : (
                  <span className="insight-sub success-text">
                    You are <strong>{formatCurrency(targetSurplus)}</strong> above target.
                  </span>
                )}
              </div>
            </div>

            <div className="insight-card">
              <div className="insight-icon"><CheckCircle2 size={20} /></div>
              <div className="insight-body">
                <h4>Your Commission</h4>
                <p>
                  Your total commission is <strong>{formatCurrency(summary.total_commission)}</strong>{' '}
                  across <strong>{summary.deal_count}</strong> deal(s).
                </p>
                <span className="insight-sub">
                  Scheduled payouts: <strong>{formatCurrency(summary.total_payouts)}</strong>.
                </span>
              </div>
            </div>

            <div className="insight-card">
              <div className="insight-icon"><ArrowUpRight size={20} /></div>
              <div className="insight-body">
                <h4>Deals Closed</h4>
                <p>
                  <strong>{summary.closed_won_deals}</strong> Closed Won, average value{' '}
                  <strong>{formatCurrency(summary.average_deal_value)}</strong>.
                </p>
                <span className="insight-sub">
                  ARR booked: <strong>{formatCurrency(summary.total_arr)}</strong>.
                </span>
              </div>
            </div>
          </>
        )}

        {(isManager || isAdmin) && (
          <>
            <div className="insight-card highlight-card">
              <div className="insight-icon"><Trophy size={20} /></div>
              <div className="insight-body">
                <h4>Top Performer</h4>
                {summary.top_ae ? (
                  <p>
                    <strong>{summary.top_ae.owner}</strong> with{' '}
                    <strong>{formatCurrency(summary.top_ae.revenue)}</strong> revenue
                    {summary.total_revenue > 0 && (
                      <> ({((summary.top_ae.revenue / summary.total_revenue) * 100).toFixed(1)}% of {isAdmin ? 'company' : 'team'} revenue)</>
                    )}
                    .
                  </p>
                ) : (
                  <p>No AE data available yet.</p>
                )}
                {summary.lowest_ae && (
                  <span className="insight-sub">
                    Lowest: <strong>{summary.lowest_ae.owner}</strong> ({formatCurrency(summary.lowest_ae.revenue)}).
                  </span>
                )}
              </div>
            </div>

            <div className="insight-card">
              <div className="insight-icon"><ArrowUpRight size={20} /></div>
              <div className="insight-body">
                <h4>{isAdmin ? 'Company' : 'Team'} Revenue</h4>
                <p>
                  {isAdmin ? 'Company' : 'Team'} revenue is <strong>{formatCurrency(summary.total_revenue)}</strong>{' '}
                  across <strong>{summary.deal_count}</strong> deals ({summary.closed_won_deals} Closed Won).
                </p>
                <span className="insight-sub">
                  <strong>{attainment.toFixed(1)}%</strong> of aggregate MVP target ({formatCurrency(targetAmount)}).
                </span>
              </div>
            </div>

            <div className="insight-card">
              <div className="insight-icon"><CheckCircle2 size={20} /></div>
              <div className="insight-body">
                <h4>Commission & Payouts</h4>
                <p>
                  Total commission: <strong>{formatCurrency(summary.total_commission)}</strong>.
                </p>
                <span className="insight-sub">
                  Scheduled payouts: <strong>{formatCurrency(summary.total_payouts)}</strong>.
                </span>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
