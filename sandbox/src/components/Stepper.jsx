export default function Stepper({ steps, currentIndex }) {
  return (
    <div className="stepper">
      {steps.map((label, idx) => {
        const state = idx === currentIndex ? 'active' : idx < currentIndex ? 'done' : ''
        return (
          <div className={`step ${state}`} key={label}>
            <span className="dot">{idx < currentIndex ? '✓' : idx + 1}</span>
            <span>{label}</span>
          </div>
        )
      })}
    </div>
  )
}
