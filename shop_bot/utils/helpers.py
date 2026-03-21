import json
from config import ORDER_STATUSES


def format_price(price: float, currency: str = "so'm") -> str:
    return f"{price:,.0f} {currency}".replace(",", " ")


def get_effective_price(product: dict) -> float:
    if product.get("discount_price"):
        return float(product["discount_price"])
    return float(product["price"])


def parse_json_field(value: str) -> list:
    if not value:
        return []
    try:
        return json.loads(value)
    except Exception:
        return []


def cart_total(cart_items: list) -> float:
    total = 0.0
    for item in cart_items:
        price = get_effective_price(item)
        total += price * item["quantity"]
    return total


def format_order_text(order: dict, items: list, currency: str = "so'm") -> str:
    status_label = ORDER_STATUSES.get(order["status"], order["status"])
    lines = [
        f"🧾 <b>Buyurtma #{order['id']}</b>",
        f"📅 {order['created_at'][:16]}",
        f"👤 {order.get('full_name') or order.get('user_name', '—')}",
        f"📞 {order.get('phone', '—')}",
        f"📍 {order.get('address', '—')}",
        f"🚚 {order.get('delivery_type', '—')}",
        f"💳 {order.get('payment_type', '—')}",
        f"📊 Holat: {status_label}",
        "",
        "<b>Mahsulotlar:</b>",
    ]
    for it in items:
        extras = []
        if it.get("size"):
            extras.append(f"o'lcham: {it['size']}")
        if it.get("color"):
            extras.append(f"rang: {it['color']}")
        extra_str = f" ({', '.join(extras)})" if extras else ""
        lines.append(
            f"• {it['product_name']}{extra_str} x{it['quantity']} = {format_price(it['price'] * it['quantity'], currency)}"
        )
    if order.get("discount_amount") and float(order["discount_amount"]) > 0:
        lines.append(f"\n🎁 Chegirma: -{format_price(order['discount_amount'], currency)}")
    lines.append(f"\n💰 <b>Jami: {format_price(order['total_amount'], currency)}</b>")
    if order.get("comment"):
        lines.append(f"\n💬 Izoh: {order['comment']}")
    if order.get("admin_note"):
        lines.append(f"\n📝 Admin izohi: {order['admin_note']}")
    return "\n".join(lines)
