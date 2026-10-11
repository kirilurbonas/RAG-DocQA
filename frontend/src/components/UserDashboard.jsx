import { useState, useEffect } from 'react';
import axios from 'axios';
import '../styles/dashboard.css';

export default function UserDashboard({ user }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await axios.get('/api/v1/analytics/user/stats');
      setStats(response.data);
    } catch (err) {
      setError('Failed to load statistics');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('userId');
    localStorage.removeItem('username');
    delete axios.defaults.headers.common['Authorization'];
    window.location.reload();
  };

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="header-content">
          <h1>Welcome, {user.username}!</h1>
          <button onClick={handleLogout} className="logout-btn">Logout</button>
        </div>
      </header>

      <div className="dashboard-nav">
        <button
          className={`nav-btn ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          Overview
        </button>
        <button
          className={`nav-btn ${activeTab === 'account' ? 'active' : ''}`}
          onClick={() => setActiveTab('account')}
        >
          Account
        </button>
      </div>

      <div className="dashboard-content">
        {activeTab === 'overview' && (
          <section className="tab-content">
            <h2>Usage Statistics</h2>
            {loading ? (
              <p>Loading statistics...</p>
            ) : error ? (
              <p className="error">{error}</p>
            ) : stats ? (
              <div className="stats-grid">
                <div className="stat-card">
                  <div className="stat-label">Total Events</div>
                  <div className="stat-value">{stats.total_events}</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">Total Tokens</div>
                  <div className="stat-value">{stats.total_tokens}</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">Avg Latency</div>
                  <div className="stat-value">{stats.avg_latency_ms}ms</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">Success Rate</div>
                  <div className="stat-value">{(stats.success_rate * 100).toFixed(1)}%</div>
                </div>
              </div>
            ) : null}

            {stats && stats.events_by_type && (
              <div className="events-breakdown">
                <h3>Events by Type</h3>
                <ul>
                  {Object.entries(stats.events_by_type).map(([type, count]) => (
                    <li key={type}>
                      <span className="event-type">{type}</span>
                      <span className="event-count">{count}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        )}

        {activeTab === 'account' && (
          <section className="tab-content">
            <h2>Account Settings</h2>
            <div className="account-info">
              <div className="info-item">
                <label>Username</label>
                <p>{user.username}</p>
              </div>
              <div className="info-item">
                <label>Email</label>
                <p>{user.email}</p>
              </div>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
