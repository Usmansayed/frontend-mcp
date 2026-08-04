import { Link } from 'react-router-dom'

const destinations = [
  { to: '/dashboard', title: 'Dashboard', desc: 'Analytics, reports, and nested widgets (auth required).' },
  { to: '/settings/profile', title: 'Settings', desc: 'Profile, security, notifications, and billing tabs.' },
  { to: '/shop', title: 'Shop', desc: 'Categories → products → detail → cart → checkout wizard.' },
  { to: '/forms', title: 'Forms', desc: 'Simple, validated, and multi-step wizard forms.' },
  { to: '/help/faq', title: 'Help Center', desc: 'Accordion FAQ, contact form, and article tree.' },
  { to: '/eval/flaws', title: 'Flaw Gallery', desc: 'Hidden-flaw surfaces for coordination / Ship Council eval.' },
]

export default function Home() {
  return (
    <div>
      <h1>Navigation Maze</h1>
      <p className="muted">
        A deliberately deep, branched frontend for testing the perception engine.
        Every path below leads to more sub-paths, modals, forms, and guarded routes.
      </p>
      <div className="grid cols-3">
        {destinations.map((d) => (
          <Link to={d.to} key={d.to} className="card" style={{ display: 'block' }}>
            <h3 style={{ marginTop: 0 }}>{d.title} →</h3>
            <p className="muted" style={{ marginBottom: 0 }}>{d.desc}</p>
          </Link>
        ))}
      </div>
    </div>
  )
}
