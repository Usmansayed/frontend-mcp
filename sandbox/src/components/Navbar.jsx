import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { useCart } from '../context/CartContext.jsx'

export default function Navbar() {
  const { isAuthenticated, user, logout } = useAuth()
  const { count } = useCart()
  const navigate = useNavigate()

  return (
    <header className="navbar">
      <div className="brand">◆ MAZE</div>
      <nav>
        <NavLink to="/" end>Home</NavLink>
        <NavLink to="/dashboard">Dashboard</NavLink>
        <NavLink to="/settings">Settings</NavLink>
        <NavLink to="/shop">Shop</NavLink>
        <NavLink to="/forms">Forms</NavLink>
        <NavLink to="/help">Help</NavLink>
      </nav>
      <div className="spacer" />
      <NavLink to="/shop/cart">Cart ({count})</NavLink>
      {isAuthenticated ? (
        <div className="row">
          <span className="badge">{user.username} · {user.role}</span>
          <button onClick={() => { logout(); navigate('/') }}>Logout</button>
        </div>
      ) : (
        <button className="primary" onClick={() => navigate('/login')}>Login</button>
      )}
    </header>
  )
}
