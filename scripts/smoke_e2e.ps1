param(
  [string]$BaseUrl = "http://localhost"
)

$ErrorActionPreference = "Stop"

function Invoke-Api($Method, $Path, $Body=$null, $Token=$null) {
  $headers = @{ "Content-Type" = "application/json"; "Idempotency-Key" = [guid]::NewGuid().ToString() }
  if ($Token) { $headers["Authorization"] = "Bearer $Token" }
  if ($Body) {
    return Invoke-RestMethod -Method $Method -Uri "$BaseUrl$Path" -Headers $headers -Body ($Body | ConvertTo-Json -Depth 8)
  }
  return Invoke-RestMethod -Method $Method -Uri "$BaseUrl$Path" -Headers $headers
}

$email = "smoke.user@example.com"
$pass = "password123"

try {
  Invoke-Api "POST" "/api/v1/auth/signup" @{ email=$email; password=$pass; display_name="스모크유저" } | Out-Null
} catch {
  Write-Host "signup skip: $($_.Exception.Message)"
}

$login = Invoke-Api "POST" "/api/v1/auth/login" @{ email=$email; password=$pass }
$token = $login.access_token

$case = Invoke-Api "POST" "/api/v1/cases" @{ title="스모크 테스트 케이스"; description_text="신호대기 후 후미 추돌" } $token
$caseId = $case.case.id

$result = Invoke-Api "POST" "/api/v1/cases/$caseId/analyze-text" @{ description_text="신호대기 중 후방 차량 추돌" } $token

Write-Host "[OK] case_id=$caseId result_id=$($result.result_id) trace_id=$($result.trace_id)"
