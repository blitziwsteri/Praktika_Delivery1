import pytest
from database import Database

@pytest.fixture
def db(tmp_path):
    return Database(tmp_path / "test.db")
