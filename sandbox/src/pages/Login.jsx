import { useState } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = location.state?.from || '/dashboard'

  function handleSubmit(e) {
    e.preventDefault()
    if (!username || !password) {
      setError('Both username and password are required.')
      return
    }
    if (password.length < 4) {
      setError('Password must be at least 4 characters.')
      return
    }
    login(username)
    navigate(from, { replace: true })
  }

  return (
    <div className="center-screen">
      <form className="card" style={{ width: 'min(380px, 92vw)' }} onSubmit={handleSubmit}>
        <h1 style={{ fontSize: '1.4rem' }}>Sign in</h1>
        <p className="muted">Use <code>admin</code> for the admin-only branch.</p>
        <div className="field">
          <label>Username</label>
          <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="admin" />
        </div>
        <div className="field">
          <label>Password</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••" />
        </div>
        {error && <div className="error-text">{error}</div>}
        <button className="primary" type="submit" style={{ width: '100%', marginTop: 8 }}>Continue</button>
        <p className="muted" style={{ marginBottom: 0, marginTop: 14 }}>
          <Link to="/">← Back home</Link>
        </p>
      </form>
    </div>
  )
}
