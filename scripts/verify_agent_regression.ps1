param(
  [switch]$SkipDockerBuild
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot

Push-Location $RepoRoot
try {
  if (-not $SkipDockerBuild) {
    Write-Host ""
    Write-Host "==> Docker compose build/start"
    docker compose up --build -d
  }

  Write-Host ""
  Write-Host "==> Agent compile check"
  docker compose exec -T agent python -m compileall app scripts

  Write-Host ""
  Write-Host "==> Agent internal route contract"
  docker compose exec -T agent python scripts/check_internal_routes.py

  Write-Host ""
  Write-Host "==> Agent regression scenarios"
  docker compose exec -T agent python scripts/test_agent_regression_scenarios.py

  Write-Host ""
  Write-Host "verify_agent_regression=passed"
} finally {
  Pop-Location
}
