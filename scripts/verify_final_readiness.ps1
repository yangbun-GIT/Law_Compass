param(
  [switch]$SkipDockerBuild,
  [switch]$SkipDockerChecks,
  [string]$BaseUrl = "http://localhost"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot

function Invoke-Step {
  param(
    [string]$Name,
    [scriptblock]$Action
  )

  Write-Host ""
  Write-Host "==> $Name"
  & $Action
}

function Invoke-InDirectory {
  param(
    [string]$Path,
    [scriptblock]$Action
  )

  Push-Location (Join-Path $RepoRoot $Path)
  try {
    & $Action
  } finally {
    Pop-Location
  }
}

Push-Location $RepoRoot
try {
  Invoke-Step "Python compile: evaluation and operating risk scripts" {
    python -m py_compile `
      scripts/reference_evidence_alignment_eval.py `
      scripts/summarize_operating_risk.py `
      apps/worker/worker/frame_analysis.py
  }

  Invoke-Step "Agent source-status tests" {
    Invoke-InDirectory "apps/agent" {
      $env:PYTHONPATH='.'
      python -m pytest tests/test_evidence_source_status.py tests/test_expert_guidance_sections.py
    }
  }

  Invoke-Step "Reference hardening fixture and operating risk summary" {
    python scripts/verify_reference_hardening_fixture.py
    python scripts/summarize_operating_risk.py `
      --reference-guidance logs/video_accuracy/reference_hardening_fixture_smoke/resolved_guidance.json `
      --reference-evidence logs/video_accuracy/reference_hardening_fixture_smoke/resolved_evidence_alignment.json `
      --reference-calibration logs/video_accuracy/reference_hardening_fixture_smoke/resolved_calibration.json `
      --batch-output tests/fixtures/video_accuracy/reference_hardening_minimal/batch_aggregate_conflict_resolved.json `
      --output logs/operating_risk_summary.json
  }

  Invoke-Step "Gateway tests and build" {
    Invoke-InDirectory "apps/gateway" {
      npm test -- report-composer.test.ts
      npm run build
    }
  }

  Invoke-Step "Frontend build" {
    Invoke-InDirectory "apps/frontend" {
      npm run build
    }
  }

  if (-not $SkipDockerChecks) {
    if (-not $SkipDockerBuild) {
      Invoke-Step "Docker compose build/start" {
        docker compose up --build -d
      }
    }

    Invoke-Step "Agent regression guard" {
      powershell -ExecutionPolicy Bypass -File (Join-Path $RepoRoot "scripts\verify_agent_regression.ps1") -SkipDockerBuild
    }

    Invoke-Step "Gateway health through edge" {
      $health = Invoke-WebRequest -UseBasicParsing "$BaseUrl/health"
      if ($health.StatusCode -ne 200) {
        throw "Health check failed with HTTP $($health.StatusCode)"
      }
      Write-Host $health.Content
    }
  }

  Write-Host ""
  Write-Host "verify_final_readiness=passed"
} finally {
  Pop-Location
}
