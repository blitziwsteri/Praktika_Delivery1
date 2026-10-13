"""Графический интерфейс Tkinter для управления заказами."""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from database import Database
from models import Customer, Order, OrderItem, STATUSES
from data_export import export_file, import_file
from logger_config import setup_logging

class DeliveryApp:
    def __init__(self, root=None, db=None):
        self.root = root or tk.Tk()
        self.db = db or Database()
        self.root.title("Быстрая доставка — учёт заказов")
        self.root.geometry("1100x600")
        self._build()
        self.refresh()

    def _build(self):
        bar = ttk.Frame(self.root, padding=8); bar.pack(fill="x")
        ttk.Label(bar, text="Статус:").pack(side="left")
        self.status_var = tk.StringVar(value="Все")
        self.status_combo = ttk.Combobox(
            bar, textvariable=self.status_var, values=("Все", *STATUSES),
            state="readonly", width=13
        )
        self.status_combo.pack(side="left", padx=4)
        self.status_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh())
        ttk.Label(bar, text="Дата:").pack(side="left", padx=(6, 2))
        self.date_var = tk.StringVar(value="")
        ttk.Entry(bar, textvariable=self.date_var, width=12, state="readonly").pack(side="left")
        ttk.Button(bar, text="📅", width=3, command=self.pick_filter_date).pack(side="left", padx=2)
        ttk.Button(bar, text="Сбросить дату", command=self.clear_date_filter).pack(side="left", padx=2)
        ttk.Button(bar, text="Экспорт", command=self.export_data).pack(side="right", padx=3)
        ttk.Button(bar, text="Импорт", command=self.import_data).pack(side="right", padx=3)
        cols = ("id", "date", "customer", "status", "total", "items")
        self.tree = ttk.Treeview(self.root, columns=cols, show="headings", selectmode="browse")
        labels = {"id":"№", "date":"Дата", "customer":"Клиент", "status":"Статус", "total":"Сумма", "items":"Товары"}
        widths = {"id":45,"date":95,"customer":230,"status":110,"total":90,"items":390}
        for col in cols:
            self.tree.heading(col, text=labels[col]); self.tree.column(col, width=widths[col], anchor="w")
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)
        bottom = ttk.Frame(self.root, padding=(8, 0, 8, 8)); bottom.pack(fill="x")
        left = ttk.Frame(bottom); left.pack(side="left")
        ttk.Button(left, text="Добавить заказ", command=self.add_order).pack(side="left", padx=(0, 5))
        ttk.Button(left, text="Редактировать", command=self.edit_order).pack(side="left", padx=5)
        ttk.Button(left, text="Удалить", command=self.delete_order).pack(side="left", padx=5)
        ttk.Button(left, text="Клиенты", command=self.show_customers).pack(side="left", padx=5)
        right = ttk.Frame(bottom); right.pack(side="right")
        ttk.Button(right, text="Отчёт", command=self.show_report).pack(side="right")
        self.root.bind("<Double-1>", lambda _e: self.edit_order())

    def refresh(self):
        for row in self.tree.get_children(): self.tree.delete(row)
        status = self.status_var.get()
        chosen_date = self.date_var.get().strip()
        try:
            rows = self.db.list_orders(status=None if status == "Все" else status,
                                       date_from=chosen_date or None, date_to=chosen_date or None)
        except ValueError as exc:
            messagebox.showerror("Фильтр даты", str(exc), parent=self.root); return
        for o in rows:
            items = ", ".join(f"{i['product_name']} × {i['quantity']}" for i in o["items"])
            self.tree.insert("", "end", iid=str(o["id"]), values=(o["id"], o["order_date"], o["customer_name"], o["status"], f"{o['total']:.2f}", items))

    def clear_date_filter(self):
        self.date_var.set("")
        self.refresh()

    def pick_filter_date(self):
        self._calendar_popup(self.root, self.date_var, self.refresh)

    def _calendar_popup(self, parent, target_var, callback=None):
        import calendar
        from datetime import date
        current_text = target_var.get().strip()
        try: selected = date.fromisoformat(current_text) if current_text else date.today()
        except ValueError: selected = date.today()
        win = tk.Toplevel(parent); win.title("Выберите дату"); win.transient(parent); win.grab_set()
        win.resizable(False, False)
        state = {"year": selected.year, "month": selected.month}
        head = ttk.Frame(win, padding=8); head.pack(fill="x")
        body = ttk.Frame(win, padding=(8, 0, 8, 8)); body.pack()
        def draw():
            for child in head.winfo_children(): child.destroy()
            for child in body.winfo_children(): child.destroy()
            ttk.Button(head, text="◀", width=3, command=lambda: shift(-1)).pack(side="left")
            ttk.Label(head, text=f"{calendar.month_name[state['month']]} {state['year']}", width=18, anchor="center").pack(side="left", padx=5)
            ttk.Button(head, text="▶", width=3, command=lambda: shift(1)).pack(side="left")
            for col, day_name in enumerate(("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")):
                ttk.Label(body, text=day_name, width=4, anchor="center").grid(row=0, column=col, pady=3)
            for row, week in enumerate(calendar.monthcalendar(state['year'], state['month']), start=1):
                for col, day_num in enumerate(week):
                    if day_num:
                        ttk.Button(body, text=str(day_num), width=4,
                                   command=lambda d=day_num: choose(d)).grid(row=row, column=col, padx=1, pady=1)
            ttk.Button(body, text="Сегодня", command=lambda: choose(date.today().day, date.today().year, date.today().month)).grid(row=7, column=0, columnspan=3, sticky="ew", pady=(6, 0))
            ttk.Button(body, text="Очистить", command=clear).grid(row=7, column=3, columnspan=4, sticky="ew", pady=(6, 0))
        def shift(delta):
            state['month'] += delta
            if state['month'] < 1: state['month'] = 12; state['year'] -= 1
            elif state['month'] > 12: state['month'] = 1; state['year'] += 1
            draw()
        def choose(day_num, year=None, month=None):
            from datetime import date
            target_var.set(date(year or state['year'], month or state['month'], day_num).isoformat())
            win.destroy()
            if callback: callback()
        def clear():
            target_var.set(""); win.destroy()
            if callback: callback()
        draw()

    def show_customers(self):
        win = tk.Toplevel(self.root); win.title("Клиенты"); win.geometry("760x420"); win.transient(self.root)
        cols = ("id", "name", "phone", "address")
        tree = ttk.Treeview(win, columns=cols, show="headings", selectmode="browse")
        for col, label, width in (("id", "ID", 55), ("name", "Имя", 180), ("phone", "Телефон", 150), ("address", "Адрес", 320)):
            tree.heading(col, text=label); tree.column(col, width=width, anchor="w")
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        def refresh_customers():
            for row in tree.get_children(): tree.delete(row)
            for customer in self.db.get_customers():
                tree.insert("", "end", iid=str(customer["id"]), values=(customer["id"], customer["name"], customer["phone"], customer["address"]))
        def selected_customer():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Клиенты", "Сначала выберите клиента.", parent=win); return None
            return int(selection[0])
        def customer_form(customer_id=None):
            current = self.db.get_customer(customer_id) if customer_id is not None else None
            form = tk.Toplevel(win); form.title("Редактировать клиента" if current else "Новый клиент"); form.transient(win); form.grab_set()
            body = ttk.Frame(form, padding=12); body.pack(fill="both", expand=True)
            vars_ = {}
            for row, (key, label) in enumerate((("name", "Имя"), ("phone", "Телефон"), ("address", "Адрес"))):
                ttk.Label(body, text=label+":").grid(row=row, column=0, sticky="w", padx=(0, 8), pady=5)
                var = tk.StringVar(value=(current or {}).get(key, "")); vars_[key] = var
                ttk.Entry(body, textvariable=var, width=38).grid(row=row, column=1, sticky="ew", pady=5)
            def save_customer():
                try:
                    customer = Customer(vars_["name"].get().strip(), vars_["phone"].get().strip(), vars_["address"].get().strip())
                    if customer_id is None: self.db.add_customer(customer)
                    else: self.db.update_customer(customer_id, customer)
                    refresh_customers(); form.destroy()
                except Exception as exc:
                    messagebox.showerror("Ошибка", str(exc), parent=form)
            buttons = ttk.Frame(body); buttons.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))
            ttk.Button(buttons, text="Сохранить", command=save_customer).pack(side="left")
            ttk.Button(buttons, text="Отмена", command=form.destroy).pack(side="right")
        def edit_customer():
            customer_id = selected_customer()
            if customer_id is not None: customer_form(customer_id)
        def delete_customer():
            customer_id = selected_customer()
            if customer_id is None: return
            if not messagebox.askyesno("Удаление клиента", "Удалить выбранного клиента? Клиента с заказами удалить нельзя.", parent=win): return
            try:
                self.db.delete_customer(customer_id); refresh_customers()
            except ValueError as exc:
                messagebox.showerror("Невозможно удалить", str(exc), parent=win)
        buttons = ttk.Frame(win, padding=(10, 0, 10, 10)); buttons.pack(fill="x")
        ttk.Button(buttons, text="Добавить клиента", command=customer_form).pack(side="left", padx=(0, 5))
        ttk.Button(buttons, text="Редактировать", command=edit_customer).pack(side="left", padx=5)
        ttk.Button(buttons, text="Удалить", command=delete_customer).pack(side="left", padx=5)
        ttk.Button(buttons, text="Закрыть", command=win.destroy).pack(side="right")
        refresh_customers()

    def _selected_id(self):
        sel = self.tree.selection()
        if not sel: messagebox.showwarning("Выбор заказа", "Сначала выберите заказ", parent=self.root); return None
        return int(sel[0])

    def _order_form(self, existing=None):
        customers = self.db.get_customers()
        if not customers:
            messagebox.showinfo(
                "Клиенты",
                "Сначала добавьте клиента через кнопку «Клиенты» или командой CLI.",
                parent=self.root,
            )
            return

        current = self.db.get_order(existing) if existing is not None else None
        win = tk.Toplevel(self.root)
        win.title("Редактирование заказа" if current else "Новый заказ")
        win.transient(self.root)
        win.grab_set()
        win.resizable(False, False)

        frame = ttk.Frame(win, padding=14)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        # Показываем ID и имя, чтобы клиентов с одинаковыми именами можно было различить.
        customer_map = {
            f"{customer['id']} — {customer['name']}": customer['id']
            for customer in customers
        }
        current_customer = next(
            (label for label, customer_id in customer_map.items()
             if current and customer_id == current["customer_id"]),
            next(iter(customer_map)),
        )
        customer_var = tk.StringVar(value=current_customer)

        ttk.Label(frame, text="Клиент:").grid(
            row=0, column=0, sticky="w", padx=(0, 12), pady=5
        )
        customer_combo = ttk.Combobox(
            frame, textvariable=customer_var, values=list(customer_map),
            state="readonly", width=38,
        )
        customer_combo.grid(row=0, column=1, sticky="ew", pady=5)

        status_labels = {
            "Новый": "новый",
            "В доставке": "в доставке",
            "Выполнен": "выполнен",
            "Отменён": "отменён",
        }
        current_status = current["status"] if current else "новый"
        current_status_label = next(
            (label for label, status in status_labels.items()
             if status == current_status),
            "Новый",
        )
        status_var = tk.StringVar(value=current_status_label)

        ttk.Label(frame, text="Статус заказа:").grid(
            row=1, column=0, sticky="w", padx=(0, 12), pady=5
        )
        ttk.Combobox(
            frame, textvariable=status_var, values=list(status_labels),
            state="readonly", width=38,
        ).grid(row=1, column=1, sticky="ew", pady=5)

        old_items = current["items"] if current else []
        first_item = old_items[0] if old_items else {}
        values = {
            "date": current["order_date"] if current else __import__("datetime").date.today().isoformat(),
            "product": first_item.get("product_name", ""),
            "quantity": str(first_item.get("quantity", 1)),
            "price": str(first_item.get("price", 0)),
        }
        fields = {}
        form_fields = (
            ("Дата (ГГГГ-ММ-ДД):", "date"),
            ("Товар:", "product"),
            ("Количество:", "quantity"),
            ("Цена за единицу:", "price"),
        )
        for row, (label, key) in enumerate(form_fields, start=2):
            ttk.Label(frame, text=label).grid(
                row=row, column=0, sticky="w", padx=(0, 12), pady=5
            )
            variable = tk.StringVar(value=values[key])
            fields[key] = variable
            ttk.Entry(frame, textvariable=variable, width=41).grid(
                row=row, column=1, sticky="ew", pady=5
            )

        ttk.Label(
            frame,
            text="Форма поддерживает одну товарную позицию. Несколько товаров можно импортировать из JSON/XML.",
            wraplength=400,
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(8, 4))

        def save():
            try:
                selected_customer = customer_map.get(customer_var.get())
                if selected_customer is None:
                    raise ValueError("Выберите клиента из списка.")
                item = OrderItem(
                    fields["product"].get().strip(),
                    int(fields["quantity"].get()),
                    float(fields["price"].get().replace(",", ".")),
                )
                order = Order(
                    selected_customer,
                    fields["date"].get().strip(),
                    status_labels[status_var.get()],
                    [item],
                )
                if existing is not None:
                    self.db.update_order(existing, order)
                else:
                    self.db.add_order(order)
                self.refresh()
                win.destroy()
            except (ValueError, KeyError, TypeError) as exc:
                messagebox.showerror("Ошибка данных", str(exc), parent=win)

        buttons = ttk.Frame(frame)
        buttons.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        ttk.Button(buttons, text="Сохранить", command=save).pack(side="left")
        ttk.Button(buttons, text="Отмена", command=win.destroy).pack(side="right")

    def add_order(self): self._order_form()
    def edit_order(self):
        oid = self._selected_id()
        if oid is not None: self._order_form(oid)
    def delete_order(self):
        oid = self._selected_id()
        if oid is not None and messagebox.askyesno("Удаление", f"Удалить заказ №{oid}?", parent=self.root):
            try: self.db.delete_order(oid); self.refresh()
            except ValueError as exc: messagebox.showerror("Ошибка", str(exc), parent=self.root)
    def show_report(self):
        win = tk.Toplevel(self.root); win.title("Отчёт за месяц"); win.transient(self.root)
        report = self.db.report("month")
        lines = [f"Период: {report['date_from']} — {report['date_to']}", "", "Количество заказов по статусам:"]
        lines += [f"  {s}: {n}" for s,n in report["counts"].items()]
        lines += ["", f"Выручка по выполненным заказам: {report['revenue']:.2f}", "", "Топ-3 клиента по сумме заказов:"]
        lines += [f"  {i}. {c['name']} — {c['total']:.2f}" for i,c in enumerate(report["top_customers"], 1)] or ["  Нет данных"]
        ttk.Label(win, text="\n".join(lines), padding=15, justify="left").pack(anchor="w")
    def export_data(self):
        filename = filedialog.asksaveasfilename(parent=self.root, defaultextension=".json", filetypes=(("JSON", "*.json"), ("XML", "*.xml")))
        if filename:
            try: count = export_file(self.db, filename); messagebox.showinfo("Экспорт", f"Экспортировано заказов: {count}", parent=self.root)
            except (ValueError, OSError) as exc: messagebox.showerror("Ошибка", str(exc), parent=self.root)
    def import_data(self):
        filename = filedialog.askopenfilename(parent=self.root, filetypes=(("JSON", "*.json"), ("XML", "*.xml")))
        if filename and messagebox.askyesno("Импорт", "Импорт заменит текущих клиентов и заказы. Продолжить?", parent=self.root):
            try: count = import_file(self.db, filename); self.refresh(); messagebox.showinfo("Импорт", f"Импортировано заказов: {count}", parent=self.root)
            except (ValueError, OSError) as exc: messagebox.showerror("Ошибка", str(exc), parent=self.root)

def main():
    setup_logging(); app = DeliveryApp(); app.root.mainloop()

if __name__ == "__main__": main()
