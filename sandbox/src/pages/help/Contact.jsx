import { useState } from 'react'

export default function Contact() {
  const [form, setForm] = useState({ topic: 'general', email: '', message: '' })
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')

  function submit(e) {
    e.preventDefault()
    if (!form.email.includes('@')) return setError('Enter a valid email.')
    if (form.message.trim().length < 10) return setError('Message must be at least 10 characters.')
    setError('')
    setSent(true)
  }

  if (sent) {
    return (
      <div className="card">
        <h3>Thanks!</h3>
        <p className="muted">Your <b>{form.topic}</b> request was submitted.</p>
        <button onClick={() => { setSent(false); setForm({ topic: 'general', email: '', message: '' }) }}>
          Send another
        </button>
      </div>
    )
  }

  return (
    <form className="card" onSubmit={submit}>
      <h3 style={{ marginTop: 0 }}>Contact Support</h3>
      <div className="field">
        <label>Topic</label>
        <select value={form.topic} onChange={(e) => setForm({ ...form, topic: e.target.value })}>
          <option value="general">General</option>
          <option value="billing">Billing</option>
          <option value="bug">Bug report</option>
        </select>
      </div>
      <div className="field">
        <label>Email</label>
        <input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="you@example.com" />
      </div>
      <div className="field">
        <label>Message</label>
        <textarea rows={4} value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} />
      </div>
      {error && <div className="error-text">{error}</div>}
      <button className="primary" type="submit">Submit</button>
    </form>
  )
}
