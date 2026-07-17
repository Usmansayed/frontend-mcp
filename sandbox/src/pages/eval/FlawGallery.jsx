import { Link, useParams } from 'react-router-dom'
import './flaws.css'

/**
 * F1–F6: tricky pack (baseline).
 * F7–F12: hard pack — last difficult gate (decoy selectors, transform CB, left shell).
 */
const CASES = {
  F1: {
    title: 'Sticky without top (top:auto never pins)',
    badge: 'verify · chrome permanence',
    shellClass: 'flaw-shell',
    asideClass: 'flaw-aside flaw-aside--broken-sticky',
    mainClass: 'flaw-main',
    microOverflow: false,
    kpiMode: 'dominant',
  },
  F2: {
    title: 'Micro horizontal overflow (+10px ghost)',
    badge: 'verify · overflow',
    shellClass: 'flaw-shell',
    asideClass: 'flaw-aside flaw-aside--sticky',
    mainClass: 'flaw-main',
    microOverflow: true,
    kpiMode: 'dominant',
  },
  F3: {
    title: 'Near-equal KPI hierarchy (1.58→1.50rem)',
    badge: 'ship · hierarchy',
    shellClass: 'flaw-shell',
    asideClass: 'flaw-aside flaw-aside--sticky',
    mainClass: 'flaw-main',
    microOverflow: false,
    kpiMode: 'near_equal',
  },
  F4: {
    title: 'Subtle marketing-width shell (~58vw)',
    badge: 'ship · layout',
    shellClass: 'flaw-shell',
    asideClass: 'flaw-aside flaw-aside--sticky',
    mainClass: 'flaw-main flaw-main--narrow',
    microOverflow: false,
    kpiMode: 'dominant',
  },
  F5: {
    title: 'Sticky child / static aside trap',
    badge: 'verify · chrome trap',
    shellClass: 'flaw-shell',
    asideClass: 'flaw-aside flaw-aside--trap',
    mainClass: 'flaw-main',
    microOverflow: false,
    kpiMode: 'dominant',
    trap: true,
  },
  F6: {
    title: 'Sticky-without-top + near-equal KPIs',
    badge: 'both · verify + ship',
    shellClass: 'flaw-shell',
    asideClass: 'flaw-aside flaw-aside--broken-sticky',
    mainClass: 'flaw-main',
    microOverflow: false,
    kpiMode: 'near_equal',
  },
  F7: {
    title: 'Transform containing-block kills sticky',
    badge: 'hard · verify · transform CB',
    shellClass: 'flaw-shell',
    asideClass: 'flaw-aside flaw-aside--sticky',
    mainClass: 'flaw-main',
    microOverflow: false,
    kpiMode: 'dominant',
    transformHost: true,
  },
  F8: {
    title: 'Barely-over overflow (+3px vs +2 tolerance)',
    badge: 'hard · verify · overflow',
    shellClass: 'flaw-shell',
    asideClass: 'flaw-aside flaw-aside--sticky',
    mainClass: 'flaw-main',
    microOverflow: 'tiny',
    kpiMode: 'dominant',
  },
  F9: {
    title: 'Exact-equal KPI type (identical rem)',
    badge: 'hard · ship · hierarchy',
    shellClass: 'flaw-shell',
    asideClass: 'flaw-aside flaw-aside--sticky',
    mainClass: 'flaw-main',
    microOverflow: false,
    kpiMode: 'exact_equal',
  },
  F10: {
    title: 'Left-aligned compressed main (~62vw)',
    badge: 'hard · ship · layout',
    shellClass: 'flaw-shell',
    asideClass: 'flaw-aside flaw-aside--sticky',
    mainClass: 'flaw-main flaw-main--left-narrow',
    microOverflow: false,
    kpiMode: 'dominant',
    leftNarrow: true,
  },
  F11: {
    title: 'Decoy sticky nav hides static aside',
    badge: 'hard · verify · selector decoy',
    shellClass: 'flaw-shell flaw-shell--decoy',
    asideClass: 'flaw-aside',
    mainClass: 'flaw-main',
    microOverflow: false,
    kpiMode: 'dominant',
    decoyNav: true,
  },
  F12: {
    title: 'Transform + left shell + exact-equal KPIs',
    badge: 'hard · both · final boss',
    shellClass: 'flaw-shell',
    asideClass: 'flaw-aside flaw-aside--sticky',
    mainClass: 'flaw-main flaw-main--left-narrow',
    microOverflow: false,
    kpiMode: 'exact_equal',
    transformHost: true,
    leftNarrow: true,
  },
  F13: {
    title: 'overflow-x:hidden ancestor breaks sticky',
    badge: 'expert · verify · overflow containment',
    shellClass: 'flaw-shell flaw-shell--ox-hidden',
    asideClass: 'flaw-aside flaw-aside--sticky',
    mainClass: 'flaw-main',
    microOverflow: false,
    kpiMode: 'dominant',
  },
  F14: {
    title: 'Sticky with top:-80px (pins off-screen)',
    badge: 'expert · verify · negative top',
    shellClass: 'flaw-shell',
    asideClass: 'flaw-aside flaw-aside--sticky-neg',
    mainClass: 'flaw-main',
    microOverflow: false,
    kpiMode: 'dominant',
  },
  F15: {
    title: 'ox-hidden + decoy nav + exact-equal KPIs',
    badge: 'expert · both · production false-green',
    shellClass: 'flaw-shell flaw-shell--ox-hidden flaw-shell--decoy',
    asideClass: 'flaw-aside',
    mainClass: 'flaw-main',
    microOverflow: false,
    kpiMode: 'exact_equal',
    decoyNav: true,
  },
}

function Nav({ trap }) {
  const links = (
    <>
      <a className="active" href="#overview">Overview</a>
      <a href="#analytics">Analytics</a>
      <a href="#reports">Reports</a>
      <a href="#team">Team</a>
    </>
  )
  if (trap) {
    return <div className="flaw-aside-inner">{links}</div>
  }
  return links
}

function Kpis({ mode }) {
  if (mode === 'near_equal') {
    const items = [
      { label: 'Revenue', value: '$48.2k', cls: 'flaw-kpi--near-a' },
      { label: 'Users', value: '1,204', cls: 'flaw-kpi--near-b' },
      { label: 'Churn', value: '2.1%', cls: 'flaw-kpi--near-c' },
      { label: 'NPS', value: '61', cls: 'flaw-kpi--near-d' },
    ]
    return (
      <div className="flaw-kpis">
        {items.map((k) => (
          <section className={`flaw-kpi ${k.cls}`} key={k.label} data-kpi={k.label}>
            <div className="label">{k.label}</div>
            <div className="value">{k.value}</div>
          </section>
        ))}
      </div>
    )
  }
  if (mode === 'exact_equal') {
    const items = [
      { label: 'Revenue', value: '$48.2k' },
      { label: 'Users', value: '1,204' },
      { label: 'Churn', value: '2.1%' },
      { label: 'NPS', value: '61' },
    ]
    return (
      <div className="flaw-kpis">
        {items.map((k) => (
          <section className="flaw-kpi flaw-kpi--exact" key={k.label} data-kpi={k.label}>
            <div className="label">{k.label}</div>
            <div className="value">{k.value}</div>
          </section>
        ))}
      </div>
    )
  }
  return (
    <div className="flaw-kpis">
      <section className="flaw-kpi" data-kpi="Primary MRR">
        <div className="label">Primary MRR</div>
        <div className="value" style={{ fontSize: '2.1rem' }}>$128k</div>
      </section>
      <section className="flaw-kpi" data-kpi="Users">
        <div className="label">Users</div>
        <div className="value" style={{ fontSize: '1.2rem', opacity: 0.85 }}>1,204</div>
      </section>
      <section className="flaw-kpi" data-kpi="Churn">
        <div className="label">Churn</div>
        <div className="value" style={{ fontSize: '1.2rem', opacity: 0.85 }}>2.1%</div>
      </section>
      <section className="flaw-kpi" data-kpi="NPS">
        <div className="label">NPS</div>
        <div className="value" style={{ fontSize: '1.2rem', opacity: 0.85 }}>61</div>
      </section>
    </div>
  )
}

function AsideBlock({ cfg }) {
  const aside = (
    <aside className={cfg.asideClass} data-role="sidebar">
      <div style={{ fontWeight: 700, marginBottom: 12 }}>Acme Ops</div>
      <Nav trap={Boolean(cfg.trap)} />
    </aside>
  )
  if (cfg.transformHost) {
    return <div className="flaw-transform-host">{aside}</div>
  }
  return aside
}

export function FlawGalleryIndex() {
  return (
    <div style={{ padding: 32, background: '#0f1220', color: '#e6e8f2', minHeight: '100vh' }}>
      <h1>Flaw Gallery</h1>
      <p style={{ color: '#9aa0c0', maxWidth: 640 }}>
        Tricky + hard hidden flaws. Soft text criteria alone should not clear them.
        F7–F12 are the final hard gate.
      </p>
      <ul>
        {Object.entries(CASES).map(([id, c]) => (
          <li key={id} style={{ marginBottom: 8 }}>
            <Link to={`/eval/flaws/${id}`} style={{ color: '#6c8cff' }}>
              {id} — {c.title}
            </Link>
            <span style={{ color: '#9aa0c0', marginLeft: 8 }}>({c.badge})</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function FlawCase() {
  const { caseId } = useParams()
  const id = String(caseId || '').toUpperCase()
  const cfg = CASES[id]
  if (!cfg) {
    return (
      <div style={{ padding: 32, color: '#e6e8f2', background: '#0f1220', minHeight: '100vh' }}>
        <h1>Unknown flaw case</h1>
        <Link to="/eval/flaws" style={{ color: '#6c8cff' }}>Back to gallery</Link>
      </div>
    )
  }

  const centeredNarrow = cfg.mainClass.includes('flaw-main--narrow') && !cfg.leftNarrow
  const leftNarrow = Boolean(cfg.leftNarrow)
  const wrapMain = centeredNarrow || leftNarrow

  const page = (
    <>
      {cfg.decoyNav ? (
        <nav className="flaw-decoy-nav" role="navigation" aria-label="Breadcrumb">
          Home / Ops / Overview
        </nav>
      ) : null}
      <div className={cfg.shellClass} data-flaw-case={id}>
        <AsideBlock cfg={cfg} />
        <div
          className={
            centeredNarrow
              ? 'flaw-main-wrap'
              : leftNarrow
                ? 'flaw-main-wrap flaw-main-wrap--left'
                : undefined
          }
          style={wrapMain ? undefined : { flex: 1, minWidth: 0 }}
        >
          <main className={cfg.mainClass} role="main">
            <span className="flaw-badge">{id} · {cfg.badge}</span>
            <h1>Welcome, ops</h1>
            <p style={{ color: '#9aa0c0' }}>{cfg.title}. Marker text for soft verify: FlawCase {id}.</p>
            {cfg.microOverflow === true ? <div className="flaw-micro-overflow" aria-hidden="true" /> : null}
            {cfg.microOverflow === 'tiny' ? (
              <div className="flaw-micro-overflow flaw-micro-overflow--tiny" aria-hidden="true" />
            ) : null}
            <Kpis mode={cfg.kpiMode} />
            <div>
              <h2>Activity</h2>
              <p style={{ color: '#9aa0c0' }}>
                Tall content forces scroll so chrome permanence can be measured, not guessed from CSS alone.
              </p>
              {Array.from({ length: 40 }).map((_, i) => (
                <p key={i} style={{ color: '#9aa0c0', minHeight: 28 }}>
                  Row {i + 1}: synthetic activity so page height exceeds the viewport for scroll tests.
                </p>
              ))}
            </div>
          </main>
        </div>
      </div>
    </>
  )

  if (cfg.decoyNav) {
    return <div className="flaw-page-decoy">{page}</div>
  }
  return page
}
