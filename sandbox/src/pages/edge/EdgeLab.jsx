import { useEffect, useMemo, useRef, useState } from 'react'

const ALL_ITEMS = Array.from({ length: 200 }, (_, i) => ({
  id: i + 1,
  label: `Virtual row #${i + 1}`,
}))

function isBetaEnabled() {
  const params = new URLSearchParams(window.location.search)
  return params.get('beta') === '1' || localStorage.getItem('ff_beta') === '1'
}

export default function EdgeLab() {
  const [betaOn, setBetaOn] = useState(isBetaEnabled)
  const [liveCount, setLiveCount] = useState(0)
  const [scrollTop, setScrollTop] = useState(0)
  const [editorText, setEditorText] = useState('')
  const [uploadName, setUploadName] = useState('')
  const [frameClicked, setFrameClicked] = useState(false)
  const [showUiError, setShowUiError] = useState(false)
  const listRef = useRef(null)

  useEffect(() => {
    const id = setInterval(() => setLiveCount((c) => c + 1), 400)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    setBetaOn(isBetaEnabled())
  }, [])

  useEffect(() => {
    if (new URLSearchParams(window.location.search).get('devtest') !== '1') return
    console.error('EDGE_LAB_CONSOLE_ERROR')
    fetch('/api/dev-insights-missing').catch(() => {})
  }, [])

  useEffect(() => {
    if (new URLSearchParams(window.location.search).get('devtestb') !== '1') return
    console.warn('EDGE_LAB_CONSOLE_WARN')
    fetch('/api/dev-insights-ok')
    fetch('/api/dev-insights-slow')
  }, [])

  const itemHeight = 36
  const viewportHeight = 220
  const start = Math.floor(scrollTop / itemHeight)
  const visibleCount = Math.ceil(viewportHeight / itemHeight) + 2
  const windowItems = useMemo(
    () => ALL_ITEMS.slice(start, start + visibleCount),
    [start, visibleCount],
  )

  function enableBetaFlag() {
    localStorage.setItem('ff_beta', '1')
    setBetaOn(true)
  }

  return (
    <div>
      <h1>Edge case lab</h1>
      <p className="muted">Phase 4 sandbox: feature flags, iframe, virtual list, editor, upload, live DOM.</p>

      <section className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Feature flag</h3>
        {betaOn ? (
          <div className="badge" data-testid="beta-feature">Beta feature enabled</div>
        ) : (
          <div>
            <p className="muted">Beta section hidden. Enable via <code>?beta=1</code> or the button.</p>
            <button className="primary" type="button" onClick={enableBetaFlag}>Enable beta flag</button>
          </div>
        )}
      </section>

      <section className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>iframe context</h3>
        <iframe
          title="edge-frame"
          data-testid="edge-iframe"
          style={{ width: '100%', height: 120, border: '1px solid #334' }}
          srcDoc={`<!doctype html><html><body style="font-family:sans-serif;padding:12px">
            <button id="frame-btn" onclick="document.getElementById('out').textContent='clicked'">Click inside frame</button>
            <span id="out"></span>
          </body></html>`}
        />
        {frameClicked && <div className="badge">Frame interaction recorded</div>}
        <button
          className="primary"
          type="button"
          style={{ marginTop: 8 }}
          onClick={() => {
            const frame = document.querySelector('[data-testid="edge-iframe"]')
            const doc = frame?.contentDocument
            doc?.getElementById('frame-btn')?.click()
            const out = doc?.getElementById('out')?.textContent
            if (out === 'clicked') setFrameClicked(true)
          }}
        >
          Probe iframe button
        </button>
      </section>

      <section className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Virtualized list</h3>
        <div
          ref={listRef}
          data-testid="virtual-list"
          style={{ height: viewportHeight, overflow: 'auto', border: '1px solid #334' }}
          onScroll={(e) => setScrollTop(e.currentTarget.scrollTop)}
        >
          <div style={{ height: ALL_ITEMS.length * itemHeight, position: 'relative' }}>
            {windowItems.map((item) => (
              <div
                key={item.id}
                data-row-id={item.id}
                style={{
                  position: 'absolute',
                  top: (item.id - 1) * itemHeight,
                  height: itemHeight,
                  left: 0,
                  right: 0,
                  padding: '8px 12px',
                  borderBottom: '1px solid #223',
                }}
              >
                {item.label}
              </div>
            ))}
          </div>
        </div>
        <p className="muted" data-testid="virtual-visible-count">Visible rows in DOM: {windowItems.length}</p>
      </section>

      <section className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Rich editor</h3>
        <div
          id="rich-editor"
          data-testid="rich-editor"
          contentEditable
          suppressContentEditableWarning
          className="card"
          style={{ minHeight: 80, padding: 12 }}
          onInput={(e) => setEditorText(e.currentTarget.textContent || '')}
        />
        {editorText.includes('edge-ok') && <div className="badge">Editor content verified</div>}
      </section>

      <section className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>File upload</h3>
        <input
          data-testid="file-input"
          type="file"
          onChange={(e) => setUploadName(e.target.files?.[0]?.name || '')}
        />
        {uploadName && <div className="badge" data-testid="upload-result">Uploaded: {uploadName}</div>}
      </section>

      <section className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Dev insights (Tier B)</h3>
        <p className="muted">
          Append <code>?devtestb=1</code> to auto-fire console.warn, API calls, and a slow request.
        </p>
        <button
          type="button"
          className="danger"
          onClick={() => setShowUiError(true)}
        >
          Show UI error banner
        </button>
        {showUiError && (
          <div className="error-text banner-error" style={{ marginTop: 12 }}>
            EDGE_LAB_UI_ERROR: validation banner visible
          </div>
        )}
      </section>

      <section className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Dev insights (Tier A)</h3>
        <p className="muted">
          Append <code>?devtest=1</code> to auto-fire console.error and a failing fetch.
        </p>
        <button
          type="button"
          className="danger"
          onClick={() => {
            throw new Error('EDGE_LAB_UNCAUGHT')
          }}
        >
          Trigger uncaught error
        </button>
      </section>

      <section className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Live DOM (no URL change)</h3>
        <p data-testid="live-counter">Live tick: {liveCount}</p>
      </section>
    </div>
  )
}
