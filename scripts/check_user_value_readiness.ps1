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

  Write-Host ""
  Write-Host "==> $Label"
  & $Command
  $exitCode = $LASTEXITCODE
  if ($null -ne $exitCode -and $exitCode -ne 0) {
    throw "$Label failed with exit code $exitCode"
  }
}

function Invoke-InDirectory {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Path,
    [Parameter(Mandatory = $true)]
    [scriptblock]$Command
  )

  Push-Location (Join-Path $RepoRoot $Path)
  try {
    & $Command
    $exitCode = $LASTEXITCODE
    if ($null -ne $exitCode -and $exitCode -ne 0) {
      throw "$Path command failed with exit code $exitCode"
    }
  } finally {
    Pop-Location
  }
}

Push-Location $RepoRoot
try {
  if (-not $SkipDockerBuild) {
    Invoke-Checked "Docker compose build/start" { docker compose up --build -d }
  }

  Invoke-Checked "Agent user-value contracts" {
    docker compose exec -T agent python -m pytest `
      tests/test_expert_guidance_sections.py `
      tests/test_elderly_report_support_language.py `
      tests/test_knia_report_integration.py `
      tests/test_orchestrator_e2e_modes.py `
      -q
  }

  Invoke-Checked "Reference metrics fixture" {
    python scripts/validate_reference_case_manifest.py `
      --manifest tests\fixtures\video_accuracy\reference_metrics_manifest.json `
      --output logs\video_accuracy\p12_3_reference_metrics_manifest_preflight.json
    python scripts\evaluate_video_reference_metrics.py `
      --reference-manifest tests\fixtures\video_accuracy\reference_metrics_manifest.json `
      --batch-aggregate tests\fixtures\video_accuracy\reference_metrics_batch_aggregate.json `
      --output logs\video_accuracy\p12_3_reference_metrics_fixture_eval.json `
      --fail-on-threshold
  }

  Invoke-InDirectory "apps/gateway" {
    Invoke-Checked "Gateway report and route tests" { npm test }
    Invoke-Checked "Gateway build" { npm run build }
  }

  Invoke-InDirectory "apps/frontend" {
    Invoke-Checked "Frontend display safety" { npm run test:display }
    Invoke-Checked "Frontend chat display safety" { npm run test:chat }
    Invoke-Checked "Frontend build" { npm run build }
  }

  Write-Host ""
  Write-Host "check_user_value_readiness=passed"
} finally {
  Pop-Location
}
