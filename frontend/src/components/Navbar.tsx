import React from 'react';
import { useAuth } from '../context/AuthContext';
import { LogOut, Shield, Briefcase, UserCheck } from 'lucide-react';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();

  const getRoleBadge = (role?: string) => {
    switch (role) {
      case 'Admin':
        return (
          <span className="role-badge badge-admin">
            <Shield size={13} style={{ marginRight: 4 }} /> Admin
          </span>
        );
      case 'Manager':
        return (
          <span className="role-badge badge-manager">
            <Briefcase size={13} style={{ marginRight: 4 }} /> Manager
          </span>
        );
      case 'AE':
      default:
        return (
          <span className="role-badge badge-ae">
            <UserCheck size={13} style={{ marginRight: 4 }} /> Account Executive
          </span>
        );
    }
  };

  return (
    <header className="navbar-container">
      <div className="navbar-content">
        <div className="navbar-brand">
          <div className="brand-logo">L</div>
          <div className="brand-text">
            <span className="brand-title">Lumberfi</span>
            <span className="brand-subtitle">Commission Platform</span>
          </div>
        </div>

        <div className="navbar-actions">
          <div className="user-profile">
            <div className="user-info">
              <span className="user-name">{user?.name || user?.email}</span>
              <span className="user-email">{user?.email}</span>
            </div>
            {getRoleBadge(user?.role)}
          </div>

          <button className="logout-btn" onClick={logout} title="Sign out">
            <LogOut size={16} />
            <span>Logout</span>
          </button>
        </div>
      </div>
    </header>
  );
};
