"""Командный интерфейс системы доставки."""
import argparse
import json
import logging
from database import Database
from models import Customer, Order, OrderItem, STATUSES
from data_export import export_file, import_file
from logger_config import setup_logging


def build_parser():
    parser = argparse.ArgumentParser(description="Система учёта заказов компании «Быстрая доставка»")
    parser.add_argument("--db", help="Путь к SQLite-файлу базы данных")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("customers", help="Показать клиентов")
    addc = sub.add_parser("add-customer", help="Добавить клиента")
    addc.add_argument("--name", required=True); addc.add_argument("--phone", default=""); addc.add_argument("--address", default="")
    updatec = sub.add_parser("update-customer", help="Изменить клиента")
    updatec.add_argument("--id", type=int, required=True); updatec.add_argument("--name", required=True); updatec.add_argument("--phone", default=""); updatec.add_argument("--address", default="")
    delc = sub.add_parser("delete-customer", help="Удалить клиента без заказов")
    delc.add_argument("--id", type=int, required=True)
    addo = sub.add_parser("add-order", help="Добавить заказ")
    addo.add_argument("--customer-id", type=int, required=True, help="ID клиента из команды customers")
    addo.add_argument("--product", required=True, help="Название товара")
    addo.add_argument("--quantity", type=int, default=1, help="Количество")
    addo.add_argument("--price", type=float, required=True, help="Цена за единицу")
    addo.add_argument("--date", help="Дата YYYY-MM-DD; по умолчанию сегодня")
    addo.add_argument("--status", choices=STATUSES, default="новый")
    orders = sub.add_parser("orders", help="Показать заказы")
    orders.add_argument("--status", choices=("новый", "в доставке", "выполнен", "отменён"))
    orders.add_argument("--date-from", help="Дата от YYYY-MM-DD")
    orders.add_argument("--date-to", help="Дата до YYYY-MM-DD")
    report = sub.add_parser("report", help="Сформировать отчёт")
    report.add_argument("--period", choices=("day", "week", "month"), default="month")
    report.add_argument("--date", help="Опорная дата YYYY-MM-DD; по умолчанию сегодня")
    exp = sub.add_parser("export", help="Экспортировать все данные и заказы")
    exp.add_argument("--file", required=True)
    imp = sub.add_parser("import", help="Импортировать данные из файла (заменяет текущие данные)")
    imp.add_argument("--file", required=True)
    return parser


def main(argv=None):
    setup_logging()
    args = build_parser().parse_args(argv)
    db = Database(args.db) if args.db else Database()
    try:
        if args.command == "customers":
            print(json.dumps(db.get_customers(), ensure_ascii=False, indent=2))
        elif args.command == "add-customer":
            print(f"Создан клиент ID={db.add_customer(Customer(args.name, args.phone, args.address))}")
        elif args.command == "update-customer":
            db.update_customer(args.id, Customer(args.name, args.phone, args.address)); print("Клиент обновлён")
        elif args.command == "delete-customer":
            db.delete_customer(args.id); print("Клиент удалён")
        elif args.command == "add-order":
            from datetime import date
            if not db.get_customer(args.customer_id):
                raise ValueError(f"Клиент с ID={args.customer_id} не найден. Выполните: python main_cli.py customers")
            order = Order(args.customer_id, args.date or date.today().isoformat(), args.status,
                          [OrderItem(args.product, args.quantity, args.price)])
            print(f"Создан заказ ID={db.add_order(order)}")
        elif args.command == "orders":
            print(json.dumps(db.list_orders(args.status, args.date_from, args.date_to), ensure_ascii=False, indent=2))
        elif args.command == "report":
            print(json.dumps(db.report(args.period, args.date), ensure_ascii=False, indent=2))
        elif args.command == "export":
            count = export_file(db, args.file); print(f"Экспортировано заказов: {count}")
            logging.info("Экспортировано %s заказов в %s", count, args.file)
        elif args.command == "import":
            count = import_file(db, args.file); print(f"Импортировано заказов: {count}")
            logging.info("Импортировано %s заказов из %s", count, args.file)
    except (ValueError, OSError) as exc:
        logging.exception("Ошибка выполнения команды")
        print(f"Ошибка: {exc}")
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
