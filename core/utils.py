from datetime import datetime


@staticmethod
def format_time(timestamp):
    """格式化时间戳为日期时间字符串"""
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def parse_order(order: dict) -> str:
    """
    解析 order 数据
    """
    # 收集字段（None 或空字符串将跳过）
    fields = {
        "交易号": order.get("out_trade_no"),
        "计划标题": order.get("plan_title"),
        "用户名": order.get("user_name"),
        "用户ID": order.get("user_id"),
        "计划ID": order.get("plan_id"),
        "时长": f"{order['month']}个月" if order.get("month") else None,
        "总金额": order.get("total_amount"),
        "订单状态": order.get("status"),
        "产品类型": order.get("product_type"),
        "折扣": order.get("discount"),
        "备注": order.get("remark"),
        "兑换码ID": order.get("redeem_id"),
        "创建时间": format_time(int(order["create_time"])),
    }

    # 构建非空字段的输出行
    lines = ["📦 订单信息："]
    lines += [
        f"- {k}: {v}" for k, v in fields.items() if v not in [None, "", "N/A"]
    ]

    # 处理 SKU 信息（如果存在）
    sku_detail = order.get("sku_detail", [])
    sku_lines = [
        f"  - {sku.get('name', '未知')} × {sku.get('count', 'N/A')} (SKU ID: {sku.get('sku_id', 'N/A')})"
        for sku in sku_detail
        if any(sku.get(key) for key in ("name", "count", "sku_id"))
    ]
    if sku_lines:
        lines.append("SKU 列表：")
        lines.extend(sku_lines)

    return "\n".join(lines)


def parse_sponsors(data: dict) -> list[str]:
    """
    解析赞助者数据
    """
    formatted_list = []

    for item in data.get("list", []):
        user = item.get("user", {})
        current = item.get("current_plan", {})
        plans = item.get("sponsor_plans", [])

        plan_list = [
            {
                "name": p.get("name", "未知方案"),
                "price": float(p.get("price", 0)),
            }
            for p in plans
        ]
        plan_list.sort(key=lambda x: x["price"])

        sponsor_info = {
            "name": user.get("name", ""),
            "user_id": user.get("user_id", ""),
            "avatar": user.get("avatar", ""),
            "total_amount": float(item.get("all_sum_amount", 0)),
            "current_plan": {
                "name": current.get("name", ""),
                "price": float(current.get("price", 0)),
            },
            "first_pay": format_time(item.get("first_pay_time", 0)),
            "last_pay": format_time(item.get("last_pay_time", 0))
        }

        lines = [
            f"🎉 赞助主体： {sponsor_info['name']}（ID: {sponsor_info['user_id']}）\n",
            f"📦 赞助方案：{sponsor_info['current_plan']['name']}（{sponsor_info['current_plan']['price']:.2f}）元\n",
            f"📆 首次赞助：{sponsor_info['first_pay']}\n",
            f"📆 最近赞助：{sponsor_info['last_pay']}\n",
            f"💰 总计赞助：{sponsor_info['total_amount']:.2f}元",
        ]

        formatted_list.append("\n".join(lines))

    return formatted_list
