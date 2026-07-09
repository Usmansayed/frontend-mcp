import { useState } from 'react'
import { useNavigate, useOutletContext } from 'react-router-dom'

export default function ShippingStep() {
  const { data, setData } = useOutletContext()
  const navigate = useNavigate()
  const [form, setForm] = useState(data.shipping || {})
  const [error, setError] = useState('')

  function next(e) {
    e.preventDefault()
    if (!form.name || !form.address || !form.city) {
      return setError('Name, address, and city are required.')
    }
    setData((d) => ({ ...d, shipping: form }))
    navigate('/shop/checkout/payment')
  }

  return (
    <form className="card" style={{ maxWidth: 560 }} onSubmit={next}>
      <h3 style={{ marginTop: 0 }}>Shipping details</h3>
      <div className="field">
        <label>Full name</label>
        <input value={form.name || ''} onChange={(e) => setForm({ ...form, name: e.target.value })} />
      </div>
      <div className="field">
        <label>Address</label>
        <input value={form.address || ''} onChange={(e) => setForm({ ...form, address: e.target.value })} />
      </div>
      <div className="grid cols-2">
        <div className="field">
          <label>City</label>
          <input value={form.city || ''} onChange={(e) => setForm({ ...form, city: e.target.value })} />
        </div>
        <div className="field">
          <label>Country</label>
          <select value={form.country || 'US'} onChange={(e) => setForm({ ...form, country: e.target.value })}>
            <option>US</option><option>UK</option><option>DE</option><option>IN</option>
          </select>
        </div>
      </div>
      {error && <div className="error-text">{error}</div>}
      <div className="row end">
        <button className="primary" type="submit">Continue to payment →</button>
      </div>
    </form>
  )
}
