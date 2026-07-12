# Figma Intelligence — Architecture

Connection + coordination layer over **southleft/figma-console-mcp**.

## Layers

### Connection Manager (`connection/`)

- `connect(pat)` — validate via console status, store PAT
- `disconnect()` — clear stored token
- `status()` — connected, token source
- Token file: `.cache/figma_tokens.json` (override: `FIGMA_TOKEN_PATH`)

### Session Manager (`session/`)

Persists active design context:

- `file_key`, `file_url`, `file_name`
- `active_page_id`, `active_frame_id`
- `selection_node_ids`
- `known_files` (recent files, max 20)

Session file: `.cache/figma_session.json` (override: `FIGMA_SESSION_PATH`)

### Figma Console MCP Adapter (`adapter/console.py`)

Internal methods (MCP tool names hidden from rest of codebase):

| Method | Console tool (internal) |
|--------|-------------------------|
| `connect()` | `figma_get_status` |
| `navigate()` | `figma_navigate` |
| `get_current_file()` | `figma_get_file_data` |
| `get_components()` | `figma_get_library_components` / kit fallback |
| `get_styles()` | `figma_get_styles` |
| `get_variables()` | `figma_get_variables` |
| `get_tokens()` | `figma_get_token_values` |
| `get_selection()` | status payload |

### Context Normalizer (`normalize/context.py`)

Maps raw payloads → `context_models.FigmaDesignContext`.

### Design Cache (`cache/store.py`)

In-memory TTL cache (default 120s). Keyed by file + page + frame + selection. Invalidated on session updates.

### Coordination Layer (`coordination/coordinator.py`)

`get_design_context(refresh=False)` — cache hit, or parallel MCP fetches + normalize + cache put.

### Health Monitor (`health/monitor.py`)

Connection status + console `health()` combined report.

## Service facade (`service.py`)

Primary API:

- `connect`, `disconnect`, `connection_status`, `health`
- `get_context`, `list_files`
- `set_active_file`, `set_active_page`, `set_active_frame`, `set_selection`

Legacy: `discover`, `run_pipeline`, `run_duplication_pipeline`.

## Boundaries

Do **not** add inspiration, critique, or component search here. Delegate to sibling intelligence modules after context is available.
