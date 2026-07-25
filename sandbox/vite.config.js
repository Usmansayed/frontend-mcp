import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

function devInsights404Plugin() {
  return {
    name: 'dev-insights-404',
    configureServer(server) {
      server.middlewares.use('/api/dev-insights-missing', (_req, res) => {
        res.statusCode = 404
        res.setHeader('Content-Type', 'application/json')
        res.end(JSON.stringify({ error: 'not found' }))
      })
      server.middlewares.use('/api/dev-insights-ok', (_req, res) => {
        res.statusCode = 200
        res.setHeader('Content-Type', 'application/json')
        res.end(JSON.stringify({ ok: true }))
      })
      server.middlewares.use('/api/dev-insights-slow', (_req, res) => {
        setTimeout(() => {
          res.statusCode = 200
          res.setHeader('Content-Type', 'application/json')
          res.end(JSON.stringify({ ok: true, slow: true }))
        }, 2500)
      })
    },
  }
}

export default defineConfig({
  plugins: [react(), devInsights404Plugin()],
  server: {
    // Non-standard: avoid clashing with typical local apps on 3000/5173/8080.
    port: 18765,
    strictPort: true,
    host: true,
  },
})
