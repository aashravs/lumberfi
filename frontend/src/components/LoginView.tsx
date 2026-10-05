import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Lock, Mail, AlertCircle, ArrowRight, ShieldCheck } from 'lucide-react';

export const LoginView: React.FC = () => {
  const { login } = useAuth();
  const [email, setEmail] = useState<string>('admin@gmail.com');
  const [password, setPassword] = useState<string>('demo123');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Please provide both email and password.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await login(email, password);
    } catch (err: any) {
      setError(err.message || 'Login failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  const fillDemoAccount = (demoEmail: string) => {
    setEmail(demoEmail);
    setPassword('demo123');
    setError(null);
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-brand">
          <div className="login-logo">L</div>
          <h2>Lumberfi</h2>
          <p className="login-tagline">Sales Commission & Incentive Compensation</p>
        </div>

        {error && (
          <div className="login-error-banner">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="login-email">Email Address</label>
            <div className="input-with-icon">
              <Mail size={16} className="input-icon" />
              <input
                id="login-email"
                type="email"
                required
                placeholder="name@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={loading}
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="login-password">Password</label>
            <div className="input-with-icon">
              <Lock size={16} className="input-icon" />
              <input
                id="login-password"
                type="password"
                required
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
              />
            </div>
          </div>

          <button type="submit" className="login-submit-btn" disabled={loading}>
            {loading ? (
              <>
                <div className="spinner-sm"></div> Authenticating...
              </>
            ) : (
              <>
                Sign In to Platform <ArrowRight size={16} />
              </>
            )}
          </button>
        </form>

        {/* Demo Fast-Login Helper */}
        <div className="demo-credentials-box">
          <div className="demo-box-header">
            <ShieldCheck size={14} />
            <span>Demo Test Accounts (Password: <code>demo123</code>)</span>
          </div>
          <div className="demo-buttons-grid">
            <button
              type="button"
              className="demo-account-btn admin-role"
              onClick={() => fillDemoAccount('admin@gmail.com')}
            >
              <strong>Admin:</strong> Aashrav
            </button>
            <button
              type="button"
              className="demo-account-btn manager-role"
              onClick={() => fillDemoAccount('manager@gmail.com')}
            >
              <strong>Manager:</strong> Test Manager
            </button>
            <button
              type="button"
              className="demo-account-btn ae-role"
              onClick={() => fillDemoAccount('aashrav04@gmail.com')}
            >
              <strong>AE:</strong> Ethan Kowalski
            </button>
            <button
              type="button"
              className="demo-account-btn ae-role"
              onClick={() => fillDemoAccount('sofia.brandt@lumberfi.com')}
            >
              <strong>AE:</strong> Sofia Brandt
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
