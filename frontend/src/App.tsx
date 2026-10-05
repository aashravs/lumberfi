import React, { useEffect, useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { KpiCards } from './components/KpiCards';
import { InsightsPanel, scopeLabel } from './components/InsightsPanel';
import { ChartsSection } from './components/ChartsSection';
import { DealsTable } from './components/DealsTable';
import { PayoutsTable } from './components/PayoutsTable';
import { AdminPanel } from './components/AdminPanel';
import { LoginView } from './components/LoginView';
import { api, ApiError } from './services/api';
import type { DashboardSummary, PerformanceItem, TrendItem } from './types';
import { RefreshCw } from 'lucide-react';
import './App.css';

const DashboardContent: React.FC = () => {
  const { user } = useAuth();

  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [performance, setPerformance] = useState<PerformanceItem[]>([]);
  const [trends, setTrends] = useState<TrendItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState<number>(0);

  const loadDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sumRes, perfRes, trendsRes] = await Promise.all([
        api.getDashboardSummary(),
        api.getDashboardPerformance(),
        api.getDashboardTrends(),
      ]);
      setSummary(sumRes);
      setPerformance(Array.isArray(perfRes) ? perfRes : []);
      setTrends(Array.isArray(trendsRes) ? trendsRes : []);
    } catch (err) {
      // 401 is handled globally (redirect to login); show everything else.
      if (err instanceof ApiError && err.status === 403) {
        setError('Access denied: your role cannot view this data.');
      } else if (!(err instanceof ApiError && err.status === 401)) {
        setError(err instanceof Error ? err.message : 'Failed to load dashboard data.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, [user?.email, user?.role, refreshKey]);

  const handleRefresh = () => {
    setRefreshKey((k) => k + 1);
  };

  return (
    <div className="app-container">
      <Navbar />

      <main className="dashboard-main">
        {/* Scope Banner */}
        <section className="scope-banner">
          <div>
            <h2 className="scope-heading">
              {user?.role === 'Admin'
                ? 'Enterprise Commission & Revenue Dashboard'
                : user?.role === 'Manager'
                ? 'Sales Management & Team Compensation'
                : `Sales Performance & Commission Portal — ${user?.name || ''}`}
            </h2>
            <p className="scope-sub">
              {scopeLabel(user?.role)} · live data from MongoDB Atlas
            </p>
          </div>
          <button
            className="scope-refresh-btn"
            onClick={handleRefresh}
            title="Refresh active metrics"
          >
            <RefreshCw size={14} className={loading ? 'spinner' : ''} />
            <span>Refresh Data</span>
          </button>
        </section>

        {error && <div className="status-banner error-banner">{error}</div>}

        {/* 1. KPI Cards */}
        <KpiCards summary={summary} loading={loading} />

        {/* 2. Business Insights Panel */}
        <InsightsPanel
          summary={summary}
          userRole={user?.role}
        />

        {/* 3. Role-Aware Interactive Visualizations */}
        <ChartsSection
          trends={trends}
          performance={performance}
          userRole={user?.role}
          loading={loading}
        />

        {/* 4. Admin Pipeline Controls (Only visible to Admin) */}
        {user?.role === 'Admin' && <AdminPanel onRecalculateSuccess={handleRefresh} />}

        {/* 5. Deals Table */}
        <DealsTable userRole={user?.role} key={`deals-${user?.email}-${refreshKey}`} />

        {/* 6. Payout Schedules Table */}
        <PayoutsTable userRole={user?.role} key={`payouts-${user?.email}-${refreshKey}`} />
      </main>
    </div>
  );
};

const MainShell: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="login-page">
        <div className="spinner"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginView />;
  }

  return <DashboardContent />;
};

export default function App() {
  return (
    <AuthProvider>
      <MainShell />
    </AuthProvider>
  );
}
