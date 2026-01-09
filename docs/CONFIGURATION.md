# Configuring Sur5 Lite

Sur5 Lite stores settings in `settings.json` in the application directory.

---

## Settings File Location

| Platform | Location |
|----------|----------|
| Windows | `%APPDATA%\Sur5\settings.json` or `./settings.json` (portable) |
| macOS | `~/Library/Application Support/Sur5/settings.json` |
| Linux | `~/.config/Sur5/settings.json` |

**Portable Mode**: If `settings.json` exists next to the executable, Sur5 Lite uses it instead of the system location.

---

## RAM Presets

Sur5 Lite automatically detects available hardware and suggests appropriate settings:

| Preset | Context Size | GPU Layers | Best For |
|--------|-------------|------------|----------|
| Ultra | 512 tokens | 0 | 4GB RAM, constrained systems |
| Minimal | 2,048 tokens | Auto | Low-end systems |
| Fast | 8,192 tokens | Auto | 8GB+ RAM, quick responses |
| Balanced | 24,576 tokens | Auto | 16GB+ RAM, thinking mode |
| Power | 32,768 tokens | Auto | 24GB+ RAM, max context |

### Manual Override

Edit `settings.json`:

```json
{
  "ram_config": "16GB"
}
```

Valid values: `"4GB"`, `"8GB"`, `"16GB"`, `"32GB"`

---

## GPU Acceleration

### NVIDIA (CUDA)

Sur5 Lite auto-detects CUDA GPUs and enables acceleration automatically. GPU layer offloading is controlled by the RAM preset.

### Apple Silicon (Metal)

Metal is enabled by default on Apple Silicon Macs. Sur5 Lite will automatically offload model layers to the GPU based on your RAM preset.

### Manual GPU Control

GPU settings are managed through the RAM presets. Higher presets (16GB, 32GB) offload more layers to the GPU for faster inference.

---

## Thinking Mode

Enable/disable the reasoning display:

```json
{
  "thinking_mode_enabled": true
}
```

When enabled, supported models (Qwen3, Granite-H) will show their reasoning process before the final answer.

---

## Themes

The default theme is `sur5ve`. Additional themes can be added by creating JSON files in `sur5_lite_pyside/themes/theme_data/`.

```json
{
  "current_theme": "sur5ve",
  "font_size": 14
}
```

Change themes via **View → Theme** in the menu bar.

---

## Model Settings

```json
{
  "model_path": "models/qwen2.5-3b-instruct-q4_k_m.gguf",
  "max_tokens": 2048,
  "temperature": 0.7,
  "top_p": 0.9
}
```

### Parameter Guide

| Parameter | Range | Description |
|-----------|-------|-------------|
| `temperature` | 0.0-2.0 | Creativity (higher = more random) |
| `top_p` | 0.0-1.0 | Nucleus sampling threshold |
| `max_tokens` | 1-4096 | Max response length |

---

## Keyboard Shortcuts

Sur5 Lite uses the following keyboard shortcuts (not currently customizable):

| Shortcut | Action |
|----------|--------|
| `Enter` | Send message |
| `Shift+Enter` | New line in message |
| `Ctrl+N` | New conversation |
| `Ctrl+X` | Clear chat |
| `Ctrl+O` | Select model |
| `Ctrl+F` | Find in chat |
| `Escape` | Stop generation |
| `Ctrl+Shift+S` | Save conversation |
| `Ctrl+Shift+T` | Export as text |
| `Ctrl+Shift+M` | Export as markdown |

---

## Advanced Settings

### Additional Options

```json
{
  "enable_markdown": true,
  "show_timestamps": true,
  "auto_save_conversations": true,
  "max_chat_history": 1000
}
```

| Setting | Description |
|---------|-------------|
| `enable_markdown` | Render markdown in responses |
| `show_timestamps` | Show message timestamps |
| `auto_save_conversations` | Auto-save chat history |
| `max_chat_history` | Max messages to keep in memory |

---

## Resetting to Defaults

Delete `settings.json` to reset all settings. Sur5 Lite will create a new file with defaults on next launch.

---

## Next Steps

- [Building Guide](BUILDING.md) — Build Sur5 Lite from source
- [Troubleshooting](TROUBLESHOOTING.md) — Common issues and solutions
