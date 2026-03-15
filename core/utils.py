from __future__ import annotations

from datetime import datetime
import textwrap
from typing import Any


def format_time(timestamp: Any) -> str | None:
    """Format a unix timestamp into local time."""
    if timestamp in (None, "", 0, "0"):
        return None

    try:
        return datetime.fromtimestamp(int(timestamp)).strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError, OSError):
        return str(timestamp)


def _stringify_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if value == "":
        return '""'
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _append_scalar_lines(lines: list[str], key: str | None, value: Any, indent: int) -> None:
    prefix = "  " * indent
    text = _stringify_scalar(value)

    if key is None:
        wrapped = textwrap.wrap(
            text,
            width=92,
            break_long_words=False,
            break_on_hyphens=False,
        ) or [text]
        lines.extend(f"{prefix}{part}" for part in wrapped)
        return

    available_width = max(24, 92 - len(prefix) - len(key) - 2)
    wrapped = textwrap.wrap(
        text,
        width=available_width,
        break_long_words=False,
        break_on_hyphens=False,
    ) or [text]

    lines.append(f"{prefix}{key}: {wrapped[0]}")
    if len(wrapped) == 1:
        return

    continuation_prefix = f"{prefix}{' ' * (len(key) + 2)}"
    for part in wrapped[1:]:
        lines.append(f"{continuation_prefix}{part}")


def _append_payload_lines(
    lines: list[str], key: str | None, value: Any, indent: int = 0
) -> None:
    prefix = "  " * indent

    if isinstance(value, dict):
        if key is not None:
            lines.append(f"{prefix}{key}:")
            indent += 1
        if not value:
            lines.append(f"{'  ' * indent}{{}}")
            return
        for child_key, child_value in value.items():
            _append_payload_lines(lines, str(child_key), child_value, indent)
        return

    if isinstance(value, list):
        if key is not None:
            lines.append(f"{prefix}{key}:")
            indent += 1
        if not value:
            lines.append(f"{'  ' * indent}[]")
            return
        for index, item in enumerate(value):
            _append_payload_lines(lines, f"[{index}]", item, indent)
        return

    _append_scalar_lines(lines, key, value, indent)


def parse_structured_payload(title: str, payload: Any) -> str:
    """Render any structured payload into a readable text block."""
    lines = [title]
    _append_payload_lines(lines, None, payload)
    return "\n".join(lines)


def parse_webhook_payload(payload: dict[str, Any]) -> str:
    """Render the complete webhook payload into a readable text block."""
    return parse_structured_payload("Webhook payload", payload)


def parse_order(order: dict[str, Any]) -> str:
    """Render a concise order summary."""
    fields = {
        "Order No": order.get("out_trade_no"),
        "Plan Title": order.get("plan_title"),
        "User Name": order.get("user_name"),
        "User ID": order.get("user_id"),
        "Plan ID": order.get("plan_id"),
        "Month": f"{order['month']} month(s)" if order.get("month") else None,
        "Total Amount": order.get("total_amount"),
        "Show Amount": order.get("show_amount"),
        "Status": order.get("status"),
        "Product Type": order.get("product_type"),
        "Discount": order.get("discount"),
        "Remark": order.get("remark"),
        "Redeem ID": order.get("redeem_id"),
        "Address Person": order.get("address_person"),
        "Address Phone": order.get("address_phone"),
        "Address Address": order.get("address_address"),
        "Create Time": format_time(order.get("create_time")),
    }

    lines = ["Order info"]
    lines.extend(
        f"- {key}: {value}"
        for key, value in fields.items()
        if value not in (None, "", "N/A")
    )

    sku_detail = order.get("sku_detail", [])
    if sku_detail:
        lines.append("- SKU Detail:")
        for sku in sku_detail:
            if not isinstance(sku, dict):
                lines.append(f"  - {sku}")
                continue
            name = sku.get("name", "unknown")
            count = sku.get("count", "N/A")
            sku_id = sku.get("sku_id", "N/A")
            lines.append(f"  - {name} x {count} (SKU ID: {sku_id})")

    return "\n".join(lines)


def parse_sponsors(data: dict[str, Any]) -> list[str]:
    """Render sponsor information for image output."""
    formatted_list: list[str] = []

    for item in data.get("list", []):
        user = item.get("user", {})
        current = item.get("current_plan", {})

        sponsor_info = {
            "name": user.get("name", ""),
            "user_id": user.get("user_id", ""),
            "total_amount": float(item.get("all_sum_amount", 0) or 0),
            "current_plan": {
                "name": current.get("name", ""),
                "price": float(current.get("price", 0) or 0),
            },
            "first_pay": format_time(item.get("first_pay_time")),
            "last_pay": format_time(item.get("last_pay_time")),
        }

        lines = [
            f"Sponsor: {sponsor_info['name']} (ID: {sponsor_info['user_id']})",
            (
                "Current Plan: "
                f"{sponsor_info['current_plan']['name']} "
                f"({sponsor_info['current_plan']['price']:.2f})"
            ),
            f"First Pay: {sponsor_info['first_pay'] or 'N/A'}",
            f"Last Pay: {sponsor_info['last_pay'] or 'N/A'}",
            f"Total Amount: {sponsor_info['total_amount']:.2f}",
        ]

        formatted_list.append("\n".join(lines))

    return formatted_list
