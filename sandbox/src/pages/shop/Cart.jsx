import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useCart } from '../../context/CartContext.jsx'
import Modal from '../../components/Modal.jsx'

export default function Cart() {
  const { items, removeItem, clear, total } = useCart()
  const navigate = useNavigate()
  const [clearOpen, setClearOpen] = useState(false)

  if (items.length === 0) {
    return (
      <div>
        <h1>Cart</h1>
        <div className="card">
          <p className="muted">Your cart is empty.</p>
          <Link to="/shop">Browse products →</Link>
        </div>
      </div>
    )
  }

  return (
    <div>
      <h1>Cart</h1>
      <div className="card">
        <table className="table">
          <thead><tr><th>Item</th><th>Qty</th><th>Price</th><th></th></tr></thead>
          <tbody>
            {items.map((i) => (
              <tr key={i.id}>
                <td>{i.name}</td>
                <td>{i.qty}</td>
                <td>${i.price * i.qty}</td>
                <td><button className="danger" onClick={() => removeItem(i.id)}>Remove</button></td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="row" style={{ justifyContent: 'space-between', marginTop: 14 }}>
          <button className="danger" onClick={() => setClearOpen(true)}>Clear cart</button>
          <div className="row">
            <b>Total: ${total}</b>
            <button className="primary" onClick={() => navigate('/shop/checkout/shipping')}>Checkout →</button>
          </div>
        </div>
      </div>

      <Modal
        open={clearOpen}
        title="Clear cart?"
        onClose={() => setClearOpen(false)}
        onConfirm={() => { clear(); setClearOpen(false) }}
        confirmLabel="Clear"
      >
        This will remove all {items.length} item(s).
      </Modal>
    </div>
  )
}
