# Contributing to Clash Verge CLI

Thanks for your interest in contributing!

## Development Setup

```bash
# Clone the repository
git clone https://github.com/Kerry1020/clash-verge-cli.git
cd clash-verge-cli

# Create virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install in development mode with test/lint tools
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest            # unit + CLI tests, HTTP is mocked
ruff check .      # lint

# Try the CLI
clash-verge --help
clash-verge status
```

Please add tests for new commands or bug fixes. Tests must not touch the real
Clash Verge config (the `isolate_home` fixture in `tests/conftest.py` takes care
of that) and must not make real network requests.

## Code Style

- Follow PEP 8
- Use type hints where possible
- Keep functions under 50 lines
- Add docstrings to public functions

## Submitting Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Issues

Feel free to submit issues for:
- Bug reports
- Feature requests
- Questions about usage

## License

By contributing, you agree that your contributions will be licensed under the GPL-3.0 License.
