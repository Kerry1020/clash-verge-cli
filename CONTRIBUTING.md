# Contributing to Clash Verge CLI

Thanks for your interest in contributing!

## Development Setup

```bash
# Clone the repository
git clone https://github.com/lingion/clash-verge-cli.git
cd clash-verge-cli

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

## Running Tests

```bash
# Test the CLI
python clash_verge_cli.py --help

# Run specific command
python clash_verge_cli.py status
```

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

By contributing, you agree that your contributions will be licensed under the MIT License.
