$ErrorActionPreference = "Stop"
py -3.12 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "Python 3.12 is required" }
& .venv\Scripts\python.exe -m pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed" }
& .venv\Scripts\python.exe -m pip install -e .
if ($LASTEXITCODE -ne 0) { throw "Package installation failed" }
& .venv\Scripts\rsec.exe doctor
Write-Host "CPU tools are installed. Use WSL2/Linux for GPU training; see docs/TRAINING_GUIDE.md."
