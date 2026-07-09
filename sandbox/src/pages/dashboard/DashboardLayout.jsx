import { NavLink, Outlet } from 'react-router-dom'
import Breadcrumbs from '../../components/Breadcrumbs.jsx'
import { useAuth } from '../../context/AuthContext.jsx'

export default function DashboardLayout() {
  const { user } = useAuth()
  return (
    <div className="body-area">
      <aside className="sidebar">
        <h4>Overview</h4>
        <NavLink to="/dashboard" end>Home</NavLink>
        <NavLink to="/dashboard/analytics">Analytics</NavLink>
        <h4>Reports</h4>
        <NavLink to="/dashboard/reports/weekly">Weekly</NavLink>
        <NavLink to="/dashboard/reports/monthly">Monthly</NavLink>
        {user.role === 'admin' && <NavLink to="/dashboard/reports/admin">Admin (restricted)</NavLink>}
        <h4>Team</h4>
        <NavLink to="/dashboard/team">Members</NavLink>
      </aside>
      <div className="content">
        <Breadcrumbs />
        <Outlet />
      </div>
    </div>
  )
}
