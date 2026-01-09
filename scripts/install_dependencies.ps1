# Sur5 Lite Dependency Installation Script
# Run this in a regular PowerShell window: .\install_dependencies.ps1

Write-Host "================================" -ForegroundColor Cyan
Write-Host "Sur5 Lite Dependency Installation" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Navigate to app directory (relative to script location)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppRoot = Split-Path -Parent $ScriptDir
Set-Location -Path $AppRoot

Write-Host "Stage 1: Installing PySide6 (UI Framework)..." -ForegroundColor Yellow
python -m pip install PySide6>=6.5.0
Write-Host "✓ PySide6 installed" -ForegroundColor Green
Write-Host ""

Write-Host "Stage 2: Installing llama-cpp-python (this will take 5-10 minutes)..." -ForegroundColor Yellow
Write-Host "  - Downloading and compiling C++ code..." -ForegroundColor Gray
python -m pip install llama-cpp-python==0.3.16 --no-cache-dir
Write-Host "✓ llama-cpp-python installed" -ForegroundColor Green
Write-Host ""

Write-Host "Stage 2b: Installing llama-cpp-agent..." -ForegroundColor Yellow
python -m pip install llama-cpp-agent==0.2.35
Write-Host "✓ llama-cpp-agent installed" -ForegroundColor Green
Write-Host ""

Write-Host "Stage 3: Installing RAG and document processing packages..." -ForegroundColor Yellow
python -m pip install faiss-cpu>=1.8.0 sentence-transformers>=2.3.0 onnxruntime>=1.20.0 rank-bm25>=0.2.2
python -m pip install pypdf>=4.0.0 python-docx>=1.0.0 beautifulsoup4>=4.12.0 markdown>=3.5.0
python -m pip install docling>=1.0.0 Pillow>=10.0.0
python -m pip install nltk>=3.8.0 psutil>=5.9.0 gputil>=1.4.0 numpy>=1.26.0 tqdm>=4.66.0
Write-Host "✓ All packages installed" -ForegroundColor Green
Write-Host ""

Write-Host "================================" -ForegroundColor Cyan
Write-Host "Verifying installation..." -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

# Verify critical imports
Write-Host "Testing PySide6..." -NoNewline
python -c "from PySide6.QtWidgets import QApplication; print(' OK')"

Write-Host "Testing llama-cpp-python..." -NoNewline
python -c "import llama_cpp; print(' OK')"

Write-Host ""
Write-Host "================================" -ForegroundColor Green
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host ""
Write-Host "To launch the application, run:" -ForegroundColor Yellow
Write-Host "  python launch_sur5.py" -ForegroundColor White
Write-Host ""


















