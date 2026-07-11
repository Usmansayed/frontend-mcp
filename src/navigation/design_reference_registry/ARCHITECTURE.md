# Design Reference Registry

Stores **Design Snapshots** (not screenshots) as structural references for comparison.

## Flow

```text
Reference product (e.g. Linear dashboard)
        │
        ▼
Design Snapshot Engine
        │
        ▼
DesignReferenceRegistry.register()
        │
        ▼
User app snapshot → find_similar() → compare_snapshots() → recommendations
```

Comparison is structural (typography families, palette, spacing scale, patterns) — not image diff.

## API

```python
from navigation.design_reference_registry import DesignReferenceRegistry
from navigation.design_snapshot_engine import DesignSnapshot

registry = DesignReferenceRegistry(storage_path=Path('artifacts/references.json'))
registry.register('linear_dashboard', 'Linear Dashboard', snapshot, tags=['saas', 'dashboard'])
matches = registry.find_similar(current_snapshot)
```
