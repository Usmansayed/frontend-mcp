import { Link } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext.jsx'

export default function DashboardHome() {
  const { user } = useAuth()
  return (
    <div>
      <h1>Welcome, {user.username}</h1>
      <div className="grid cols-4">
        <div className="card"><div className="muted">Revenue</div><h2 style={{ margin: 0 }}>$48.2k</h2></div>
        <div className="card"><div className="muted">Users</div><h2 style={{ margin: 0 }}>1,204</h2></div>
        <div className="card"><div className="muted">Churn</div><h2 style={{ margin: 0 }}>2.1%</h2></div>
        <div className="card"><div className="muted">NPS</div><h2 style={{ margin: 0 }}>61</h2></div>
      </div>
      <div className="card">
        <h3 style={{ marginTop: 0 }}>Quick links</h3>
        <div className="row">
          <Link className="badge" to="/dashboard/analytics">Analytics</Link>
          <Link className="badge" to="/dashboard/reports/weekly">Weekly report</Link>
          <Link className="badge" to="/dashboard/team">Team</Link>
          <Link className="badge" to="/settings/profile">Profile settings</Link>
        </div>
      </div>
    </div>
  )
}
