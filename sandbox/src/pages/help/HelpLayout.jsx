import { NavLink, Outlet } from 'react-router-dom'

export default function HelpLayout() {
  return (
    <div>
      <h1>Help Center</h1>
      <div className="pill-nav">
        <NavLink to="/help/faq">FAQ</NavLink>
        <NavLink to="/help/articles">Articles</NavLink>
        <NavLink to="/help/contact">Contact</NavLink>
      </div>
      <Outlet />
    </div>
  )
}
