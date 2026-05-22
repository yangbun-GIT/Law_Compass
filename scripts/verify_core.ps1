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
  Invoke-Step "Gateway tests" {
    Invoke-InDirectory "apps/gateway" {
      npm test
    }
  }

  Invoke-Step "Gateway build" {
    Invoke-InDirectory "apps/gateway" {
      npm run build
    }
  }

  Invoke-Step "Frontend build" {
    Invoke-InDirectory "apps/frontend" {
      npm run build
    }
  }

  Invoke-Step "Frontend display safety test" {
    Invoke-InDirectory "apps/frontend" {
      npm run test:display
    }
  }

  Invoke-Step "Frontend chat safety test" {
    Invoke-InDirectory "apps/frontend" {
      npm run test:chat
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
  Write-Host "verify_core=passed"
} finally {
  Pop-Location
}
