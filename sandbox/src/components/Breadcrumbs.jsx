import { Link, useLocation } from 'react-router-dom'

export default function Breadcrumbs() {
  const location = useLocation()
  const segments = location.pathname.split('/').filter(Boolean)

  let path = ''
  const crumbs = segments.map((seg) => {
    path += `/${seg}`
    return { label: decodeURIComponent(seg), to: path }
  })

  return (
    <div className="breadcrumbs">
      <Link to="/">home</Link>
      {crumbs.map((c) => (
        <span key={c.to}>
          <span className="sep">/</span>
          <Link to={c.to}>{c.label}</Link>
        </span>
      ))}
    </div>
  )
}
