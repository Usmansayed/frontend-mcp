import { useParams, Link } from 'react-router-dom'

const REPORTS = {
  weekly: { title: 'Weekly Report', rows: [['Mon', 120], ['Tue', 98], ['Wed', 140]] },
  monthly: { title: 'Monthly Report', rows: [['Jan', 3200], ['Feb', 2980], ['Mar', 3610]] },
  admin: { title: 'Admin Report (restricted)', rows: [['Refunds', 42], ['Fraud flags', 3]] },
}

export default function Reports() {
  const { period } = useParams()
  const report = REPORTS[period]

  if (!report) {
    return (
      <div className="card">
        <p>Unknown report period.</p>
        <Link to="/dashboard/reports/weekly">Go to weekly</Link>
      </div>
    )
  }

  return (
    <div>
      <h1>{report.title}</h1>
      <div className="card">
        <table className="table">
          <thead><tr><th>Label</th><th>Value</th></tr></thead>
          <tbody>
            {report.rows.map(([k, v]) => (
              <tr key={k}><td>{k}</td><td>{v}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
