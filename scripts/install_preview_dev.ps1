# Install experimental preview MCP (1.2.0.dev9) from PyPI or local wheels.
# Usage:
#   .\scripts\install_preview_dev.ps1              # PyPI (after publish)
#   .\scripts\install_preview_dev.ps1 -Local       # build + install from repo
param(
    [switch]$Local
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Version = "1.2.0.dev9"

if ($Local) {
    Set-Location $Root
    Write-Host "Building frontend-perception-engine $Version..."
    if (Test-Path dist) { Remove-Item -Recurse -Force dist }
    python -m build
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $engineWheel = Get-ChildItem dist -Filter "frontend_perception_engine-$Version-*.whl" | Select-Object -First 1
    if (-not $engineWheel) { Write-Error "Engine wheel not found in dist/" }

    Write-Host "Building frontend-mcp $Version..."
    Push-Location packages/frontend-mcp
    if (Test-Path dist) { Remove-Item -Recurse -Force dist }
    python -m build
    if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
    $mcpWheel = Get-ChildItem dist -Filter "frontend_mcp-$Version-*.whl" | Select-Object -First 1
    Pop-Location
    if (-not $mcpWheel) { Write-Error "MCP wheel not found in packages/frontend-mcp/dist/" }

    python -m pip install --force-reinstall --no-deps $engineWheel.FullName
    python -m pip install --force-reinstall $mcpWheel.FullName
} else {
    python -m pip install --pre --upgrade "frontend-perception-engine==$Version" "frontend-mcp==$Version"
}

Write-Host "Installed preview $Version. Restart Cursor MCP to pick up changes."
