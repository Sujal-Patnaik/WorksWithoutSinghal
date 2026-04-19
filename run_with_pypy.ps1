param(
    [ValidateSet("build", "run", "all", "test", "tune", "compare", "plot")]
    [string]$Action = "all",

    [string]$PyPyHome = "",

    [string]$PyPyExe = "",

    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

function Resolve-PyPyExe {
    param(
        [string]$PyPyRoot,
        [string]$ExplicitPyPyExe
    )

    if ($ExplicitPyPyExe) {
        if (Test-Path $ExplicitPyPyExe) {
            return $ExplicitPyPyExe
        }
        throw "PyPy executable path '$ExplicitPyPyExe' does not exist."
    }

    $candidates = @()

    if ($PyPyRoot) {
        $candidates += @(
            (Join-Path $PyPyRoot "pypy3.exe"),
            (Join-Path $PyPyRoot "pypy.exe")
        )
    }

    $pypy3Command = Get-Command pypy3 -ErrorAction SilentlyContinue
    if ($pypy3Command) {
        $candidates += $pypy3Command.Source
    }

    $pypyCommand = Get-Command pypy -ErrorAction SilentlyContinue
    if ($pypyCommand) {
        $candidates += $pypyCommand.Source
    }

    $uniqueCandidates = $candidates | Select-Object -Unique

    foreach ($candidate in $uniqueCandidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    throw "Could not locate a PyPy executable. Provide -PyPyExe, provide -PyPyHome, or add pypy3/pypy to PATH."
}

function Resolve-VenvPyPy {
    param([string]$VenvDir)

    $candidates = @(
        (Join-Path $VenvDir "Scripts\pypy3.exe"),
        (Join-Path $VenvDir "Scripts\pypy.exe")
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    throw "Could not find PyPy executable under '$VenvDir\Scripts'. Rebuild the venv with PyPy."
}

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

$VenvDir = Join-Path $RepoRoot ".venv-pypy"
$PyPyExe = Resolve-PyPyExe -PyPyRoot $PyPyHome -ExplicitPyPyExe $PyPyExe

Write-Host "[INFO] Repository root: $RepoRoot"
Write-Host "[INFO] Using PyPy:      $PyPyExe"
Write-Host "[INFO] Action:          $Action"

if ($Action -in @("build", "all")) {
    if (-not (Test-Path $VenvDir)) {
        Write-Host "[BUILD] Creating PyPy virtual environment at $VenvDir"
        & $PyPyExe -m venv $VenvDir
    } else {
        Write-Host "[BUILD] Reusing existing PyPy virtual environment at $VenvDir"
    }

    $VenvPyPy = Resolve-VenvPyPy -VenvDir $VenvDir

    if (-not $SkipInstall) {
        Write-Host "[BUILD] Upgrading pip tooling"
        & $VenvPyPy -m pip install --upgrade pip setuptools wheel

        $RequirementsFile = Join-Path $RepoRoot "requirements.txt"
        if (Test-Path $RequirementsFile) {
            Write-Host "[BUILD] Installing dependencies from requirements.txt"
            & $VenvPyPy -m pip install -r $RequirementsFile
        } else {
            Write-Host "[BUILD] No requirements.txt found; skipping dependency install"
        }
    } else {
        Write-Host "[BUILD] SkipInstall enabled; skipping package installation"
    }
}

if ($Action -in @("run", "all", "test", "tune", "compare", "plot")) {
    if (-not (Test-Path $VenvDir)) {
        throw "Virtual environment not found at '$VenvDir'. Run with -Action build or -Action all first."
    }

    $VenvPyPy = Resolve-VenvPyPy -VenvDir $VenvDir

    if ($Action -in @("run", "all")) {
        Write-Host "[RUN] Executing main.py"
        & $VenvPyPy (Join-Path $RepoRoot "main.py")
    }

    if ($Action -eq "test") {
        Write-Host "[TEST] Executing test_operators.py"
        & $VenvPyPy (Join-Path $RepoRoot "test_operators.py")
    }

    if ($Action -eq "tune") {
        Write-Host "[TUNE] Executing tune.py"
        & $VenvPyPy (Join-Path $RepoRoot "tune.py")
    }

    if ($Action -eq "compare") {
        Write-Host "[COMPARE] Executing experiments/compare_policies.py"
        & $VenvPyPy (Join-Path $RepoRoot "experiments\compare_policies.py") --pypy-exe $VenvPyPy
    }

    if ($Action -eq "plot") {
        Write-Host "[PLOT] Executing experiments/plot_comparison.py"
        & $VenvPyPy (Join-Path $RepoRoot "experiments\plot_comparison.py")
    }
}

Write-Host "[DONE] Completed action '$Action'."
