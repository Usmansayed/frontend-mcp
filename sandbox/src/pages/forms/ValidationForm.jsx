import { useState } from 'react'

function validate(form) {
  const errors = {}
  if (!form.email.includes('@')) errors.email = 'Invalid email address.'
  if (!/^\d{10}$/.test(form.phone)) errors.phone = 'Phone must be exactly 10 digits.'
  if (Number(form.age) < 18) errors.age = 'Must be 18 or older.'
  if (!form.terms) errors.terms = 'You must accept the terms.'
  return errors
}

export default function ValidationForm() {
  const [form, setForm] = useState({ email: '', phone: '', age: '', terms: false })
  const [errors, setErrors] = useState({})
  const [ok, setOk] = useState(false)

  function submit(e) {
    e.preventDefault()
    const next = validate(form)
    setErrors(next)
    setOk(Object.keys(next).length === 0)
  }

  return (
    <form className="card" style={{ maxWidth: 520 }} onSubmit={submit}>
      <h3 style={{ marginTop: 0 }}>Validated form</h3>
      <div className="field">
        <label>Email</label>
        <input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        {errors.email && <div className="error-text">{errors.email}</div>}
      </div>
      <div className="field">
        <label>Phone (10 digits)</label>
        <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
        {errors.phone && <div className="error-text">{errors.phone}</div>}
      </div>
      <div className="field">
        <label>Age</label>
        <input type="number" value={form.age} onChange={(e) => setForm({ ...form, age: e.target.value })} />
        {errors.age && <div className="error-text">{errors.age}</div>}
      </div>
      <div className="row" style={{ marginBottom: 6 }}>
        <input
          type="checkbox"
          style={{ width: 'auto' }}
          checked={form.terms}
          onChange={(e) => setForm({ ...form, terms: e.target.checked })}
        />
        <span>I accept the terms</span>
      </div>
      {errors.terms && <div className="error-text">{errors.terms}</div>}
      {ok && <div className="badge" style={{ marginTop: 10 }}>Form is valid ✓</div>}
      <div style={{ marginTop: 12 }}>
        <button className="primary" type="submit">Validate & submit</button>
      </div>
    </form>
  )
}
