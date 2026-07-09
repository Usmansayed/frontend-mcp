import { useState } from 'react'

const CHANNELS = ['Email', 'SMS', 'Push', 'Slack']

export default function Notifications() {
  const [prefs, setPrefs] = useState({ Email: true, SMS: false, Push: true, Slack: false })

  return (
    <div>
      <h1>Notifications</h1>
      <div className="card" style={{ maxWidth: 520 }}>
        {CHANNELS.map((c) => (
          <div className="row" key={c} style={{ justifyContent: 'space-between', padding: '8px 0' }}>
            <span>{c}</span>
            <button
              className={prefs[c] ? 'success' : ''}
              onClick={() => setPrefs((p) => ({ ...p, [c]: !p[c] }))}
            >
              {prefs[c] ? 'On' : 'Off'}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
