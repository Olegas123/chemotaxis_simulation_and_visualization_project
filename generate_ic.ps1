# generate_ic.ps1
# Generate all initial conditions using unified IC generator

Write-Host "===== Unified IC Generation =====" -ForegroundColor Green
Write-Host ""

# Check if IC generator exists
if (-Not (Test-Path "bin\ic_gen.exe")) {
    Write-Host "IC generator not found. Building it..." -ForegroundColor Yellow
    
    # Build IC generator
    g++ -O3 -Wall -march=native -std=c++17 -o bin\ic_gen.exe initialConditions.cpp
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to build IC generator" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Built: bin\ic_gen.exe" -ForegroundColor Green
    Write-Host ""
}

# Ensure ic directory exists
if (-Not (Test-Path "ic")) {
    New-Item -ItemType Directory -Path "ic" | Out-Null
    Write-Host "Created directory: ic\" -ForegroundColor Green
}

# Generate all IC files
Write-Host "Generating complete IC set..." -ForegroundColor Cyan
Write-Host ""

.\bin\ic_gen.exe all

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: IC generation failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "===== IC Generation Complete =====" -ForegroundColor Green
Write-Host ""
Write-Host "Generated files in ic\ directory:" -ForegroundColor Cyan
Write-Host "  - master_ic.dat      (3D master IC)" -ForegroundColor White
Write-Host "  - ic_polar.dat       (2D polar, from 3D top)" -ForegroundColor White
Write-Host "  - ic_cyl.dat         (2D cylindrical, from 3D outer)" -ForegroundColor White
Write-Host "  - ic_1d.dat          (1D independent)" -ForegroundColor White
Write-Host ""
Write-Host "Ready to run simulations!" -ForegroundColor Green
Write-Host "  .\run.ps1 1d" -ForegroundColor Yellow
Write-Host "  .\run.ps1 top" -ForegroundColor Yellow
Write-Host "  .\run.ps1 side" -ForegroundColor Yellow
Write-Host "  .\run.ps1 coupled" -ForegroundColor Yellow
Write-Host "  .\run.ps1 all" -ForegroundColor Yellow