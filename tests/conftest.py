from pathlib import Path

import pytest

from src.database import Repository


@pytest.fixture()
def repo(tmp_path: Path) -> Repository:
    return Repository(tmp_path / "apartments.db")
