"""Component claim validator."""
from __future__ import annotations

from pathlib import Path

from navigation.resolver_intelligence.context import ResolverContext
from navigation.resolver_intelligence.contracts import CheckResult, ValidationResult
from navigation.resolver_intelligence.plugins.component import resolve_component

_EXPORT_PATTERNS = (
    "export function {name}",
    "export default function {name}",
    "export const {name}",
    "export default {name}",
)


def validate_component_claim(claim: dict, ctx: ResolverContext) -> ValidationResult:
    component_block = claim.get("component") or {}
    name = ""
    if isinstance(component_block, dict):
        name = str(component_block.get("name") or "").strip()
    name = name or str(claim.get("name") or "").strip()
    file_claim = str(claim.get("file") or "").strip()

    checks: list[CheckResult] = []
    if not name:
        checks.append(CheckResult("component_name_present", False, "claim.component.name required"))
        return ValidationResult(valid=False, checks=checks)

    file_path = Path(file_claim) if file_claim else None
    if file_path and not file_path.is_absolute():
        file_path = ctx.repo_root / file_path

    file_exists = bool(file_path and file_path.is_file())
    checks.append(CheckResult("file_exists", file_exists, str(file_path) if file_path else "missing"))

    exports_name = False
    duplicate_count = 0
    if file_exists and file_path is not None:
        text = file_path.read_text(encoding="utf-8", errors="replace")[:50_000]
        exports_name = any(p.format(name=name) in text for p in _EXPORT_PATTERNS)
        src = ctx.repo_layout.src_dir
        if src and src.is_dir():
            for candidate in src.rglob(f"*{name}*"):
                if candidate.suffix.lower() in {".jsx", ".tsx", ".js", ".ts"}:
                    duplicate_count += 1

    checks.append(CheckResult("exports_component", exports_name, name))
    checks.append(
        CheckResult(
            "duplicate_components",
            duplicate_count <= 1,
            f"found {duplicate_count} similarly named files",
        )
    )

    resolve_result = resolve_component(name, ctx)
    agrees = False
    if resolve_result.matches and file_claim:
        norm = file_claim.replace("\\", "/").lstrip("./")
        agrees = any(m.file_path.endswith(norm) for m in resolve_result.matches)
    elif resolve_result.matches and resolve_result.status.value == "resolved":
        agrees = True

    checks.append(
        CheckResult(
            "resolve_component_agrees",
            agrees,
            resolve_result.status.value,
        )
    )

    valid = all(c.passed for c in checks)
    return ValidationResult(
        valid=valid,
        checks=checks,
        mcp_resolve=resolve_result,
        normalized_match=resolve_result.matches[0] if agrees and resolve_result.matches else None,
    )
