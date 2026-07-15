import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text()


def load_json_fixture(name: str) -> dict:
    return json.loads(load_fixture(name))
