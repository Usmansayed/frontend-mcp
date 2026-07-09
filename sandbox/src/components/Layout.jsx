import { Outlet } from 'react-router-dom'
import Navbar from './Navbar.jsx'
import Breadcrumbs from './Breadcrumbs.jsx'

export default function Layout() {
  return (
    <div className="app-shell">
      <Navbar />
      <div className="content" style={{ width: '100%', maxWidth: 'none' }}>
        <Breadcrumbs />
        <Outlet />
      </div>
    </div>
  )
}

export function SidebarLayout({ title, links, children }) {
  return (
    <div className="body-area">
      <aside className="sidebar">
        <h4>{title}</h4>
        {children}
      </aside>
      <div className="content">
        <Breadcrumbs />
        <Outlet />
      </div>
    </div>
  )
}
