param(
    [string]$PackageName = "deerflow-ads-backend.tar.gz",
    [switch]$IncludeEnv,
    [switch]$IncludePostgres
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..\..")
$DistDir = Join-Path $RepoRoot "dist"
$StageDir = Join-Path $DistDir "deerflow-ads-backend"
$PackagePath = Join-Path $DistDir $PackageName

function Test-PostgresConfig {
    param([string]$ConfigPath)

    if (-not (Test-Path $ConfigPath)) {
        return $false
    }

    $content = Get-Content -LiteralPath $ConfigPath -Raw
    return (
        $content -match '(?ms)^\s*database\s*:\s*.*?^\s*backend\s*:\s*[''"]?postgres(?:ql)?[''"]?\s*(?:#.*)?$' -or
        $content -match '(?ms)^\s*checkpointer\s*:\s*.*?^\s*type\s*:\s*[''"]?postgres(?:ql)?[''"]?\s*(?:#.*)?$'
    )
}

function Copy-RequiredFile {
    param(
        [string]$Source,
        [string]$Destination
    )

    if (-not (Test-Path $Source)) {
        throw "Missing required file: $Source"
    }
    Copy-Item -LiteralPath $Source -Destination $Destination -Force
}

function Copy-DirectoryFiltered {
    param(
        [string]$Source,
        [string]$Destination,
        [string[]]$ExcludedNames = @()
    )

    if (-not (Test-Path $Source)) {
        throw "Missing required directory: $Source"
    }

    $sourcePath = (Resolve-Path $Source).Path
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null

    Get-ChildItem -LiteralPath $sourcePath -Force | ForEach-Object {
        if ($ExcludedNames -contains $_.Name) {
            return
        }

        $target = Join-Path $Destination $_.Name
        Copy-Item -LiteralPath $_.FullName -Destination $target -Recurse -Force
    }
}

New-Item -ItemType Directory -Path $DistDir -Force | Out-Null
if (Test-Path $StageDir) {
    Remove-Item -LiteralPath $StageDir -Recurse -Force
}
New-Item -ItemType Directory -Path $StageDir -Force | Out-Null

Copy-RequiredFile `
    -Source (Join-Path $RepoRoot "deploy\ads\app.sh") `
    -Destination (Join-Path $StageDir "app.sh")
Copy-RequiredFile `
    -Source (Join-Path $RepoRoot "config.yaml") `
    -Destination (Join-Path $StageDir "config.yaml")
Copy-RequiredFile `
    -Source (Join-Path $RepoRoot "extensions_config.json") `
    -Destination (Join-Path $StageDir "extensions_config.json")

if ($IncludeEnv -and (Test-Path (Join-Path $RepoRoot ".env"))) {
    Copy-Item -LiteralPath (Join-Path $RepoRoot ".env") -Destination (Join-Path $StageDir ".env") -Force
} else {
    Copy-RequiredFile `
        -Source (Join-Path $RepoRoot ".env.example") `
        -Destination (Join-Path $StageDir ".env.example")
}

Copy-DirectoryFiltered `
    -Source (Join-Path $RepoRoot "backend") `
    -Destination (Join-Path $StageDir "backend") `
    -ExcludedNames @(
        ".venv",
        ".vscode",
        ".pytest_cache",
        ".ruff_cache",
        ".langgraph_api",
        ".deer-flow",
        ".mypy_cache",
        "tests",
        "__pycache__"
    )

Copy-DirectoryFiltered `
    -Source (Join-Path $RepoRoot "skills") `
    -Destination (Join-Path $StageDir "skills") `
    -ExcludedNames @("custom")

$uv = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uv) {
    $uv = Get-Command uv.exe -ErrorAction SilentlyContinue
}
if (-not $uv) {
    throw "uv is required to generate requirements.txt from backend/uv.lock."
}

Push-Location (Join-Path $RepoRoot "backend")
try {
    $configUsesPostgres = Test-PostgresConfig (Join-Path $RepoRoot "config.yaml")
    $envIncludePostgres = $env:INCLUDE_POSTGRES -eq "1" -or
        $env:UV_EXTRAS -match "(^|[,\s])postgres($|[,\s])" -or
        -not [string]::IsNullOrWhiteSpace($env:DATABASE_URL)
    $shouldIncludePostgres = $IncludePostgres -or $envIncludePostgres -or $configUsesPostgres
    $exportArgs = @("export", "--frozen", "--no-dev", "--format", "requirements.txt", "--no-hashes", "--no-header", "--no-annotate")
    if ($shouldIncludePostgres) {
        $exportArgs += @("--extra", "postgres")
        Write-Host "Including postgres extra dependencies in requirements.txt"
    }
    $requirements = & $uv.Source @exportArgs
} finally {
    Pop-Location
}

$requirementsText = $requirements |
    Where-Object {
        $line = $_.Trim()
        $line -and
            -not $line.StartsWith("#") -and
            -not $line.StartsWith("-e ./packages/harness")
    }

$requirementsPath = Join-Path $StageDir "requirements.txt"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllLines($requirementsPath, [string[]]$requirementsText, $utf8NoBom)

if ($shouldIncludePostgres -and -not ($requirementsText | Where-Object { $_ -match '^asyncpg==' })) {
    throw "Postgres dependencies were requested, but generated requirements.txt does not contain asyncpg. Check uv export --extra postgres."
}

if (Test-Path $PackagePath) {
    Remove-Item -LiteralPath $PackagePath -Force
}

Push-Location $DistDir
try {
    tar -czf $PackagePath "deerflow-ads-backend"
} finally {
    Pop-Location
}

Write-Host "ADS backend package created:"
Write-Host "  $PackagePath"
Write-Host ""
Write-Host "Upload and extract it in ADS, then run:"
Write-Host "  ./app.sh"
Write-Host ""
Write-Host "Postgres dependencies are included automatically when config.yaml uses postgres."
Write-Host "You can also force them with:"
Write-Host "  powershell -ExecutionPolicy Bypass -File deploy/ads/build-package.ps1 -IncludePostgres"
