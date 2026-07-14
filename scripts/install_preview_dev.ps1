# Install experimental preview MCP (1.2.0.dev2) from PyPI or local wheels.
# Usage:
#   .\scripts\install_preview_dev.ps1              # PyPI (after publish)
#   .\scripts\install_preview_dev.ps1 -Local       # build + install from repo
param(
    [switch]$Local
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Version = "1.2.0.dev2"

if ($Local) {
    Set-Location $Root
    Write-Host "Building frontend-perception-engine $Version..."
    if (Test-Path dist) { Remove-Item -Recurse -Force dist }
    python -m build
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $engineWheel = Get-ChildItem dist -Filter "frontend_perception_engine-$Version-*.whl" | Select-Object -First 1
    if (-not $engineWheel) { Write-Error "Engine wheel not found in dist/" }
    pip install --force-reinstall $engineWheel.FullName

    $aliasDir = Join-Path $Root "packages\frontend-mcp"
    Set-Location $aliasDir
    if (Test-Path dist) { Remove-Item -Recurse -Force dist }
    Write-Host "Building frontend-mcp $Version..."
    python -m build
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $mcpWheel = Get-ChildItem dist -Filter "frontend_mcp-$Version-*.whl" | Select-Object -First 1
    if (-not $mcpWheel) { Write-Error "frontend-mcp wheel not found in packages/frontend-mcp/dist/" }
    pip install --force-reinstall $mcpWheel.FullName
} else {
    Write-Host "Installing preview from PyPI: frontend-mcp==$Version"
    pip install --upgrade "frontend-mcp==$Version" "frontend-perception-engine==$Version"
}

Write-Host ""
Write-Host "Installed versions:"
python -c "import importlib.metadata as m; print('  frontend-mcp:', m.version('frontend-mcp')); print('  frontend-perception-engine:', m.version('frontend-perception-engine'))"

Write-Host ""
Write-Host "Next: restart Cursor, ensure mcp.json uses frontend-mcp.exe with PYTHONPATH cleared."
Write-Host "See docs/PREVIEW_1.2.0.md for validation checklist."
