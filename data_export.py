"""Импорт и экспорт заказов в JSON и XML."""
import json
import xml.etree.ElementTree as ET
from pathlib import Path


def export_file(database, filename):
    path = Path(filename)
    data = database.export_data()
    suffix = path.suffix.lower()
    if suffix == ".json":
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    elif suffix == ".xml":
        root = ET.Element("delivery")
        customers_el = ET.SubElement(root, "customers")
        for c in data["customers"]:
            el = ET.SubElement(customers_el, "customer", id=str(c["id"]))
            for key in ("name", "phone", "address"):
                ET.SubElement(el, key).text = str(c.get(key, ""))
        orders_el = ET.SubElement(root, "orders")
        for o in data["orders"]:
            el = ET.SubElement(orders_el, "order", id=str(o["id"]))
            for key in ("customer_id", "order_date", "status", "total"):
                ET.SubElement(el, key).text = str(o[key])
            items_el = ET.SubElement(el, "items")
            for item in o["items"]:
                iel = ET.SubElement(items_el, "item")
                for key in ("product_name", "quantity", "price"):
                    ET.SubElement(iel, key).text = str(item[key])
        ET.indent(root, space="  ")
        ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
    else:
        raise ValueError("Формат файла должен быть .json или .xml")
    return len(data["orders"])


def import_file(database, filename):
    path = Path(filename)
    suffix = path.suffix.lower()
    try:
        if suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
        elif suffix == ".xml":
            root = ET.parse(path).getroot()
            if root.tag != "delivery": raise ValueError("Корневой XML-элемент должен быть delivery")
            customers = []
            for el in root.findall("./customers/customer"):
                customers.append({"id": int(el.attrib["id"]), "name": el.findtext("name", ""), "phone": el.findtext("phone", ""), "address": el.findtext("address", "")})
            orders = []
            for el in root.findall("./orders/order"):
                items = [{"product_name": i.findtext("product_name", ""), "quantity": int(i.findtext("quantity", "0")), "price": float(i.findtext("price", "-1"))} for i in el.findall("./items/item")]
                orders.append({"id": int(el.attrib["id"]), "customer_id": int(el.findtext("customer_id", "0")), "order_date": el.findtext("order_date", ""), "status": el.findtext("status", ""), "total": float(el.findtext("total", "-1")), "items": items})
            data = {"customers": customers, "orders": orders}
        else:
            raise ValueError("Формат файла должен быть .json или .xml")
    except (OSError, json.JSONDecodeError, ET.ParseError, KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Не удалось прочитать или проверить файл: {exc}") from exc
    return database.import_data(data)
