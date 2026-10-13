"""Слой доступа к SQLite: клиенты, заказы и отчёты."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import date, timedelta
from models import Customer, Order, OrderItem, STATUSES

DEFAULT_DB = Path(__file__).resolve().parent / "data" / "delivery.db"

class Database:
    def __init__(self, db_path=DEFAULT_DB):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    @contextmanager
    def connect(self):
        """Открывает соединение и гарантированно закрывает его после операции."""
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        try:
            with con:
                yield con
        finally:
            con.close()

    def init_db(self):
        with self.connect() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    phone TEXT DEFAULT '',
                    address TEXT DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
                    order_date TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('новый','в доставке','выполнен','отменён')),
                    total REAL NOT NULL CHECK(total >= 0)
                );
                CREATE TABLE IF NOT EXISTS order_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
                    product_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL CHECK(quantity > 0),
                    price REAL NOT NULL CHECK(price >= 0)
                );
            """)

    def add_customer(self, customer: Customer) -> int:
        customer.validate()
        with self.connect() as con:
            cur = con.execute("INSERT INTO customers(name,phone,address) VALUES(?,?,?)", (customer.name.strip(), customer.phone.strip(), customer.address.strip()))
            return cur.lastrowid

    def update_customer(self, customer_id: int, customer: Customer):
        customer.validate()
        with self.connect() as con:
            cur = con.execute("UPDATE customers SET name=?, phone=?, address=? WHERE id=?", (customer.name.strip(), customer.phone.strip(), customer.address.strip(), customer_id))
            if not cur.rowcount: raise ValueError("Клиент не найден")

    def delete_customer(self, customer_id: int):
        with self.connect() as con:
            if con.execute("SELECT 1 FROM orders WHERE customer_id=? LIMIT 1", (customer_id,)).fetchone():
                raise ValueError("Нельзя удалить клиента, у которого есть заказы")
            cur = con.execute("DELETE FROM customers WHERE id=?", (customer_id,))
            if not cur.rowcount: raise ValueError("Клиент не найден")

    def get_customers(self):
        with self.connect() as con:
            return [dict(r) for r in con.execute("SELECT * FROM customers ORDER BY name COLLATE NOCASE")]

    def get_customer(self, customer_id):
        with self.connect() as con:
            row = con.execute("SELECT * FROM customers WHERE id=?", (customer_id,)).fetchone()
            return dict(row) if row else None

    def add_order(self, order: Order) -> int:
        order.validate()
        with self.connect() as con:
            if not con.execute("SELECT 1 FROM customers WHERE id=?", (order.customer_id,)).fetchone():
                raise ValueError("Выбранный клиент не существует")
            cur = con.execute("INSERT INTO orders(customer_id,order_date,status,total) VALUES(?,?,?,?)", (order.customer_id, order.order_date, order.status, order.total))
            order_id = cur.lastrowid
            con.executemany("INSERT INTO order_items(order_id,product_name,quantity,price) VALUES(?,?,?,?)", [(order_id, i.product_name.strip(), i.quantity, i.price) for i in order.items])
            return order_id

    def update_order(self, order_id: int, order: Order):
        order.validate()
        with self.connect() as con:
            if not con.execute("SELECT 1 FROM customers WHERE id=?", (order.customer_id,)).fetchone():
                raise ValueError("Выбранный клиент не существует")
            cur = con.execute("UPDATE orders SET customer_id=?,order_date=?,status=?,total=? WHERE id=?", (order.customer_id, order.order_date, order.status, order.total, order_id))
            if not cur.rowcount: raise ValueError("Заказ не найден")
            con.execute("DELETE FROM order_items WHERE order_id=?", (order_id,))
            con.executemany("INSERT INTO order_items(order_id,product_name,quantity,price) VALUES(?,?,?,?)", [(order_id, i.product_name.strip(), i.quantity, i.price) for i in order.items])

    def delete_order(self, order_id: int):
        with self.connect() as con:
            cur = con.execute("DELETE FROM orders WHERE id=?", (order_id,))
            if not cur.rowcount: raise ValueError("Заказ не найден")

    def get_order(self, order_id: int):
        with self.connect() as con:
            row = con.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
            if not row: return None
            result = dict(row)
            result["items"] = [dict(i) for i in con.execute("SELECT product_name,quantity,price FROM order_items WHERE order_id=? ORDER BY id", (order_id,))]
            return result

    def list_orders(self, status=None, date_from=None, date_to=None):
        query = "SELECT o.*, c.name AS customer_name FROM orders o JOIN customers c ON c.id=o.customer_id WHERE 1=1"
        params = []
        if status:
            if status not in STATUSES: raise ValueError("Недопустимый статус")
            query += " AND o.status=?"; params.append(status)
        if date_from:
            date.fromisoformat(date_from); query += " AND o.order_date>=?"; params.append(date_from)
        if date_to:
            date.fromisoformat(date_to); query += " AND o.order_date<=?"; params.append(date_to)
        query += " ORDER BY o.order_date DESC, o.id DESC"
        with self.connect() as con:
            rows = [dict(r) for r in con.execute(query, params)]
            for row in rows:
                row["items"] = [dict(i) for i in con.execute("SELECT product_name,quantity,price FROM order_items WHERE order_id=? ORDER BY id", (row["id"],))]
            return rows

    def report(self, period="month", on_date=None):
        on_date = date.fromisoformat(on_date) if on_date else date.today()
        if period == "day": start = end = on_date
        elif period == "week": start = on_date - timedelta(days=on_date.weekday()); end = start + timedelta(days=6)
        elif period == "month": start = on_date.replace(day=1); end = (start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        else: raise ValueError("Период должен быть day, week или month")
        with self.connect() as con:
            counts = {s: 0 for s in STATUSES}
            for r in con.execute("SELECT status,COUNT(*) n FROM orders WHERE order_date BETWEEN ? AND ? GROUP BY status", (start.isoformat(), end.isoformat())): counts[r["status"]] = r["n"]
            top = [dict(r) for r in con.execute("SELECT c.id,c.name,ROUND(SUM(o.total),2) total FROM customers c JOIN orders o ON o.customer_id=c.id WHERE o.order_date BETWEEN ? AND ? GROUP BY c.id,c.name ORDER BY SUM(o.total) DESC,c.name LIMIT 3", (start.isoformat(), end.isoformat()))]
            revenue = con.execute("SELECT COALESCE(ROUND(SUM(total),2),0) FROM orders WHERE order_date BETWEEN ? AND ? AND status='выполнен'", (start.isoformat(), end.isoformat())).fetchone()[0]
        return {"period": period, "date_from": start.isoformat(), "date_to": end.isoformat(), "counts": counts, "top_customers": top, "revenue": float(revenue)}

    def export_data(self):
        with self.connect() as con:
            customers = [dict(r) for r in con.execute("SELECT * FROM customers ORDER BY id")]
        orders = []
        for row in self.list_orders():
            orders.append({"id": row["id"], "customer_id": row["customer_id"], "order_date": row["order_date"], "status": row["status"], "total": row["total"], "items": row["items"]})
        return {"customers": customers, "orders": orders}

    def import_data(self, data):
        if not isinstance(data, dict) or not isinstance(data.get("customers"), list) or not isinstance(data.get("orders"), list):
            raise ValueError("Файл должен содержать списки customers и orders")
        customers = {}
        for c in data["customers"]:
            if not isinstance(c, dict) or not isinstance(c.get("id"), int) or not c.get("name"):
                raise ValueError("Некорректные данные клиента")
            if c["id"] in customers: raise ValueError("Повторяется ID клиента")
            customers[c["id"]] = c
        parsed = []
        seen = set()
        for raw in data["orders"]:
            if not isinstance(raw, dict): raise ValueError("Некорректный заказ")
            old_id = raw.get("id")
            if not isinstance(old_id, int) or old_id in seen: raise ValueError("Некорректный или повторяющийся ID заказа")
            seen.add(old_id)
            cid = raw.get("customer_id")
            if cid not in customers: raise ValueError(f"У заказа {old_id} не найден клиент")
            items = [OrderItem(str(i.get("product_name", "")), int(i.get("quantity", 0)), float(i.get("price", -1))) for i in raw.get("items", [])]
            order = Order(cid, str(raw.get("order_date", "")), raw.get("status", ""), items, total=float(raw.get("total", -1)))
            order.validate()
            parsed.append((old_id, order))
        # Сначала полная проверка, затем транзакционная замена содержимого.
        with self.connect() as con:
            con.execute("DELETE FROM order_items"); con.execute("DELETE FROM orders"); con.execute("DELETE FROM customers")
            customer_id_map = {}
            for old_id, c in customers.items():
                cur = con.execute("INSERT INTO customers(id,name,phone,address) VALUES(?,?,?,?)", (old_id, c["name"].strip(), str(c.get("phone", "")), str(c.get("address", ""))))
                customer_id_map[old_id] = cur.lastrowid
            for old_id, o in parsed:
                cur = con.execute("INSERT INTO orders(id,customer_id,order_date,status,total) VALUES(?,?,?,?,?)", (old_id, customer_id_map[o.customer_id], o.order_date, o.status, o.total))
                con.executemany("INSERT INTO order_items(order_id,product_name,quantity,price) VALUES(?,?,?,?)", [(old_id, i.product_name.strip(), i.quantity, i.price) for i in o.items])
        return len(parsed)
