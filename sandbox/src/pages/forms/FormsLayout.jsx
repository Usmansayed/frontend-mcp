import { NavLink, Outlet } from 'react-router-dom'

export default function FormsLayout() {
  return (
    <div>
      <h1>Forms Playground</h1>
      <div className="pill-nav">
        <NavLink to="/forms/simple">Simple</NavLink>
        <NavLink to="/forms/validation">Validation</NavLink>
        <NavLink to="/forms/wizard">Wizard</NavLink>
      </div>
      <Outlet />
    </div>
  )
}
