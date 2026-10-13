import json
import pytest
from models import Customer, Order, OrderItem
from data_export import export_file, import_file

def seeded(db):
    cid = db.add_customer(Customer("Ольга", "111", "Казань"))
    db.add_order(Order(cid, "2025-04-20", "новый", [OrderItem("Книга", 3, 120)]))

def test_json_roundtrip(db, tmp_path):
    seeded(db); path = tmp_path / "backup.json"
    assert export_file(db, path) == 1
    other = type(db)(tmp_path / "other.db")
    assert import_file(other, path) == 1
    assert other.list_orders()[0]["total"] == 360

def test_xml_roundtrip(db, tmp_path):
    seeded(db); path = tmp_path / "backup.xml"
    export_file(db, path)
    other = type(db)(tmp_path / "other.db")
    assert import_file(other, path) == 1
    assert other.list_orders()[0]["customer_name"] == "Ольга"

def test_invalid_import_keeps_database(db, tmp_path):
    seeded(db); path = tmp_path / "bad.json"
    path.write_text(json.dumps({"customers": [], "orders": [{"id": 1}]}), encoding="utf-8")
    with pytest.raises(ValueError): import_file(db, path)
    assert len(db.list_orders()) == 1

def test_unknown_extension(db, tmp_path):
    with pytest.raises(ValueError): export_file(db, tmp_path / "file.csv")
