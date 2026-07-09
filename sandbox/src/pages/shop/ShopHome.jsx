import { Link } from 'react-router-dom'
import { CATEGORIES } from './data.js'

export default function ShopHome() {
  return (
    <div>
      <h1>Shop</h1>
      <p className="muted">Pick a category to drill into products.</p>
      <div className="grid cols-3">
        {CATEGORIES.map((c) => (
          <Link key={c.id} to={`/shop/category/${c.id}`} className="card" style={{ display: 'block' }}>
            <h3 style={{ marginTop: 0 }}>{c.name} →</h3>
          </Link>
        ))}
      </div>
    </div>
  )
}
