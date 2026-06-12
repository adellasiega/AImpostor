# AImpostor

### Installation

```bash
# Clone repository
git clone https://github.com/USERNAME/AImpostor.git
cd AImpostor

# Create virtual environment
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate

# Install package with dependencies
pip install -e .
```

### Running the Game

```bash
# Run with default config
python -m framework.main

# Run with custom config
python -m framework.main --config path/to/config.json
```

### Run Tests

```bash
# Run all tests
pytest -v

# Run specific test file
pytest tests/test_game.py -v
```