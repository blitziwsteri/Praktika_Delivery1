import pytest
from models import Customer, Order, OrderItem

def test_customer_requires_name():
    with pytest.raises(ValueError): Customer(" ").validate()

def test_order_total_calculated():
    order = Order(1, "2025-04-20", "новый", [OrderItem("Пицца", 2, 750)])
    order.validate()
    assert order.total == 1500

def test_invalid_order_status():
    order = Order(1, "2025-04-20", "неизвестно", [OrderItem("Пицца", 1, 10)])
    with pytest.raises(ValueError): order.validate()

def test_invalid_item_quantity():
    with pytest.raises(ValueError): OrderItem("Товар", 0, 10).validate()
