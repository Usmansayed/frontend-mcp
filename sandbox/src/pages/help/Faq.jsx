import Accordion from '../../components/Accordion.jsx'

const items = [
  { id: 'q1', title: 'How do I navigate the maze?', body: 'Follow the navbar, sidebars, breadcrumbs, tabs, and buttons. Some routes are guarded by login.' },
  { id: 'q2', title: 'Which routes require authentication?', body: 'The whole Dashboard and Settings sections require login. Admin reports require the admin role.' },
  { id: 'q3', title: 'How deep does the checkout go?', body: 'Shop → product → cart → checkout (shipping → payment → review → confirmation).' },
  { id: 'q4', title: 'Are there modals?', body: 'Yes — the profile page and cart use confirmation modals.' },
]

export default function Faq() {
  return (
    <div className="card">
      <h3 style={{ marginTop: 0 }}>Frequently Asked Questions</h3>
      <Accordion items={items} />
    </div>
  )
}
