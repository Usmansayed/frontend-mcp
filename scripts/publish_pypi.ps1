# Publish frontend-perception-engine and frontend-mcp to PyPI (same version).
# Loads TWINE_* from ../../.env (pipy_username / pipy_password).
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

Write-Host "Building frontend-perception-engine..."
if (Test-Path dist) { Remove-Item -Recurse -Force dist }
python -m build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Uploading frontend-perception-engine..."
uvx twine upload dist/*
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$aliasDir = Join-Path $Root "packages\frontend-mcp"
Set-Location $aliasDir
if (Test-Path dist) { Remove-Item -Recurse -Force dist }

Write-Host "Building frontend-mcp alias..."
python -m build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Uploading frontend-mcp..."
uvx twine upload dist/*
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Done. Published both packages at version in pyproject.toml."
