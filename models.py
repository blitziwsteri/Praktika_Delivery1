"""Модели данных системы доставки."""
from dataclasses import dataclass, field
from datetime import date
from typing import List

STATUSES = ("новый", "в доставке", "выполнен", "отменён")

@dataclass
class Customer:
    name: str
    phone: str = ""
    address: str = ""
    id: int | None = None

    def validate(self):
        if not self.name or not self.name.strip():
            raise ValueError("Имя клиента обязательно")

@dataclass
class OrderItem:
    product_name: str
    quantity: int
    price: float

    def validate(self):
        if not self.product_name or not self.product_name.strip():
            raise ValueError("Название товара обязательно")
        if isinstance(self.quantity, bool) or self.quantity <= 0:
            raise ValueError("Количество должно быть положительным целым числом")
        if self.price < 0:
            raise ValueError("Цена не может быть отрицательной")

    @property
    def subtotal(self) -> float:
        return round(self.quantity * self.price, 2)

@dataclass
class Order:
    customer_id: int
    order_date: str = field(default_factory=lambda: date.today().isoformat())
    status: str = "новый"
    items: List[OrderItem] = field(default_factory=list)
    id: int | None = None
    total: float | None = None

    def validate(self):
        if not isinstance(self.customer_id, int) or self.customer_id <= 0:
            raise ValueError("Необходимо выбрать корректного клиента")
        try:
            date.fromisoformat(self.order_date)
        except (TypeError, ValueError):
            raise ValueError("Дата заказа должна быть в формате ГГГГ-ММ-ДД")
        if self.status not in STATUSES:
            raise ValueError(f"Недопустимый статус: {self.status}")
        if not self.items:
            raise ValueError("В заказе должен быть хотя бы один товар")
        for item in self.items:
            item.validate()
        calculated = round(sum(i.subtotal for i in self.items), 2)
        if self.total is not None and abs(float(self.total) - calculated) > 0.01:
            raise ValueError("Итоговая сумма не совпадает с суммой товаров")
        self.total = calculated
