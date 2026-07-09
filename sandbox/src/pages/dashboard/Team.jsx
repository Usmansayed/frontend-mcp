import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'

const MEMBERS = [
  { id: 'ada', name: 'Ada Lovelace', role: 'Engineer' },
  { id: 'alan', name: 'Alan Turing', role: 'Architect' },
  { id: 'grace', name: 'Grace Hopper', role: 'Manager' },
]

export function TeamList() {
  const [query, setQuery] = useState('')
  const filtered = MEMBERS.filter((m) => m.name.toLowerCase().includes(query.toLowerCase()))
  return (
    <div>
      <h1>Team Members</h1>
      <div className="field" style={{ maxWidth: 300 }}>
        <input placeholder="Filter members…" value={query} onChange={(e) => setQuery(e.target.value)} />
      </div>
      <div className="grid cols-3">
        {filtered.map((m) => (
          <Link key={m.id} to={`/dashboard/team/${m.id}`} className="card" style={{ display: 'block' }}>
            <h3 style={{ marginTop: 0 }}>{m.name}</h3>
            <span className="badge">{m.role}</span>
          </Link>
        ))}
      </div>
    </div>
  )
}

export function TeamMember() {
  const { memberId } = useParams()
  const member = MEMBERS.find((m) => m.id === memberId)
  if (!member) return <div className="card">Member not found. <Link to="/dashboard/team">Back</Link></div>
  return (
    <div className="card">
      <Link to="/dashboard/team">← Team</Link>
      <h1>{member.name}</h1>
      <p className="muted">Role: {member.role}</p>
      <Link className="badge" to={`/dashboard/team/${member.id}/activity`}>View activity</Link>
    </div>
  )
}

export function TeamMemberActivity() {
  const { memberId } = useParams()
  return (
    <div className="card">
      <Link to={`/dashboard/team/${memberId}`}>← Back to member</Link>
      <h1>Activity: {memberId}</h1>
      <ul>
        <li>Merged PR #482</li>
        <li>Closed ticket OPS-19</li>
        <li>Deployed release v2.3</li>
      </ul>
    </div>
  )
}
