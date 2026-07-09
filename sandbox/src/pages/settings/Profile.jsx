import { useState } from 'react'
import Modal from '../../components/Modal.jsx'
import { useAuth } from '../../context/AuthContext.jsx'

export default function Profile() {
  const { user } = useAuth()
  const [name, setName] = useState(user.username)
  const [bio, setBio] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [saved, setSaved] = useState(false)

  function confirmSave() {
    setModalOpen(false)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div>
      <h1>Profile</h1>
      <div className="card" style={{ maxWidth: 520 }}>
        <div className="field">
          <label>Display name</label>
          <input value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="field">
          <label>Bio</label>
          <textarea rows={3} value={bio} onChange={(e) => setBio(e.target.value)} />
        </div>
        <div className="row">
          <button className="primary" onClick={() => setModalOpen(true)}>Save changes</button>
          {saved && <span className="badge">Saved ✓</span>}
        </div>
      </div>

      <Modal
        open={modalOpen}
        title="Confirm changes"
        onClose={() => setModalOpen(false)}
        onConfirm={confirmSave}
        confirmLabel="Save"
      >
        Save profile updates for <b>{name}</b>?
      </Modal>
    </div>
  )
}
