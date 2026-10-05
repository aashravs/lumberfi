import React, { useEffect, useState } from 'react';
import { api, ApiError } from '../services/api';
import type { Payout } from '../types';
import { ChevronLeft, ChevronRight, Info } from 'lucide-react';

interface PayoutsTableProps {
  userRole?: string;
}

// Real component values persisted by the calculation engine.
const COMPONENTS = [
  'Advance',
  'Balance',
  'Implementation',
  'Implementation - Signing',
  'Implementation - Go-Live',
  'Monthly Commission',
  'Quarterly Commission',
  'Cancellation Clawback',
];

const formatCurrency = (val?: number | null) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(val ?? 0);

const formatDate = (val?: string | null) => (val ? String(val).split('T')[0] : '—');

const componentClass = (comp?: string) => {
  const c = comp ?? '';
  if (c === 'Advance') return 'badge-advance';
  if (c.includes('Clawback')) return 'badge-clawback';
  if (c === 'Balance') return 'badge-collection';
  return 'badge-regular';
};

export const PayoutsTable: React.FC<PayoutsTableProps> = ({ userRole }) => {
  const [payouts, setPayouts] = useState<Payout[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [componentFilter, setComponentFilter] = useState<string>('');
  const [page, setPage] = useState<number>(0);
  const limit = 10;

  const isAE = userRole === 'AE';

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .getPayouts({ component: componentFilter || undefined, limit, offset: page * limit })
      .then((res) => {
        if (cancelled) return;
        setPayouts(Array.isArray(res.payouts) ? res.payouts : []);
        setTotal(res.total ?? 0);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(
          err instanceof ApiError && err.status === 403
            ? 'Access denied.'
            : err?.message || 'Failed to load payouts.'
        );
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [componentFilter, page]);

  const totalPages = Math.ceil(total / limit);
  const colSpan = isAE ? 5 : 6;

  return (
    <div className="table-card">
      <div className="table-header-block">
        <div>
          <h3 className="section-title">Payout Schedule</h3>
          <span className="section-subtitle">
            When each piece of commission is paid out, as produced by the calculation engine
          </span>
        </div>

        <div className="filters-bar">
          <select
            value={componentFilter}
            onChange={(e) => {
              setComponentFilter(e.target.value);
              setPage(0);
            }}
            className="filter-select"
          >
            <option value="">All Components</option>
            {COMPONENTS.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="payout-explainer-banner">
        <Info size={16} className="explainer-icon" />
        <div className="explainer-text">
          <strong>How payouts work:</strong> part of the commission is paid early as an{' '}
          <em>Advance</em>. The remaining <em>Balance</em> is paid after the customer pays, with the
          advance already deducted. A <em>Cancellation Clawback</em> is a negative payout that
          recovers commission on a cancelled deal.
        </div>
      </div>

      {error && <div className="status-banner error-banner">{error}</div>}

      <div className="table-responsive">
        <table className="data-table">
          <thead>
            <tr>
              <th>Deal</th>
              {!isAE && <th>Owner</th>}
              <th>Component</th>
              <th>#</th>
              <th>Payout Date</th>
              <th className="num-col highlight-col">Payout Amount</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={colSpan} className="loading-td">
                  <div className="spinner"></div> Loading payouts...
                </td>
              </tr>
            ) : payouts.length === 0 ? (
              <tr>
                <td colSpan={colSpan} className="empty-td">
                  No payouts found for this scope.
                </td>
              </tr>
            ) : (
              payouts.map((p, idx) => (
                <tr key={`${p.deal_id}-${p.component}-${p.sequence ?? idx}`}>
                  <td>
                    <span className="deal-code">{p.deal_id}</span>
                  </td>
                  {!isAE && (
                    <td>
                      <span className="owner-badge">{p.deal_owner || '—'}</span>
                    </td>
                  )}
                  <td>
                    <span className={`comp-badge ${componentClass(p.component)}`}>
                      {p.component || '—'}
                    </span>
                  </td>
                  <td className="text-muted">{p.sequence ?? '—'}</td>
                  <td className="payout-date-cell">
                    <strong>{formatDate(p.payout_date)}</strong>
                  </td>
                  <td
                    className={`num-col payout-amount-cell ${(p.amount ?? 0) < 0 ? 'negative-amount' : ''}`}
                  >
                    <strong>{formatCurrency(p.amount)}</strong>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="pagination-bar">
        <span className="pagination-info">
          Showing {payouts.length > 0 ? page * limit + 1 : 0} to {Math.min((page + 1) * limit, total)} of{' '}
          {total} payouts
        </span>
        <div className="pagination-controls">
          <button
            className="page-btn"
            disabled={page === 0 || loading}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
          >
            <ChevronLeft size={16} /> Prev
          </button>
          <span className="current-page">
            Page {page + 1} of {Math.max(1, totalPages)}
          </span>
          <button
            className="page-btn"
            disabled={page >= totalPages - 1 || loading}
            onClick={() => setPage((p) => p + 1)}
          >
            Next <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
};
