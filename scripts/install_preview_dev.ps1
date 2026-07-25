# Install the single preview package: frontend-perception-engine
# (provides CLI entry points: frontend-mcp, frontend-perception-mcp).
# Usage:
#   .\scripts\install_preview_dev.ps1              # PyPI (after publish)
#   .\scripts\install_preview_dev.ps1 -Local       # build + install from repo
param(
    [switch]$Local
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Version = "1.2.0.dev46"
# Prefer Lib\site-packages — getsitepackages()[0] can be the conda prefix root.
$Site = python -c "import site; ps=site.getsitepackages(); print(next((p for p in ps if p.endswith('site-packages')), ps[-1]))"

function Clear-StaleFrontendDistInfo {
    param([string]$SitePackages)
    Get-ChildItem $SitePackages -Directory -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -like "frontend_perception_engine-*.dist-info" -or
            $_.Name -like "frontend_mcp-*.dist-info" -or
            $_.Name -like "__editable__.frontend_perception_engine-*" -or
            $_.Name -like "__editable__.frontend_mcp-*"
        } |
        ForEach-Object {
            Write-Host "Removing stale $($_.Name)"
            Remove-Item -Recurse -Force $_.FullName -ErrorAction SilentlyContinue
        }
    Get-ChildItem $SitePackages -Filter "__editable__*perception*.pth" -ErrorAction SilentlyContinue |
        Remove-Item -Force -ErrorAction SilentlyContinue
    Get-ChildItem $SitePackages -Filter "__editable__*frontend_mcp*.pth" -ErrorAction SilentlyContinue |
        Remove-Item -Force -ErrorAction SilentlyContinue
}

# Always drop the historical second package — it caused version skew.
# pip writes "Skipping ... not installed" to stderr; do not treat as terminating.
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
python -m pip uninstall -y frontend-mcp 2>$null | Out-Null
python -m pip uninstall -y frontend-perception-engine 2>$null | Out-Null
$ErrorActionPreference = $prevEap
Clear-StaleFrontendDistInfo -SitePackages $Site

if ($Local) {
    Set-Location $Root
    Write-Host "Building frontend-perception-engine $Version..."
    if (Test-Path dist) { Remove-Item -Recurse -Force dist }
    # python -m build writes WARNING to stderr; do not treat as terminating under Stop.
    $prevEapBuild = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    python -m build
    $buildExit = $LASTEXITCODE
    $ErrorActionPreference = $prevEapBuild
    if ($buildExit -ne 0) { exit $buildExit }
    $engineWheel = Get-ChildItem dist -Filter "frontend_perception_engine-$Version-*.whl" | Select-Object -First 1
    if (-not $engineWheel) { Write-Error "Engine wheel not found in dist/" }
    python -m pip install --force-reinstall --no-deps $engineWheel.FullName
} else {
    python -m pip install --pre --force-reinstall --no-cache-dir "frontend-perception-engine==$Version"
}

$eng = python -c "import importlib.metadata as m; print(m.version('frontend-perception-engine'))"
$mcpMod = python -c "import frontend_mcp; print(frontend_mcp.__version__)"
$aliasLeft = python -c "import importlib.metadata as m; print(any((d.metadata.get('Name') or '').lower()=='frontend-mcp' for d in m.distributions()))"
$dup = python -c "import importlib.metadata as m; print(sum(1 for d in m.distributions() if (d.metadata.get('Name') or '').lower()=='frontend-perception-engine'))"
Write-Host "Installed single package frontend-perception-engine==$Version"
Write-Host "  package_version     = $eng"
Write-Host "  frontend_mcp module = $mcpMod"
Write-Host "  engine dist-info    = $dup"
Write-Host "  old alias present   = $aliasLeft"
if ($eng.Trim() -ne $Version -or $mcpMod.Trim() -ne $Version) {
    Write-Error "Version mismatch after install (engine=$eng module=$mcpMod expected=$Version)."
}
if ($aliasLeft.Trim() -eq "True") {
    Write-Error "Old frontend-mcp alias still installed - uninstall it and retry."
}
if ([int]$dup.Trim() -ne 1) {
    Write-Error "Duplicate engine dist-info ($dup)."
}
Write-Host "Restart Cursor MCP. Health should show package_name=frontend-perception-engine and matching versions."
