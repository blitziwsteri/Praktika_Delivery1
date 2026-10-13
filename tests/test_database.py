import pytest
from models import Customer, Order, OrderItem

def seed(db):
    cid = db.add_customer(Customer("Иван", "+700000000", "Москва"))
    oid = db.add_order(Order(cid, "2025-04-20", "выполнен", [OrderItem("Пицца", 2, 750)]))
    return cid, oid

def test_customer_crud(db):
    cid = db.add_customer(Customer("Анна", "123", "Адрес"))
    db.update_customer(cid, Customer("Анна Иванова", "456", "Новый адрес"))
    assert db.get_customer(cid)["name"] == "Анна Иванова"
    db.delete_customer(cid)
    assert db.get_customer(cid) is None

def test_cannot_delete_customer_with_orders(db):
    cid, _ = seed(db)
    with pytest.raises(ValueError, match="Нельзя удалить"):
        db.delete_customer(cid)

def test_order_crud_and_items(db):
    cid, oid = seed(db)
    assert db.get_order(oid)["total"] == 1500
    db.update_order(oid, Order(cid, "2025-04-21", "новый", [OrderItem("Чай", 1, 100)]))
    assert db.get_order(oid)["items"][0]["product_name"] == "Чай"
    db.delete_order(oid)
    assert db.get_order(oid) is None

def test_filter_orders(db):
    seed(db)
    assert len(db.list_orders(status="выполнен")) == 1
    assert len(db.list_orders(status="новый")) == 0
    assert len(db.list_orders(date_from="2025-04-20", date_to="2025-04-20")) == 1

def test_report(db):
    seed(db)
    report = db.report("month", "2025-04-20")
    assert report["counts"]["выполнен"] == 1
    assert report["revenue"] == 1500
    assert report["top_customers"][0]["name"] == "Иван"

def test_reject_unknown_customer(db):
    with pytest.raises(ValueError):
        db.add_order(Order(999, "2025-04-20", "новый", [OrderItem("X", 1, 2)]))
