import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { Deal } from '../types';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface DealsTableProps {
  userRole?: string;
}

export const DealsTable: React.FC<DealsTableProps> = ({ userRole }) => {
  const [deals, setDeals] = useState<Deal[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);

  // Filters state
  const [dealStatus, setDealStatus] = useState<string>('');
  const [dealType, setDealType] = useState<string>('');
  const [owner, setOwner] = useState<string>('');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [sort, setSort] = useState<string>('-close_date');
  const [page, setPage] = useState<number>(0);
  const limit = 10;

  const isAE = userRole === 'AE';

  const fetchDeals = async () => {
    setLoading(true);
    try {
      const res = await api.getDeals({
        deal_status: dealStatus || undefined,
        deal_type: dealType || undefined,
        owner: !isAE && owner ? owner : undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        sort,
        limit,
        offset: page * limit,
      });
      setDeals(res.deals);
      setTotal(res.total);
    } catch (err) {
      console.error('Failed to load deals', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDeals();
  }, [dealStatus, dealType, owner, startDate, endDate, sort, page]);

  const handleReset = () => {
    setDealStatus('');
    setDealType('');
    setOwner('');
    setStartDate('');
    setEndDate('');
    setSort('-close_date');
    setPage(0);
  };

  const formatCurrency = (val?: number) => {
    if (val === undefined || val === null) return '$0';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(val);
  };

  const formatDate = (val?: string) => {
    if (!val) return '—';
    try {
      return val.split('T')[0];
    } catch {
      return val;
    }
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="table-card">
      <div className="table-header-block">
        <div>
          <h3 className="section-title">Deals Portfolio</h3>
          <span className="section-subtitle">
            Showing {total} deals matching active criteria (Server-side RBAC enforced)
          </span>
        </div>

        {/* Filters bar */}
        <div className="filters-bar">
          <div className="filter-group">
            <select
              value={dealStatus}
              onChange={(e) => {
                setDealStatus(e.target.value);
                setPage(0);
              }}
              className="filter-select"
            >
              <option value="">All Statuses</option>
              <option value="Closed Won">Closed Won</option>
              <option value="Cancelled">Cancelled</option>
            </select>
          </div>

          <div className="filter-group">
            <select
              value={dealType}
              onChange={(e) => {
                setDealType(e.target.value);
                setPage(0);
              }}
              className="filter-select"
            >
              <option value="">All Deal Types</option>
              <option value="New">New</option>
              <option value="Upsell">Upsell</option>
            </select>
          </div>

          {!isAE && (
            <div className="filter-group">
              <input
                type="text"
                placeholder="Filter AE owner..."
                value={owner}
                onChange={(e) => {
                  setOwner(e.target.value);
                  setPage(0);
                }}
                className="filter-input"
              />
            </div>
          )}

          <div className="filter-group date-filters">
            <input
              type="date"
              value={startDate}
              onChange={(e) => {
                setStartDate(e.target.value);
                setPage(0);
              }}
              className="filter-date"
              title="Start Date"
            />
            <span className="date-separator">to</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => {
                setEndDate(e.target.value);
                setPage(0);
              }}
              className="filter-date"
              title="End Date"
            />
          </div>

          <div className="filter-group">
            <select
              value={sort}
              onChange={(e) => {
                setSort(e.target.value);
                setPage(0);
              }}
              className="filter-select"
            >
              <option value="-close_date">Date (Newest first)</option>
              <option value="close_date">Date (Oldest first)</option>
              <option value="-tcv_year1">TCV (High to Low)</option>
              <option value="tcv_year1">TCV (Low to High)</option>
            </select>
          </div>

          {(dealStatus || dealType || owner || startDate || endDate) && (
            <button className="reset-btn" onClick={handleReset}>
              Clear Filters
            </button>
          )}
        </div>
      </div>

      <div className="table-responsive">
        <table className="data-table">
          <thead>
            <tr>
              <th>Deal Name</th>
              <th>Customer</th>
              <th>Deal Owner</th>
              <th>Type</th>
              <th>Close Date</th>
              <th>Status</th>
              <th className="num-col">TCV</th>
              <th className="num-col">ARR</th>
              <th className="num-col">Commission</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={9} className="loading-td">
                  <div className="spinner"></div> Loading deals...
                </td>
              </tr>
            ) : deals.length === 0 ? (
              <tr>
                <td colSpan={9} className="empty-td">
                  No deals found matching the selected criteria.
                </td>
              </tr>
            ) : (
              deals.map((d) => (
                <tr key={d.deal_id}>
                  {/* Deal Name more prominent than Deal ID */}
                  <td>
                    <div className="deal-primary-name">{d.deal_name || 'Unnamed Deal'}</div>
                    <div className="deal-sub-id">{d.deal_id}</div>
                  </td>
                  <td>{d.customer_name || '—'}</td>
                  <td>
                    <span className="owner-badge">{d.deal_owner || '—'}</span>
                  </td>
                  <td>
                    <span className="type-badge">{d.deal_type || '—'}</span>
                  </td>
                  <td>{formatDate(d.close_date)}</td>
                  <td>
                    <span
                      className={`status-pill ${
                        d.deal_status === 'Closed Won'
                          ? 'status-won'
                          : d.deal_status === 'Cancelled'
                          ? 'status-lost'
                          : 'status-default'
                      }`}
                    >
                      {d.deal_status || '—'}
                    </span>
                  </td>
                  <td className="num-col font-medium">{formatCurrency(d.tcv_year1)}</td>
                  <td className="num-col">{formatCurrency(d.arr)}</td>
                  <td className="num-col commission-cell">
                    {formatCurrency(d.commission)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="pagination-bar">
        <span className="pagination-info">
          Showing {deals.length > 0 ? page * limit + 1 : 0} to{' '}
          {Math.min((page + 1) * limit, total)} of {total} deals
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
