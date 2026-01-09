# Sur5 Lite Models

This folder contains AI models for Sur5 Lite. Place `.gguf` model files here and they will automatically appear in the model dropdown.

## Recommended Model

### IBM Granite 4.0-h-1b (Hybrid with Reasoning)
The recommended model for Sur5 Lite. Compact (901 MB), fast, and includes reasoning capabilities.

**Download:**
```bash
# Using huggingface-cli
pip install huggingface_hub
huggingface-cli download ibm-granite/granite-4.0-h-1b-GGUF granite-4.0-h-1b-Q4_K_M.gguf --local-dir ./Models

# Or direct download from:
# https://huggingface.co/ibm-granite/granite-4.0-h-1b-GGUF/blob/main/granite-4.0-h-1b-Q4_K_M.gguf
```

| Property | Value |
|----------|-------|
| Size | 901 MB |
| Parameters | ~1B |
| Quantization | Q4_K_M |
| License | Apache 2.0 |
| Reasoning | Yes (Hybrid architecture) |

---

## Additional Compatible Models

### GPT-OSS 20B
High-quality open-source GPT model.

```bash
huggingface-cli download unsloth/gpt-oss-20b-GGUF gpt-oss-20b-Q4_K_M.gguf --local-dir ./Models
```
- **Size:** 11.6 GB
- **License:** Apache 2.0
- **Link:** https://huggingface.co/unsloth/gpt-oss-20b-GGUF

### Nemotron-3-Nano-30B
NVIDIA's efficient model with strong reasoning.

```bash
huggingface-cli download unsloth/Nemotron-3-Nano-30B-A3B-GGUF Nemotron-3-Nano-30B-A3B-Q4_K_M.gguf --local-dir ./Models
```
- **Size:** 24.6 GB
- **License:** NVIDIA Open Model License
- **Link:** https://huggingface.co/unsloth/Nemotron-3-Nano-30B-A3B-GGUF

---

## Supported Architectures

Sur5 Lite uses llama-cpp-python for inference. Supported model architectures include:

- ✅ LLaMA / LLaMA 2 / LLaMA 3
- ✅ Gemma / Gemma 2 / Gemma 3
- ✅ Qwen / Qwen 2 / Qwen 2.5
- ✅ Phi-3
- ✅ DeepSeek / DeepSeek 2
- ✅ Mistral / Mixtral
- ✅ IBM Granite

## File Format

Sur5 Lite supports **GGUF** format models (`.gguf` extension). This is the standard format for llama.cpp-based inference.

Recommended quantizations:
- **Q4_K_M** - Best balance of quality and size
- **Q5_K_M** - Higher quality, larger size
- **Q8_0** - Near-original quality, largest size

---

*For more models, visit [Hugging Face](https://huggingface.co/models?library=gguf)*
