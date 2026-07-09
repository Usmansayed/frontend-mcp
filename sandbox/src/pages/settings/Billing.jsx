import { Link, useParams } from 'react-router-dom'

const PLANS = ['Free', 'Pro', 'Enterprise']
const INVOICES = [
  { id: 'INV-1001', amount: '$29.00', status: 'Paid' },
  { id: 'INV-1002', amount: '$29.00', status: 'Paid' },
  { id: 'INV-1003', amount: '$29.00', status: 'Due' },
]

export function BillingPlan() {
  return (
    <div>
      <h1>Plan</h1>
      <div className="grid cols-3">
        {PLANS.map((p) => (
          <div className="card" key={p}>
            <h3 style={{ marginTop: 0 }}>{p}</h3>
            <button className={p === 'Pro' ? 'primary' : ''}>{p === 'Pro' ? 'Current' : 'Choose'}</button>
          </div>
        ))}
      </div>
    </div>
  )
}

export function BillingInvoices() {
  return (
    <div>
      <h1>Invoices</h1>
      <div className="card">
        <table className="table">
          <thead><tr><th>Invoice</th><th>Amount</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {INVOICES.map((i) => (
              <tr key={i.id}>
                <td>{i.id}</td><td>{i.amount}</td><td>{i.status}</td>
                <td><Link to={`/settings/billing/invoices/${i.id}`}>View</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function InvoiceDetail() {
  const { invoiceId } = useParams()
  const invoice = INVOICES.find((i) => i.id === invoiceId)
  return (
    <div className="card">
      <Link to="/settings/billing/invoices">← Invoices</Link>
      <h1>{invoiceId}</h1>
      {invoice ? (
        <p className="muted">Amount {invoice.amount} — {invoice.status}</p>
      ) : (
        <p>Invoice not found.</p>
      )}
    </div>
  )
}
