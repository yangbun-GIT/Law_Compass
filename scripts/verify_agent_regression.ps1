param(
  [switch]$SkipDockerBuild
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot

function Invoke-Checked {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Label,
    [Parameter(Mandatory = $true)]
    [scriptblock]$Command
  )

  & $Command
  $exitCode = $LASTEXITCODE
  if ($null -ne $exitCode -and $exitCode -ne 0) {
    throw "$Label failed with exit code $exitCode"
  }
}

Push-Location $RepoRoot
try {
  if (-not $SkipDockerBuild) {
    Write-Host ""
    Write-Host "==> Docker compose build/start"
    Invoke-Checked "Docker compose build/start" { docker compose up --build -d }
  }

  Write-Host ""
  Write-Host "==> Agent compile check"
  Invoke-Checked "Agent compile check" { docker compose exec -T agent python -m compileall app scripts }

  Write-Host ""
  Write-Host "==> Agent internal route contract"
  Invoke-Checked "Agent internal route contract" { docker compose exec -T agent python scripts/check_internal_routes.py }

  Write-Host ""
  Write-Host "==> Agent regression scenarios"
  Invoke-Checked "Agent regression scenarios" { docker compose exec -T agent python scripts/test_agent_regression_scenarios.py }

  Write-Host ""
  Write-Host "==> Agent evidence search quality"
  Invoke-Checked "Agent evidence search quality" { docker compose exec -T agent python scripts/test_evidence_search_quality.py }

  Write-Host ""
  Write-Host "==> Agent evidence source resilience"
  Invoke-Checked "Agent evidence source resilience" { docker compose exec -T agent python scripts/test_evidence_source_resilience.py }

  Write-Host ""
  Write-Host "==> Agent quality packet"
  Invoke-Checked "Agent quality packet" { docker compose exec -T agent python scripts/test_agent_quality_report.py }

  Write-Host ""
  Write-Host "verify_agent_regression=passed"
} finally {
  Pop-Location
}
