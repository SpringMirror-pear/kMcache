param(
    [switch]$CompileOnly,
    [switch]$TestsOnly,
    [switch]$PackageOnly
)

$ErrorActionPreference = "Stop"

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Action
    )

    Write-Host "==> $Name"
    & $Action
}

if (-not $TestsOnly -and -not $PackageOnly) {
    Invoke-Step "Compile" {
        python -m compileall kmcache tests examples scripts
    }
}

if (-not $CompileOnly -and -not $PackageOnly) {
    Invoke-Step "Unit Tests" {
        python -m unittest `
            tests.test_local_backend `
            tests.test_manager `
            tests.test_avalanche `
            tests.test_redis_backend `
            tests.test_fastapi_integration `
            tests.test_serialization `
            tests.test_observability `
            tests.test_config `
            tests.test_package_exports `
            tests.test_packaging_metadata `
            tests.test_quality_workflow
    }
}

if (-not $CompileOnly -and -not $TestsOnly) {
    Invoke-Step "Package Smoke" {
        python -c "import tempfile; from pathlib import Path; import build_backend; tmp = tempfile.TemporaryDirectory(); wheel_name = build_backend.build_wheel(tmp.name); wheel_path = Path(tmp.name) / wheel_name; assert wheel_path.exists(), wheel_path"
    }
    Invoke-Step "Package Metadata" {
        python -m pip show fastapi > $null
        python -m pip show redis > $null
        python -m pip show httpx > $null
    }
}
