import { Link, useParams, useNavigate } from 'react-router-dom'
import { findProduct } from './data.js'
import { useCart } from '../../context/CartContext.jsx'

export default function ProductDetail() {
  const { productId } = useParams()
  const product = findProduct(productId)
  const { addItem } = useCart()
  const navigate = useNavigate()

  if (!product) {
    return <div className="card">Product not found. <Link to="/shop">Back to shop</Link></div>
  }

  return (
    <div>
      <Link to={`/shop/category/${product.category}`}>← Back to {product.category}</Link>
      <h1>{product.name}</h1>
      <div className="card" style={{ maxWidth: 560 }}>
        <p className="muted">{product.desc}</p>
        <h2>${product.price}</h2>
        <div className="row">
          <button className="primary" onClick={() => addItem(product)}>Add to cart</button>
          <button className="success" onClick={() => { addItem(product); navigate('/shop/cart') }}>
            Buy now
          </button>
        </div>
      </div>
    </div>
  )
}
