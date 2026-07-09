import { useState } from 'react'
import Stepper from '../../components/Stepper.jsx'

const STEPS = ['Account', 'Details', 'Confirm']

export default function WizardForm() {
  const [step, setStep] = useState(0)
  const [data, setData] = useState({ username: '', email: '', plan: 'free', agree: false })
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)

  function nextFromAccount() {
    if (!data.username || !data.email.includes('@')) return setError('Valid username and email required.')
    setError('')
    setStep(1)
  }
  function nextFromDetails() {
    if (!data.agree) return setError('You must agree to continue.')
    setError('')
    setStep(2)
  }

  if (done) {
    return (
      <div className="card" style={{ maxWidth: 520 }}>
        <h3>All set 🎉</h3>
        <p className="muted">Account <b>{data.username}</b> created on the <b>{data.plan}</b> plan.</p>
        <button onClick={() => { setDone(false); setStep(0); setData({ username: '', email: '', plan: 'free', agree: false }) }}>
          Restart wizard
        </button>
      </div>
    )
  }

  return (
    <div className="card" style={{ maxWidth: 560 }}>
      <Stepper steps={STEPS} currentIndex={step} />

      {step === 0 && (
        <div>
          <div className="field">
            <label>Username</label>
            <input value={data.username} onChange={(e) => setData({ ...data, username: e.target.value })} />
          </div>
          <div className="field">
            <label>Email</label>
            <input value={data.email} onChange={(e) => setData({ ...data, email: e.target.value })} />
          </div>
          {error && <div className="error-text">{error}</div>}
          <div className="row end"><button className="primary" onClick={nextFromAccount}>Next →</button></div>
        </div>
      )}

      {step === 1 && (
        <div>
          <div className="field">
            <label>Plan</label>
            <select value={data.plan} onChange={(e) => setData({ ...data, plan: e.target.value })}>
              <option value="free">Free</option>
              <option value="pro">Pro</option>
              <option value="team">Team</option>
            </select>
          </div>
          <div className="row" style={{ marginBottom: 8 }}>
            <input type="checkbox" style={{ width: 'auto' }} checked={data.agree} onChange={(e) => setData({ ...data, agree: e.target.checked })} />
            <span>I agree to the terms</span>
          </div>
          {error && <div className="error-text">{error}</div>}
          <div className="row" style={{ justifyContent: 'space-between' }}>
            <button onClick={() => setStep(0)}>← Back</button>
            <button className="primary" onClick={nextFromDetails}>Next →</button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div>
          <h3 style={{ marginTop: 0 }}>Confirm</h3>
          <pre className="muted">{JSON.stringify(data, null, 2)}</pre>
          <div className="row" style={{ justifyContent: 'space-between' }}>
            <button onClick={() => setStep(1)}>← Back</button>
            <button className="success" onClick={() => setDone(true)}>Create account</button>
          </div>
        </div>
      )}
    </div>
  )
}
