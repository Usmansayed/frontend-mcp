import { Link, useParams } from 'react-router-dom'
import { CATEGORIES, productsByCategory } from './data.js'

export default function ProductList() {
  const { categoryId } = useParams()
  const category = CATEGORIES.find((c) => c.id === categoryId)
  const products = productsByCategory(categoryId)

  if (!category) {
    return <div className="card">Unknown category. <Link to="/shop">Back to shop</Link></div>
  }

  return (
    <div>
      <Link to="/shop">← All categories</Link>
      <h1>{category.name}</h1>
      <div className="grid cols-3">
        {products.map((p) => (
          <div className="card" key={p.id}>
            <h3 style={{ marginTop: 0 }}>{p.name}</h3>
            <p className="muted">{p.desc}</p>
            <div className="row" style={{ justifyContent: 'space-between' }}>
              <b>${p.price}</b>
              <Link className="badge" to={`/shop/product/${p.id}`}>Details →</Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
