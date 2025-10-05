# Beta Version
Advanced AI Desktop Assistant - Run powerful local LLMs anywhere, no installation required.

***Completely offline • No internet • No API keys • No cloud computing • No GPU required • No admin rights***

Beta Version is a cutting-edge portable AI application that runs large language models locally on any Windows computer. Simply drop the executable and your model file onto a USB drive, plug into any PC, and start an intelligent conversation with advanced AI capabilities.

![Beta Version Interface](Images/Screenshot1.png)

![Beta Version Demo](Images/Combined_gif.gif)

# Why Beta Version is Revolutionary

🚀 **Truly Portable**
Single executable file runs on any Windows machine without installation or admin privileges.

🎨 **Intuitive Interface**
Clean dual-pane design: compose prompts below, watch AI responses stream above in real-time.

🔍 **Smart Source Tracking**
Automatic highlighting of prompt words in responses with Ctrl+click to trace sources across conversation history.

💾 **Persistent Conversations**
One-click save/load functionality keeps your AI sessions portable and organized.

⚡ **Optimized Performance**
Built on llama.cpp for maximum CPU efficiency and compatibility across hardware configurations.

🎹 **Power User Features**
Full keyboard shortcuts: Ctrl+S send, Ctrl+Z stop, Ctrl+F search, Ctrl+X clear, plus mouse-wheel zoom.

📚 **Advanced RAG Integration**
Upload documents (PDF, DOCX, TXT, MD, HTML) for intelligent document analysis and question answering.

# Quick Start Guide

1. **Download** `BetaVersion.exe` from the releases section
2. **Get a model** - We recommend `gemma-3-1b-it-Q4_K_M.gguf` for first-time users (~800MB)
3. **Copy both files** to your USB drive or local folder
4. **Double-click** `BetaVersion.exe` on any Windows computer
5. **Wait for model loading** (first run only - cached for subsequent use)
6. **Start chatting** with your local AI assistant

For different models, use File → Select Model and browse to your preferred GGUF file.

# Recommended Models

| Model | Size | Performance | Best For |
|-------|------|-------------|----------|
| **gemma-3-1b-it-Q4_K_M.gguf** | ~800MB | ~20 tokens/sec on i7-10750H | General chat, quick responses |
| **gemma-3-4b-it-Q4_K_M.gguf** | ~2.3GB | ~10 tokens/sec on i7-10750H | Better reasoning, detailed answers |
| **qwen3-1.7b-q4_k_m.gguf** | ~1.0GB | ~18 tokens/sec on i7-10750H | Advanced reasoning with thinking mode |

*Performance varies by CPU. Models auto-adapt to available system resources.*

# Advanced Features

### 🔍 Source Word Highlighting
Every word from your prompts is automatically highlighted in AI responses. Ctrl+click any highlighted word to see its complete usage history across all conversations.

![Source Highlighting Demo](Images/bold_text_demo.gif)

### ⌨️ Keyboard Shortcuts
- **Ctrl+S**: Send message to AI
- **Ctrl+Z**: Stop AI generation
- **Ctrl+F**: Search conversation history  
- **Ctrl+X**: Clear all chat history
- **Ctrl+P**: Edit system prompt
- **Ctrl+Mouse Wheel**: Zoom interface

![Keyboard Shortcuts](Images/CtrlS.gif)

### 💾 Session Management
Save and load complete conversation histories with full context preservation.

![Session Management](Images/Load_chat.gif)

### 📄 Document Intelligence
Drag and drop documents for AI-powered analysis, summarization, and Q&A.

# Technical Specifications

**System Requirements:**
- Windows 7 or later (32-bit and 64-bit)
- 2GB RAM minimum (4GB+ recommended)
- 1GB free storage for models
- Any CPU architecture (Intel, AMD, ARM64)

**Supported Formats:**
- Models: GGUF format (llama.cpp compatible)
- Documents: PDF, DOCX, TXT, MD, HTML
- Export: JSON conversation files

**Architecture:**
- Frontend: Modern PySide6 with custom UI components
- Backend: llama-cpp-python for model inference
- RAG: FAISS vector database with semantic search
- Embeddings: sentence-transformers for document processing

# Building from Source

```bash
# Clone repository
git clone https://github.com/yourrepo/betaversion.git
cd betaversion

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python launch_beta.py
```

# License & Contributing

Beta Version is released under the Apache 2.0 License - see LICENSE file for details.

This project welcomes contributions! Please read our contributing guidelines before submitting pull requests.

**Created by Redacted • Built with ❤️ for the AI community**
