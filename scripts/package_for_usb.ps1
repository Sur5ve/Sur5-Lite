# Sur5 USB Portable Package Script
# Creates a ready-to-copy USB structure with Sur5.exe

param(
    [string]$ExePath = "dist\Sur5.exe",
    [string]$OutputDir = "USB_Package"
)

Write-Host "`n╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║          Sur5 USB Portable Package Creator                  ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

$ErrorActionPreference = "Stop"

# [1/5] Verify Sur5.exe exists
Write-Host "[1/5] Verifying Sur5.exe..." -ForegroundColor Yellow

if (-not (Test-Path $ExePath)) {
    Write-Host "ERROR: Sur5.exe not found at: $ExePath" -ForegroundColor Red
    Write-Host "       Please build first: .\build_single_exe_optimized.ps1" -ForegroundColor Red
    exit 1
}

$exeSize = (Get-Item $ExePath).Length / 1MB
Write-Host "      ✓ Found: $ExePath ($([math]::Round($exeSize, 2)) MB)" -ForegroundColor Green

# [2/5] Create USB package structure
Write-Host "`n[2/5] Creating USB package structure..." -ForegroundColor Yellow

if (Test-Path $OutputDir) {
    Write-Host "      Removing old package..." -ForegroundColor Gray
    Remove-Item -Recurse -Force $OutputDir
}

New-Item -ItemType Directory -Path $OutputDir | Out-Null
New-Item -ItemType Directory -Path "$OutputDir\Models" | Out-Null

Write-Host "      ✓ Created: $OutputDir\" -ForegroundColor Green
Write-Host "      ✓ Created: $OutputDir\Models\" -ForegroundColor Green

# [3/5] Copy Sur5.exe
Write-Host "`n[3/5] Copying Sur5.exe..." -ForegroundColor Yellow

Copy-Item $ExePath "$OutputDir\Sur5.exe" -Force
Write-Host "      ✓ Copied: Sur5.exe" -ForegroundColor Green

# [4/5] Create START_HERE.txt
Write-Host "`n[4/5] Creating START_HERE.txt..." -ForegroundColor Yellow

$startHereContent = @"
╔══════════════════════════════════════════════════════════════╗
║                    Sur5 Lite                         ║
║                  USB Portable Edition                        ║
╚══════════════════════════════════════════════════════════════╝

🚀 QUICK START
══════════════
1. Place your GGUF model file in the "Models" folder
   Example: Models\Qwen3-1.7B-Q4_K_M.gguf

2. Double-click Sur5.exe to launch

3. The application will open maximized and ready to use!


📁 WHAT'S INCLUDED
═══════════════════
Sur5.exe         - Main application (~150-200MB)
Models\          - Place your GGUF model files here
START_HERE.txt   - This file


🖥️ SYSTEM REQUIREMENTS
═══════════════════════
• Windows 10 or 11 (64-bit)
• 8GB RAM minimum (16GB recommended)
• USB 3.0 recommended for best performance
• No additional software required - fully self-contained


⚡ FIRST LAUNCH
════════════════
The first time you launch Sur5.exe, it will:
• Extract files to Windows TEMP folder (~10-15 seconds)
• Open maximized with sidebar collapsed (clean interface)
• Look for models in the "Models" folder

Subsequent launches will be faster (~5-10 seconds).


🛡️ WINDOWS SMARTSCREEN
═══════════════════════
If Windows blocks Sur5.exe on first launch:

1. Click "More info" link
2. Click "Run anyway" button

This is normal for unsigned applications. Sur5 is safe to run.


🎯 FEATURES
═══════════
✓ Fully portable - no installation required
✓ Works on any Windows 11 computer
✓ Offline AI - no internet required
✓ RAG (Retrieval-Augmented Generation) support
✓ GPU acceleration (if available)
✓ Modern dark theme interface
✓ Conversation save/load
✓ Document analysis (PDF, DOCX, TXT, Markdown)


📚 SUPPORTED MODELS
═══════════════════
Any GGUF format model from HuggingFace:
• Qwen 1.7B-3B (recommended for speed)
• Llama 3 / 3.1 / 3.2
• Mistral 7B
• Phi-3
• And many more...

Download from: https://huggingface.co/models?library=gguf


🔧 TROUBLESHOOTING
══════════════════

Problem: "Model not found"
Solution: Place a .gguf file in the Models\ folder next to Sur5.exe

Problem: Slow startup
Solution: 
  • First launch is always slower (extracting to TEMP)
  • Use USB 3.0 port (not USB 2.0)
  • Antivirus may scan - add exception for Sur5.exe

Problem: Application won't launch
Solution:
  • Check Windows SmartScreen (see above)
  • No additional software required - app is fully self-contained
  • Try running from a local drive (copy USB contents to C:\)


📊 PERFORMANCE TIPS
═══════════════════
• Choose smaller models (1.7B-3B) for faster responses
• Close other applications to free up RAM
• Use SSD or local drive for best performance
• Enable GPU acceleration in settings (if available)


🎨 INTERFACE TIPS
═════════════════
• Sidebar is collapsed by default - click "Control Hub" tab to expand
• Use Ctrl+F to search conversations
• Use Ctrl+S to save conversations
• Use Ctrl+Z to undo in chat input


📞 TECHNICAL INFO
═════════════════
Version: 2.0 Portable (Single-file)
Build Date: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Architecture: x64 (Windows 11)
Optimization: ROG Laptop tuned

Built for Kickstarter Demo


🎬 DEMO READY
══════════════
This build is optimized for demonstration:
• Opens maximized automatically
• Clean interface (sidebar collapsed)
• Fast, professional appearance
• Fully portable

Perfect for your Kickstarter video!


═══════════════════════════════════════════════════════════════

Enjoy Sur5 Lite! 🤖

"@

Set-Content -Path "$OutputDir\START_HERE.txt" -Value $startHereContent -Encoding UTF8
Write-Host "      ✓ Created: START_HERE.txt" -ForegroundColor Green

# [5/5] Calculate package info
Write-Host "`n[5/5] Package summary..." -ForegroundColor Yellow

$packageSize = (Get-ChildItem $OutputDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
$checksum = (Get-FileHash "$OutputDir\Sur5.exe" -Algorithm SHA256).Hash

Write-Host "      Package size: $([math]::Round($packageSize, 2)) MB" -ForegroundColor Cyan
Write-Host "      SHA256: $checksum" -ForegroundColor Cyan

# Summary
Write-Host "`n╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║              📦 USB Package Ready! 📦                        ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

Write-Host "📂 Package Location:" -ForegroundColor White
Write-Host "   $OutputDir\" -ForegroundColor Cyan

Write-Host "`n📋 USB Structure:" -ForegroundColor White
Write-Host "   USB_ROOT\" -ForegroundColor Gray
Write-Host "   ├── Sur5.exe           (~$([math]::Round($exeSize, 0)) MB)" -ForegroundColor Gray
Write-Host "   ├── Models\            (empty - add your GGUF model)" -ForegroundColor Gray
Write-Host "   └── START_HERE.txt     (Quick start guide)" -ForegroundColor Gray

Write-Host "`n✅ Next Steps:" -ForegroundColor White
Write-Host "   1. Copy contents of $OutputDir\ to your USB drive" -ForegroundColor Cyan
Write-Host "   2. Add your GGUF model to Models\ folder" -ForegroundColor Cyan
Write-Host "   3. Test on ROG laptop: $OutputDir\Sur5.exe" -ForegroundColor Cyan

Write-Host "`n🎬 Ready for Kickstarter demo!" -ForegroundColor Green
Write-Host ""



