import { Link } from 'react-router-dom'

export default function Confirmation() {
  const orderId = 'ORD-' + Math.floor(100000 + Math.random() * 900000)
  return (
    <div className="card" style={{ maxWidth: 560, textAlign: 'center' }}>
      <h2>✓ Order confirmed</h2>
      <p className="muted">Your order <b>{orderId}</b> has been placed.</p>
      <div className="row" style={{ justifyContent: 'center' }}>
        <Link className="badge" to="/shop">Continue shopping</Link>
        <Link className="badge" to="/dashboard">Go to dashboard</Link>
      </div>
    </div>
  )
}
