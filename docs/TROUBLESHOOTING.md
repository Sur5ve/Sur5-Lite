# Troubleshooting Sur5 Lite

Common issues and solutions for Sur5 Lite.

---

## Startup Issues

### "No module named 'PySide6'"

**Cause**: Dependencies not installed.

**Solution**:
```bash
pip install -r requirements.txt
```

### "Python version 3.10+ required"

**Cause**: Using an older Python version.

**Solution**: Install Python 3.11 or later from [python.org](https://python.org).

### Black/blank window on startup

**Cause**: GPU driver issues or theme loading failure.

**Solution**:
1. Update your GPU drivers
2. Delete `settings.json` to reset theme
3. Try running with: `python launch_sur5.py --no-gpu`

---

## Model Loading Issues

### "Failed to load model"

**Possible causes**:
1. Model file is corrupted
2. Insufficient RAM
3. Unsupported model format

**Solutions**:
1. Re-download the model file
2. Try a smaller quantization (Q4_K_M instead of Q8)
3. Ensure the file is in GGUF format

### "Out of memory" or system freezes

**Cause**: Model too large for available RAM.

**Solutions**:
1. Use a smaller model or quantization (Q4_K_M)
2. Use a lower RAM preset (Minimal or Fast)
3. Close other applications
4. Use a smaller model (1-3B parameters)

### Model loads but responses are slow

**Cause**: CPU-only inference or suboptimal settings.

**Solutions**:
1. Ensure GPU acceleration is enabled (automatic on NVIDIA/Apple Silicon)
2. Use a lower RAM preset (Fast instead of Balanced) for shorter context
3. Use a smaller model or lower quantization (Q4_K_M is fastest)

---

## Generation Issues

### "llama_decode returned -1"

**Cause**: Context overflow or KV cache corruption.

**Solutions**:
1. Start a new conversation (Ctrl+N)
2. Use a lower RAM preset to reduce context size
3. Use a model with larger native context support

### Responses cut off mid-sentence

**Cause**: `max_tokens` limit reached.

**Solution**: Increase `max_tokens` in settings:
```json
{
  "model": {
    "max_tokens": 4096
  }
}
```

### Thinking mode shows but no final response

**Cause**: Model doesn't support thinking mode or format mismatch.

**Solutions**:
1. Disable thinking mode for non-thinking models
2. Use a model with thinking support (Qwen3, Granite-H)

### Garbage characters or broken formatting

**Cause**: Incorrect stop sequences for the model.

**Solution**: The model may need custom stop sequences. Check if the model is supported in `services/prompt_patterns.py`.

---

## UI Issues

### Text is too small/large

**Solution**: Adjust font size in settings:
```json
{
  "appearance": {
    "font_size": 16
  }
}
```

### Sidebar won't open/close

**Solution**: Click the "CONTROL HUB" tab on the right edge, or use the View menu.

### Theme not applying

**Solutions**:
1. Restart the application
2. Delete `settings.json` to reset
3. Check for theme file in `sur5_lite_pyside/themes/`

---

## Platform-Specific Issues

### Windows

**"VCRUNTIME140.dll not found"**

Install Visual C++ Redistributable:
```powershell
winget install Microsoft.VCRedist.2015+.x64
```

**Antivirus blocks Sur5 Lite**

Add Sur5 Lite to your antivirus exclusions. PyInstaller executables often trigger false positives.

### macOS

**"Sur5 Lite can't be opened because it is from an unidentified developer"**

Right-click the app → Open → Open anyway.

Or remove quarantine:
```bash
xattr -cr /path/to/Sur5.app
```

**Metal not being used**

Check that you're on Apple Silicon (M1/M2/M3). Intel Macs don't support Metal for LLM inference.

### Linux

**Missing Qt libraries**

```bash
sudo apt install libxcb-xinerama0 libxkbcommon-x11-0
```

**Wayland display issues**

Try forcing X11:
```bash
QT_QPA_PLATFORM=xcb python launch_sur5.py
```

---

## Performance Tips

1. **Use GPU acceleration** — Metal on Mac, CUDA on NVIDIA
2. **Match context size to your needs** — Smaller = faster
3. **Use appropriate quantization** — Q4_K_M is a good balance
4. **Close background apps** — Free up RAM for the model
5. **SSD storage** — Model loading is faster from SSD

---

## Getting Help

If your issue isn't listed here:

1. **Check the logs**: `sur5_lite_pyside/utils/logs/sur5.log`
2. **GitHub Issues**: [github.com/Sur5ve/Sur5-Lite/issues](https://github.com/Sur5ve/Sur5-Lite/issues)
3. **Email**: support@sur5ve.com

When reporting issues, include:
- Operating system and version
- Python version (`python --version`)
- Model being used
- Error message or log output

---

## Next Steps

- [Building Guide](BUILDING.md) — Build Sur5 Lite from source
- [Configuration](CONFIGURATION.md) — Customize Sur5 Lite settings
