param(
    [ValidateSet("Video", "All")]
    [string]$Scope = "Video"
)

$ErrorActionPreference = "Stop"

if (-not $env:AIHUB_API_KEY) {
    throw "AIHUB_API_KEY environment variable is not set. Set it in the current PowerShell session before running this script."
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$shellDir = Join-Path $repoRoot "datasets/aihub/traffic-accident-video/aihubshell"
$shellPath = Join-Path $shellDir "aihubshell"

if (-not (Test-Path $shellPath)) {
    throw "aihubshell not found at $shellPath"
}

$trainingVideoKeys = @(
    509290, 509291, 509292, 509293, 509294, 509295,
    509302, 509303, 509304, 509305, 509306, 509307,
    509314, 509315, 509316, 509317,
    509322, 509323, 509324, 509325, 509326, 509327, 509328, 509329
)

$validationVideoKeys = @(
    509386, 509387, 509388, 509389, 509390,
    509397, 509398, 509399, 509400, 509401,
    509408, 509409, 509410,
    509415, 509416, 509417, 509418, 509419, 509420, 509421, 509422
)

$trainingImageKeys = @(
    509296, 509297, 509298, 509299, 509300, 509301,
    509308, 509309, 509310, 509311, 509312, 509313,
    509318, 509319, 509320, 509321,
    509330, 509331, 509332, 509333, 509334, 509335, 509336, 509337
)

$validationImageKeys = @(
    509391, 509392, 509393, 509394, 509395, 509396,
    509402, 509403, 509404, 509405, 509406, 509407,
    509411, 509412, 509413, 509414,
    509423, 509424, 509425, 509426, 509427, 509428, 509429, 509430
)

$keys = @($trainingVideoKeys + $validationVideoKeys)
if ($Scope -eq "All") {
    $keys = @($keys + $trainingImageKeys + $validationImageKeys)
}

$fileKeyArg = ($keys -join ",")
$wslShellDir = "/mnt/c/Users/yangbun/Documents/OSS/Law_Compass/datasets/aihub/traffic-accident-video/aihubshell"

Write-Host "Downloading AI-Hub 597 label files. Scope=$Scope, Count=$($keys.Count)"
Write-Host "Download directory: $shellDir"
Write-Host "API key is read from AIHUB_API_KEY and will not be printed."

$bashCommand = @"
cd "$wslShellDir" &&
chmod +x ./aihubshell &&
./aihubshell -mode d -datasetkey 597 -filekey "$fileKeyArg" -aihubapikey "`$AIHUB_API_KEY"
"@

$env:AIHUB_API_KEY | wsl bash -lc "read AIHUB_API_KEY; export AIHUB_API_KEY; $bashCommand"
