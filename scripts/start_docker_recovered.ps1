#requires -Version 7.0
param(
    [ValidateRange(1, 600)]
    [int]$WaitSeconds = 60
)

$ErrorActionPreference = 'Stop'
$dockerCli = (Get-Command docker -CommandType Application | Select-Object -First 1).Source
$desktopExe = Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'
$localRoot = [Environment]::GetFolderPath('LocalApplicationData')

function Invoke-DockerBounded {
    param([string[]]$Arguments, [int]$TimeoutMilliseconds = 10000)
    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = [System.Diagnostics.ProcessStartInfo]::new($dockerCli)
    $process.StartInfo.UseShellExecute = $false
    $process.StartInfo.CreateNoWindow = $true
    $process.StartInfo.RedirectStandardOutput = $true
    $process.StartInfo.RedirectStandardError = $true
    foreach ($argument in $Arguments) { $process.StartInfo.ArgumentList.Add($argument) }
    try {
        $null = $process.Start()
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        $finished = $process.WaitForExit($TimeoutMilliseconds)
        if (-not $finished) {
            # Only terminate this script's timed-out CLI, never the backend,
            # Desktop, containers, or an unrelated process.
            try { $process.Kill() } catch { if (-not $process.HasExited) { throw } }
            $null = $process.WaitForExit(1000)
        }
        $streamsFinished = [System.Threading.Tasks.Task]::WaitAll(
            [System.Threading.Tasks.Task[]]@($stdout, $stderr), 1000)
        [pscustomobject]@{
            ExitCode = $(if ($finished) { $process.ExitCode } else { -1 })
            TimedOut = (-not $finished -or -not $streamsFinished)
            Output = $(if ($stdout.IsCompletedSuccessfully) { $stdout.Result.Trim() } else { '' })
            Error = $(if ($stderr.IsCompletedSuccessfully) { $stderr.Result.Trim() } else { '' })
        }
    } finally { $process.Dispose() }
}

function Get-DockerRuntimeProcesses {
    @(Get-Process -Name 'Docker Desktop', 'com.docker.backend', 'com.docker.proxy' `
        -ErrorAction SilentlyContinue)
}

$health = Invoke-DockerBounded -Arguments @('info', '--format', '{{.ServerVersion}}')
if ($health.ExitCode -eq 0 -and -not $health.TimedOut -and $health.Output) {
    "Docker daemon already healthy ($($health.Output)); no restart or filesystem changes."
    return
}
if (-not (Test-Path -LiteralPath $desktopExe -PathType Leaf)) {
    throw "Docker Desktop executable not found: $desktopExe"
}

# Stop through the vendor CLI, including its own deadline. Escalation still
# uses Docker's stop command; no blanket Stop-Process or file deletion.
if (@(Get-DockerRuntimeProcesses).Count) {
    $stopped = Invoke-DockerBounded -Arguments @('desktop', 'stop', '--timeout', '30') -TimeoutMilliseconds 35000
    if ($stopped.ExitCode -ne 0 -or $stopped.TimedOut -or @(Get-DockerRuntimeProcesses).Count) {
        $stopped = Invoke-DockerBounded -Arguments @('desktop', 'stop', '--force', '--timeout', '30') -TimeoutMilliseconds 35000
    }
    if ($stopped.ExitCode -ne 0 -or $stopped.TimedOut) {
        throw "Docker Desktop stop failed; no runtime directories changed. $($stopped.Error)"
    }
}
if (@(Get-DockerRuntimeProcesses).Count) {
    throw 'Docker Desktop/backend is still running; no runtime directories changed.'
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$pairs = @(
    @{ Parent = (Join-Path $localRoot 'Docker'); Name = 'run' },
    @{ Parent = $localRoot; Name = 'docker-secrets-engine' }
)
$moves = @()
# Validate both directories before changing either, in the same stopped window.
foreach ($pair in $pairs) {
    $parent = [System.IO.Path]::GetFullPath($pair.Parent)
    $parentItem = Get-Item -LiteralPath $parent -Force
    if (-not $parentItem.PSIsContainer -or ($parentItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
        throw "Unsafe runtime parent: $parent"
    }
    $source = [System.IO.Path]::GetFullPath((Join-Path $parent $pair.Name))
    $backup = [System.IO.Path]::GetFullPath($source + '-backup-' + $stamp)
    if ([System.IO.Path]::GetDirectoryName($source) -ne $parent -or
        [System.IO.Path]::GetDirectoryName($backup) -ne $parent -or
        (Test-Path -LiteralPath $backup)) {
        throw "Unsafe or existing runtime backup: $backup"
    }
    $exists = Test-Path -LiteralPath $source
    if ($exists) {
        $item = Get-Item -LiteralPath $source -Force
        if ((Resolve-Path -LiteralPath $source).ProviderPath -ne $source -or
            -not $item.PSIsContainer -or ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -or
            @(Get-ChildItem -LiteralPath $source -Directory -Force).Count) {
            throw "Unexpected runtime directory or subdirectory: $source"
        }
    }
    $moves += [pscustomobject]@{ Source = $source; Backup = $backup; Existed = $exists }
}
if (@(Get-DockerRuntimeProcesses).Count) {
    throw 'Docker restarted during preflight; no runtime directories changed.'
}
foreach ($move in $moves) {
    if ($move.Existed) {
        Move-Item -LiteralPath $move.Source -Destination $move.Backup
        "Runtime backup: $($move.Source) -> $($move.Backup)"
    }
    New-Item -ItemType Directory -Path $move.Source | Out-Null
}

Start-Process -FilePath $desktopExe -WindowStyle Hidden
$watch = [System.Diagnostics.Stopwatch]::StartNew()
do {
    $remaining = $WaitSeconds * 1000 - $watch.ElapsedMilliseconds
    if ($remaining -le 0) { break }
    $health = Invoke-DockerBounded -Arguments @('info', '--format', '{{.ServerVersion}}') `
        -TimeoutMilliseconds ([int][Math]::Min(5000, $remaining))
    if ($health.ExitCode -eq 0 -and -not $health.TimedOut -and $health.Output -and
        $watch.ElapsedMilliseconds -lt $WaitSeconds * 1000) {
        "Docker daemon ready ($($health.Output)); containers and data volumes were preserved."
        return
    }
    $remaining = $WaitSeconds * 1000 - $watch.ElapsedMilliseconds
    if ($remaining -gt 0) { Start-Sleep -Milliseconds ([int][Math]::Min(1000, $remaining)) }
} while ($watch.ElapsedMilliseconds -lt $WaitSeconds * 1000)
throw "Docker daemon did not become ready within $WaitSeconds seconds. Inspect the new Docker logs; do not repeatedly clear runtime directories. Last CLI error: $($health.Error)"
