import { useNavigate, useOutletContext } from 'react-router-dom'
import { useCart } from '../../../context/CartContext.jsx'

export default function ReviewStep() {
  const { data } = useOutletContext()
  const { items, total, clear } = useCart()
  const navigate = useNavigate()

  function placeOrder() {
    clear()
    navigate('/shop/checkout/confirmation')
  }

  return (
    <div className="card" style={{ maxWidth: 640 }}>
      <h3 style={{ marginTop: 0 }}>Review your order</h3>

      <h4>Items</h4>
      <table className="table">
        <tbody>
          {items.map((i) => (
            <tr key={i.id}><td>{i.name} × {i.qty}</td><td>${i.price * i.qty}</td></tr>
          ))}
          <tr><td><b>Total</b></td><td><b>${total}</b></td></tr>
        </tbody>
      </table>

      <h4>Ship to</h4>
      <p className="muted">{data.shipping?.name}, {data.shipping?.address}, {data.shipping?.city} ({data.shipping?.country})</p>

      <h4>Payment</h4>
      <p className="muted">{data.payment?.method}</p>

      <div className="row" style={{ justifyContent: 'space-between' }}>
        <button onClick={() => navigate('/shop/checkout/payment')}>← Back</button>
        <button className="success" onClick={placeOrder}>Place order</button>
      </div>
    </div>
  )
}
