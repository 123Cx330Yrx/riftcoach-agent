param(
    [int]$WaitSeconds = 60
)

$ErrorActionPreference = "Stop"
$dockerExe = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
$localRoot = "C:\Users\33502\AppData\Local"
$run = Join-Path $localRoot "Docker\run"
$secrets = Join-Path $localRoot "docker-secrets-engine"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"

Get-Process -Name "Docker Desktop","com.docker.backend","com.docker.proxy" `
    -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3

foreach ($pair in @(
    @{ Source = $run; Destination = (Join-Path $localRoot "Docker\run-recovery-$stamp") },
    @{ Source = $secrets; Destination = (Join-Path $localRoot "docker-secrets-engine-recovery-$stamp") }
)) {
    if (Test-Path -LiteralPath $pair.Source) {
        Move-Item -LiteralPath $pair.Source -Destination $pair.Destination
    }
    New-Item -ItemType Directory -Path $pair.Source -Force | Out-Null
}

Start-Process -FilePath $dockerExe -WindowStyle Hidden
$deadline = (Get-Date).AddSeconds($WaitSeconds)
do {
    Start-Sleep -Seconds 5
    $result = docker info --format '{{.ServerVersion}} {{.Containers}}' 2>&1
    if ($LASTEXITCODE -eq 0) {
        $result
        exit 0
    }
} while ((Get-Date) -lt $deadline)

throw "Docker daemon did not become ready within $WaitSeconds seconds."
