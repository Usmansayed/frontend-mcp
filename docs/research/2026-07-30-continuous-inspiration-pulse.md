# Continuous Parallel Inspiration Pulse (`1.2.0.dev65`)

**Goal:** Keep taking visual inspiration from the internet **fast and in parallel** for the whole design episode — not one collect then stop.

## Behavior

At `perception_session_start` for **greenfield / redesign / mockup** (medium+):

1. One-shot HTTP prefetch still runs (inspiration + creative_kit…).
2. **New:** `schedule_inspiration_pulse` starts a background loop:
   - HTTP discover wave (parallel providers, no primary browser)
   - Materialize OG/CDN thumbs into an inspiration blob session
   - Dedupe into a ring buffer (default max 24)
   - Sleep `PERCEPTION_INSPIRATION_PULSE_INTERVAL_S` (default 10s) → next wave
3. Surfaces on `card.inspiration_pulse` + `can_parallel` includes `inspiration`.
4. `perception_inspiration_pulse` reads the ring (no browser lock). `refresh=true` forces one light collect wave.
5. After structured look_lock (dev64), pulse **pauses** (`PERCEPTION_INSPIRATION_PULSE_AFTER_LOCK=0` default).
6. Cancels on `session_end`.

## Env

| Var | Default | Meaning |
|-----|---------|---------|
| `PERCEPTION_INSPIRATION_PULSE` | `1` | Enable loop |
| `PERCEPTION_INSPIRATION_PULSE_INTERVAL_S` | `10` | Seconds between waves |
| `PERCEPTION_INSPIRATION_PULSE_HARD_S` | `12` | Per-wave timeout |
| `PERCEPTION_INSPIRATION_PULSE_MAX_THUMBS` | `24` | Ring cap |
| `PERCEPTION_INSPIRATION_PULSE_AFTER_LOCK` | `0` | Keep pulsing after look_lock if `1` |

## Host loop

```
session_start → card.inspiration_pulse running
→ perception_inspiration_pulse (read thumbs)
→ LOOK many inspiration:* images
→ visual_feedback purpose=inspiration (primary_ref_ids + borrow)
→ implement from lock
```
