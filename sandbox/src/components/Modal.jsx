export default function Modal({ open, title, children, onClose, onConfirm, confirmLabel = 'Confirm' }) {
  if (!open) return null
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        {title && <h3 style={{ marginTop: 0 }}>{title}</h3>}
        <div>{children}</div>
        <div className="row end" style={{ marginTop: 18 }}>
          <button onClick={onClose}>Cancel</button>
          {onConfirm && (
            <button className="primary" onClick={onConfirm}>{confirmLabel}</button>
          )}
        </div>
      </div>
    </div>
  )
}
