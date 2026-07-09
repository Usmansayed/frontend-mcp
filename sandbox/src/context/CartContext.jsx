import { createContext, useContext, useMemo, useState } from 'react'

const CartContext = createContext(null)

export function CartProvider({ children }) {
  const [items, setItems] = useState([])

  const value = useMemo(() => {
    const addItem = (product) =>
      setItems((prev) => {
        const found = prev.find((i) => i.id === product.id)
        if (found) {
          return prev.map((i) => (i.id === product.id ? { ...i, qty: i.qty + 1 } : i))
        }
        return [...prev, { ...product, qty: 1 }]
      })

    const removeItem = (id) => setItems((prev) => prev.filter((i) => i.id !== id))
    const clear = () => setItems([])
    const count = items.reduce((sum, i) => sum + i.qty, 0)
    const total = items.reduce((sum, i) => sum + i.qty * i.price, 0)

    return { items, addItem, removeItem, clear, count, total }
  }, [items])

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>
}

export function useCart() {
  const ctx = useContext(CartContext)
  if (!ctx) throw new Error('useCart must be used within CartProvider')
  return ctx
}
