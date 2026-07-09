export const CATEGORIES = [
  { id: 'audio', name: 'Audio' },
  { id: 'wearables', name: 'Wearables' },
  { id: 'home', name: 'Smart Home' },
]

export const PRODUCTS = [
  { id: 'p1', category: 'audio', name: 'Nimbus Headphones', price: 199, desc: 'Noise-cancelling over-ear headphones.' },
  { id: 'p2', category: 'audio', name: 'Pebble Earbuds', price: 89, desc: 'Compact wireless earbuds.' },
  { id: 'p3', category: 'wearables', name: 'Pulse Watch', price: 149, desc: 'Fitness + heart-rate tracking.' },
  { id: 'p4', category: 'wearables', name: 'Aura Ring', price: 249, desc: 'Sleep and recovery insights.' },
  { id: 'p5', category: 'home', name: 'Beacon Hub', price: 129, desc: 'Central smart-home controller.' },
  { id: 'p6', category: 'home', name: 'Glow Bulb', price: 29, desc: 'Color-changing smart bulb.' },
]

export const findProduct = (id) => PRODUCTS.find((p) => p.id === id)
export const productsByCategory = (cat) => PRODUCTS.filter((p) => p.category === cat)
