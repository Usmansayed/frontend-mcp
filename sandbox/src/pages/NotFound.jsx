import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="center-screen">
      <div className="card" style={{ textAlign: 'center' }}>
        <h1>404</h1>
        <p className="muted">This branch of the maze does not exist.</p>
        <Link to="/">Return to start</Link>
      </div>
    </div>
  )
}
