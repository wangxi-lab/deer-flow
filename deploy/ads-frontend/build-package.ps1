param(
    [string]$PackageName = "deerflow-ads-frontend.tar.gz",
    [string]$AppName = "deerflow-ads-frontend",
    [switch]$SkipBuild,
    [switch]$IncludeEnv
)

$ErrorActionPreference = "Stop"

if ($AppName -notmatch '^[A-Za-z0-9_.-]+$') {
    throw "AppName may only contain letters, numbers, underscore, hyphen, and dot."
}
if (-not $PackageName.EndsWith(".tar.gz")) {
    throw "PackageName must end with .tar.gz"
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..\..")
$FrontendRoot = Join-Path $RepoRoot "frontend"
$DistDir = Join-Path $RepoRoot "dist"
$StageDir = Join-Path $DistDir $AppName
$PackagePath = Join-Path $DistDir $PackageName

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

function New-RequiredJunction {
    param(
        [string]$Source,
        [string]$LinkPath
    )

    if (-not (Test-Path $Source)) {
        throw "Missing required directory: $Source"
    }

    $sourcePath = (Resolve-Path $Source).Path
    if (Test-Path $LinkPath) {
        cmd /c rmdir "$LinkPath" | Out-Null
    }

    cmd /c mklink /J "$LinkPath" "$sourcePath" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create junction '$LinkPath' -> '$sourcePath'"
    }
}

function Copy-DirectoryFast {
    param(
        [string]$Source,
        [string]$Destination
    )

    if (-not (Test-Path $Source)) {
        throw "Missing required directory: $Source"
    }

    if (Test-Path $Destination) {
        Remove-Item -LiteralPath $Destination -Recurse -Force
    }

    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    robocopy (Resolve-Path $Source).Path $Destination /E /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -gt 7) {
        throw "robocopy failed copying '$Source' to '$Destination' with exit code $LASTEXITCODE"
    }
}

function Remove-StageDirectory {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return
    }

    cmd /c rmdir /s /q "$Path" | Out-Null
}

if (-not $SkipBuild) {
    Push-Location $FrontendRoot
    try {
        if (-not (Test-Path "node_modules")) {
            pnpm install --frozen-lockfile
        }
        $env:SKIP_ENV_VALIDATION = "1"
        $env:NEXT_OUTPUT_STANDALONE = "1"
        pnpm build
    } finally {
        Remove-Item Env:SKIP_ENV_VALIDATION -ErrorAction SilentlyContinue
        Remove-Item Env:NEXT_OUTPUT_STANDALONE -ErrorAction SilentlyContinue
        Pop-Location
    }
}

New-Item -ItemType Directory -Path $DistDir -Force | Out-Null
if (Test-Path $StageDir) {
    Remove-StageDirectory -Path $StageDir
}
New-Item -ItemType Directory -Path $StageDir -Force | Out-Null

$StandaloneDir = Join-Path $FrontendRoot ".next\standalone"
if (-not (Test-Path $StandaloneDir)) {
    throw "Missing .next/standalone. Run without -SkipBuild once, or set NEXT_OUTPUT_STANDALONE=1 before pnpm build."
}

# Copy the minimal Next.js standalone runtime first. This includes server.js,
# package.json, .next/server, and the traced production node_modules.
robocopy $StandaloneDir $StageDir /E /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -gt 7) {
    throw "robocopy failed copying standalone runtime with exit code $LASTEXITCODE"
}

foreach ($path in @(
    ".env",
    ".env.local",
    "AGENTS.md",
    "CLAUDE.md",
    "Dockerfile",
    "Makefile",
    "README.md",
    "eslint.config.js",
    "playwright.config.ts",
    "prettier.config.js",
    "vitest.config.ts",
    "tsconfig.tsbuildinfo",
    "tests",
    "scripts"
)) {
    $target = Join-Path $StageDir $path
    if (Test-Path $target) {
        Remove-Item -LiteralPath $target -Recurse -Force
    }
}

# ADS requires src/ and node_modules/ as second-level directories. The runtime
# node_modules comes from .next/standalone; src is included for package layout
# compatibility and diagnostics.
Copy-DirectoryFast -Source (Join-Path $FrontendRoot "src") -Destination (Join-Path $StageDir "src")

# Next.js runtime assets and public files.
Copy-DirectoryFast -Source (Join-Path $FrontendRoot ".next\static") -Destination (Join-Path $StageDir ".next\static")
Copy-DirectoryFast -Source (Join-Path $FrontendRoot "public") -Destination (Join-Path $StageDir "public")

# Runtime/config files required by npm start / next start.
$requiredFiles = @(
    "next.config.js",
    "next-env.d.ts",
    "postcss.config.js",
    "tsconfig.json",
    "components.json"
)
foreach ($file in $requiredFiles) {
    $source = Join-Path $FrontendRoot $file
    if (Test-Path $source) {
        Copy-Item -LiteralPath $source -Destination (Join-Path $StageDir $file) -Force
    }
}

$runtimePackage = @{
    name = $AppName
    version = "0.1.0"
    private = $true
    scripts = @{
        start = "node server.js"
        stop = "echo stop"
    }
} | ConvertTo-Json -Depth 4
[System.IO.File]::WriteAllText(
    (Join-Path $StageDir "package.json"),
    $runtimePackage,
    (New-Object System.Text.UTF8Encoding($false))
)

# Keep lock/workspace files for diagnostics; runtime uses packaged node_modules.
foreach ($file in @("pnpm-lock.yaml", "pnpm-workspace.yaml", ".npmrc")) {
    $source = Join-Path $FrontendRoot $file
    if (Test-Path $source) {
        Copy-Item -LiteralPath $source -Destination (Join-Path $StageDir $file) -Force
    }
}

if ($IncludeEnv) {
    foreach ($file in @(".env", ".env.local")) {
        $source = Join-Path $FrontendRoot $file
        if (Test-Path $source) {
            Copy-Item -LiteralPath $source -Destination (Join-Path $StageDir $file) -Force
        }
    }
} elseif (Test-Path (Join-Path $FrontendRoot ".env.example")) {
    Copy-Item -LiteralPath (Join-Path $FrontendRoot ".env.example") -Destination (Join-Path $StageDir ".env.example") -Force
}

$nodeServer = @'
#!/bin/sh
# description: start|stop node app
node_start() {
  npm start
}
node_stop() {
  npm stop
}
case "$1" in
start)
  node_start
  ;;
stop)
  node_stop
  ;;
restart)
  node_stop
  node_start
  ;;
*)
  echo "Usage: $0 {start|stop|restart}"
esac
'@

$nodeServerPath = Join-Path $StageDir "nodeServer"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($nodeServerPath, $nodeServer.Replace("`r`n", "`n"), $utf8NoBom)

if (Test-Path $PackagePath) {
    Remove-Item -LiteralPath $PackagePath -Force
}

Push-Location $DistDir
try {
    tar -czf $PackagePath $AppName
} finally {
    Pop-Location
}

Remove-StageDirectory -Path $StageDir

Write-Host "ADS frontend package created:"
Write-Host "  $PackagePath"
Write-Host ""
Write-Host "Upload it to ADS Nodejs component and start with:"
Write-Host "  ./nodeServer start"
