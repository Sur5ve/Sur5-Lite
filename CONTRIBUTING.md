# Contributing to Sur5 Lite

Thank you for your interest in contributing to Sur5 Lite!

> ⚠️ **Important**: The Sur5™ and Sur5ve™ names and logos are trademarks of Sur5ve LLC and are **NOT** part of the open source license. If you fork this project, you must create your own branding. See [TRADEMARK.md](TRADEMARK.md).

## Code of Conduct

Be respectful and constructive. We welcome contributors of all backgrounds
and experience levels.

## How to Contribute

1. **Fork the repository** on GitHub
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** following our code style guidelines
4. **Add tests** if applicable
5. **Commit your changes**: `git commit -m 'Add amazing feature'`
6. **Push to your branch**: `git push origin feature/amazing-feature`
7. **Submit a Pull Request**

## Code Style

- Follow [PEP 8](https://pep8.org/) for Python code
- Add docstrings to all public functions and classes
- Include type hints where appropriate
- Add the standard file header to new files:

```python
#!/usr/bin/env python3
"""
[Module Name] - [Brief Description]

Sur5 Lite — Open Source Edge AI
Copyright (c) 2024-2026 Sur5ve LLC
Licensed under MIT License
https://sur5ve.com
"""
```

## Reporting Issues

When reporting issues, please include:

- Your operating system and version
- Python version
- Steps to reproduce the issue
- Expected vs actual behavior
- Any relevant error messages or logs

## Feature Requests

We welcome feature requests! Please describe:

- The problem you're trying to solve
- Your proposed solution
- Any alternatives you've considered

## Development Setup

```bash
# Clone the repository
git clone https://github.com/Sur5ve/Sur5-Lite.git
cd Sur5-Lite/App

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python launch_sur5.py
```

## Testing

Before submitting a pull request:

1. Ensure the application launches without errors
2. Test model loading and generation
3. Verify your changes don't break existing functionality

## License

By contributing to Sur5 Lite, you agree that your contributions will be licensed
under the [MIT License](LICENSE).

This means:
- Your contributions can be used for any purpose, including commercial
- The MIT License is one of the most permissive open source licenses

### ⚠️ Trademark Reminder

When contributing, **do not**:
- Add new Sur5/Sur5ve logos or branding
- Modify existing trademark files
- Create derivative works of protected assets

The Sur5™ and Sur5ve™ trademarks remain the exclusive property of Sur5ve LLC.

## Questions?

For questions about contributing, please contact:
- Email: support@sur5ve.com
- Website: https://sur5ve.com

---

Thank you for helping make Sur5 Lite better!
