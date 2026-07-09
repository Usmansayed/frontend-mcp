import { useState } from 'react'
import { useNavigate, useOutletContext } from 'react-router-dom'

export default function PaymentStep() {
  const { data, setData } = useOutletContext()
  const navigate = useNavigate()
  const [form, setForm] = useState(data.payment || { method: 'card' })
  const [error, setError] = useState('')

  function next(e) {
    e.preventDefault()
    if (form.method === 'card') {
      if (!/^\d{12,19}$/.test((form.card || '').replace(/\s/g, ''))) {
        return setError('Enter a valid card number (12-19 digits).')
      }
    }
    setData((d) => ({ ...d, payment: form }))
    navigate('/shop/checkout/review')
  }

  return (
    <form className="card" style={{ maxWidth: 560 }} onSubmit={next}>
      <h3 style={{ marginTop: 0 }}>Payment</h3>
      <div className="field">
        <label>Method</label>
        <select value={form.method} onChange={(e) => setForm({ ...form, method: e.target.value })}>
          <option value="card">Credit card</option>
          <option value="paypal">PayPal</option>
          <option value="invoice">Invoice</option>
        </select>
      </div>
      {form.method === 'card' && (
        <div className="field">
          <label>Card number</label>
          <input value={form.card || ''} onChange={(e) => setForm({ ...form, card: e.target.value })} placeholder="4242 4242 4242 4242" />
        </div>
      )}
      {error && <div className="error-text">{error}</div>}
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <button type="button" onClick={() => navigate('/shop/checkout/shipping')}>← Back</button>
        <button className="primary" type="submit">Review order →</button>
      </div>
    </form>
  )
}
