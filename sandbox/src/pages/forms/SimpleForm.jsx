import { useState } from 'react'

export default function SimpleForm() {
  const [form, setForm] = useState({ firstName: '', lastName: '', newsletter: false })
  const [submitted, setSubmitted] = useState(null)

  function submit(e) {
    e.preventDefault()
    setSubmitted(form)
  }

  return (
    <div className="grid cols-2">
      <form className="card" onSubmit={submit}>
        <h3 style={{ marginTop: 0 }}>Basic form</h3>
        <div className="field">
          <label>First name</label>
          <input value={form.firstName} onChange={(e) => setForm({ ...form, firstName: e.target.value })} />
        </div>
        <div className="field">
          <label>Last name</label>
          <input value={form.lastName} onChange={(e) => setForm({ ...form, lastName: e.target.value })} />
        </div>
        <div className="row" style={{ marginBottom: 14 }}>
          <input
            type="checkbox"
            style={{ width: 'auto' }}
            checked={form.newsletter}
            onChange={(e) => setForm({ ...form, newsletter: e.target.checked })}
          />
          <span>Subscribe to newsletter</span>
        </div>
        <button className="primary" type="submit">Submit</button>
      </form>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Submitted payload</h3>
        <pre className="muted">{submitted ? JSON.stringify(submitted, null, 2) : 'Nothing submitted yet.'}</pre>
      </div>
    </div>
  )
}
