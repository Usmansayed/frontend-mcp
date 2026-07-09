import { useState } from 'react'

export default function Tabs({ tabs }) {
  const [active, setActive] = useState(tabs[0]?.id)
  const current = tabs.find((t) => t.id === active)

  return (
    <div>
      <div className="tabs">
        {tabs.map((t) => (
          <button
            key={t.id}
            className={t.id === active ? 'active' : ''}
            onClick={() => setActive(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div>{current?.content}</div>
    </div>
  )
}
