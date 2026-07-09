
## Implementation status

Phases 1–4 are implemented and tested. Run:

```bash
cd sandbox && npm run dev
cd ..
$env:PYTHONPATH="src"   # PowerShell
python src/run_all_phases.py
```

See [STAGES.md](STAGES.md) for the engine checklist (phases 1–4 ✅).  
**Program the coding agent to be the brain; give it a deterministic MCP runtime — and teach it how to work through playbooks, not API docs.**

See [MCP_PLAN.md](MCP_PLAN.md) for build milestones.  
**Agent behavior contract:** [AGENT_GUIDE.md](AGENT_GUIDE.md) — playbooks the host agent follows.

| Problem             | Industry solution                                                                 | What I'd build                                                                                                                                              | Phase |
| ------------------- | --------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ----- |
| Stateful SPA        | Persist browser contexts, cookies, localStorage, sessionStorage, reuse auth state | Build a **State Manager** that snapshots and restores browser state. Every discovered state gets an ID (`logged_in`, `project_created`, `cart_with_items`). | 2 ✅ |
| Silent validation   | Assertions + DOM verification instead of assuming success                         | Submit intentionally invalid data first, extract validation rules, then retry with valid data. Never trust button clicks alone.                             | 1 ✅ |
| Route guards        | Authentication fixtures and isolated browser contexts                             | Detect redirects, protected layouts, role checks, and annotate routes with prerequisites.                                                                   | 2 ✅ |
| Multi-step flows    | Page Object Models and explicit checkpoints                                       | Build a **Flow Graph** instead of a route graph. Each step becomes a verified checkpoint.                                                                   | 3 ✅ |
| DOM perception gaps | Accessibility tree + screenshots + assertions + traces                            | Combine a11y, DOM, screenshot, **Tier A/B dev insights**, **`scan_page()`** with preflight + degraded flags + token budget into one observation. | 1 ✅ |
| Unknown exploration | Hybrid heuristics + retries + verification                                        | Use CRG to suggest likely paths, Browser Use to execute, verifier to confirm.                                                                               | 4 ✅ |
| Feature flags       | Environment-aware testing                                                         | Detect unavailable routes and record them as feature-gated instead of failures.                                                                             | 4 ✅ |
| iframes             | Frame-aware automation                                                            | Treat each iframe as its own navigation context.                                                                                                            | 4 ✅ |
| Virtualized lists   | Smart scrolling                                                                   | Scroll until no new items appear before concluding exploration.                                                                                             | 4 ✅ |
| Rich editors        | Framework-specific handlers                                                       | Detect editors like Monaco, CodeMirror, TipTap and interact through their APIs when possible instead of treating them as plain inputs.                      | 4 ✅ |
| File uploads        | Native Playwright file APIs                                                       | Generate temporary test files and upload them programmatically.                                                                                             | 4 ✅ |
| CAPTCHA / MFA       | Stop immediately                                                                  | Mark the flow as "requires human authentication"; never let the agent loop.                                                                                 | 1 ✅ |
| WebSockets          | Observe state changes, not navigation                                             | Watch DOM mutations and network events instead of relying on URL changes.                                                                                   | 4 ✅ |


