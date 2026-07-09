import Tabs from '../../components/Tabs.jsx'

export default function Analytics() {
  return (
    <div>
      <h1>Analytics</h1>
      <Tabs
        tabs={[
          { id: 'traffic', label: 'Traffic', content: <div className="card">Traffic is up 12% week over week.</div> },
          { id: 'funnels', label: 'Funnels', content: <div className="card">Checkout funnel conversion: 3.4%.</div> },
          { id: 'cohorts', label: 'Cohorts', content: <div className="card">Week-4 retention: 28%.</div> },
        ]}
      />
    </div>
  )
}
