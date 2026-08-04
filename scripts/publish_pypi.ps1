# Publish frontend-mcp (primary) + synced legacy engine alias (same VERSION — no skew).
# Loads TWINE_* from ../.env (pipy_username / pipy_password).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

$envFile = Join-Path $Root ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*pipy_username\s*=\s*(.+)\s*$') { $env:TWINE_USERNAME = $matches[1].Trim() }
        if ($_ -match '^\s*pipy_password\s*=\s*(.+)\s*$') { $env:TWINE_PASSWORD = $matches[1].Trim() }
    }
}

if (-not $env:TWINE_USERNAME -or -not $env:TWINE_PASSWORD) {
    Write-Error "Set TWINE_USERNAME and TWINE_PASSWORD (or pipy_* in .env)"
}

Set-Location $Root
$Version = (Get-Content (Join-Path $Root "VERSION") -Raw).Trim()
Write-Host "Publishing version $Version (primary: frontend-mcp)"

# Keep legacy alias pin in lockstep with VERSION.
$AliasPy = Join-Path $Root "packages\frontend-perception-engine\pyproject.toml"
$AliasText = Get-Content $AliasPy -Raw
$AliasText = [regex]::Replace($AliasText, '(?m)^version = ".*"$', "version = `"$Version`"")
$AliasText = [regex]::Replace(
    $AliasText,
    '(?m)^(dependencies = \[\r?\n\s*")frontend-mcp==[^"\s]+(")',
    "`${1}frontend-mcp==$Version`${2}"
)
Set-Content -Path $AliasPy -Value $AliasText -NoNewline

function Build-And-Upload([string]$ProjectDir, [string]$Label) {
    Write-Host "`n=== Building $Label ==="
    $dist = Join-Path $ProjectDir "dist"
    if (Test-Path $dist) { Remove-Item -Recurse -Force $dist }
    Push-Location $ProjectDir
    try {
        python -m build
        if ($LASTEXITCODE -ne 0) { throw "build failed for $Label" }
        Write-Host "Uploading $Label..."
        uvx twine upload dist/*
        if ($LASTEXITCODE -ne 0) { throw "upload failed for $Label" }
    } finally {
        Pop-Location
    }
}

# Primary first (full code), then legacy alias.
Build-And-Upload $Root "frontend-mcp"
Build-And-Upload (Join-Path $Root "packages\frontend-perception-engine") "frontend-perception-engine"

Write-Host "`nDone. Install with:"
Write-Host "  pip install --upgrade --pre frontend-mcp"
Write-Host "  # legacy also works: pip install --upgrade --pre frontend-perception-engine"
