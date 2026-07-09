import { useMemo, useState } from 'react'
import { Outlet, useLocation, Navigate } from 'react-router-dom'
import Stepper from '../../../components/Stepper.jsx'
import { useCart } from '../../../context/CartContext.jsx'

const STEPS = ['shipping', 'payment', 'review', 'confirmation']
const LABELS = ['Shipping', 'Payment', 'Review', 'Done']

export default function CheckoutLayout() {
  const location = useLocation()
  const { items } = useCart()
  const [data, setData] = useState({ shipping: {}, payment: {} })

  const currentStep = location.pathname.split('/').pop()
  const currentIndex = STEPS.indexOf(currentStep)

  const ctx = useMemo(() => ({ data, setData }), [data])

  // Block checkout entirely if cart is empty (unless already at confirmation).
  if (items.length === 0 && currentStep !== 'confirmation') {
    return <Navigate to="/shop/cart" replace />
  }

  return (
    <div>
      <h1>Checkout</h1>
      <Stepper steps={LABELS} currentIndex={currentIndex === -1 ? 0 : currentIndex} />
      <Outlet context={ctx} />
    </div>
  )
}
