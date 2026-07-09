import { useState } from 'react'

export default function Security() {
  const [twoFA, setTwoFA] = useState(false)
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)

  function submit(e) {
    e.preventDefault()
    if (!current) return setError('Enter your current password.')
    if (next.length < 6) return setError('New password must be at least 6 characters.')
    if (next !== confirm) return setError('Passwords do not match.')
    setError('')
    setDone(true)
  }

  return (
    <div>
      <h1>Security</h1>
      <div className="card" style={{ maxWidth: 520 }}>
        <div className="row" style={{ justifyContent: 'space-between' }}>
          <div>
            <b>Two-factor authentication</b>
            <div className="muted">Extra layer of protection.</div>
          </div>
          <button className={twoFA ? 'success' : ''} onClick={() => setTwoFA((v) => !v)}>
            {twoFA ? 'Enabled' : 'Enable'}
          </button>
        </div>
      </div>

      <form className="card" style={{ maxWidth: 520 }} onSubmit={submit}>
        <h3 style={{ marginTop: 0 }}>Change password</h3>
        <div className="field">
          <label>Current password</label>
          <input type="password" value={current} onChange={(e) => setCurrent(e.target.value)} />
        </div>
        <div className="field">
          <label>New password</label>
          <input type="password" value={next} onChange={(e) => setNext(e.target.value)} />
        </div>
        <div className="field">
          <label>Confirm new password</label>
          <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
        </div>
        {error && <div className="error-text">{error}</div>}
        {done && <div className="badge">Password updated ✓</div>}
        <div style={{ marginTop: 10 }}>
          <button className="primary" type="submit">Update password</button>
        </div>
      </form>
    </div>
  )
}
