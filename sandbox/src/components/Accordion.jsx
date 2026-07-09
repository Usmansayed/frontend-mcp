import { useState } from 'react'

export default function Accordion({ items }) {
  const [openId, setOpenId] = useState(null)

  return (
    <div>
      {items.map((item) => (
        <div className="accordion-item" key={item.id}>
          <button
            className="accordion-head"
            onClick={() => setOpenId((prev) => (prev === item.id ? null : item.id))}
          >
            {openId === item.id ? '▾ ' : '▸ '} {item.title}
          </button>
          {openId === item.id && <div className="accordion-body">{item.body}</div>}
        </div>
      ))}
    </div>
  )
}
