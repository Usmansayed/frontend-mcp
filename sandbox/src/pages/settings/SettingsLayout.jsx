import { NavLink, Outlet } from 'react-router-dom'
import Breadcrumbs from '../../components/Breadcrumbs.jsx'

export default function SettingsLayout() {
  return (
    <div className="body-area">
      <aside className="sidebar">
        <h4>Account</h4>
        <NavLink to="/settings/profile">Profile</NavLink>
        <NavLink to="/settings/security">Security</NavLink>
        <NavLink to="/settings/notifications">Notifications</NavLink>
        <h4>Billing</h4>
        <NavLink to="/settings/billing/plan">Plan</NavLink>
        <NavLink to="/settings/billing/invoices">Invoices</NavLink>
      </aside>
      <div className="content">
        <Breadcrumbs />
        <Outlet />
      </div>
    </div>
  )
}
