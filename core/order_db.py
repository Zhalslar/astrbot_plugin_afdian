
import json
import sqlite3
from decimal import Decimal
from pathlib import Path
from typing import TypedDict


class OrderDict(TypedDict, total=False):
    out_trade_no: str
    user_id: str
    user_name: str
    user_private_id: str
    plan_id: str
    plan_title: str
    month: int
    total_amount: str | float | int
    show_amount: str | float | int
    status: int
    product_type: int
    discount: str | float | int
    remark: str
    redeem_id: str
    sku_detail: list
    address_person: str
    address_phone: str
    address_address: str
    create_time: int


class OrderDB:
    def __init__(self, db_path: str|Path):
        self.db_path = str(db_path)
        self._init_db()

    def _init_db(self):
        """初始化订单表结构，并创建索引"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 创建表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS afdian_orders (
                    out_trade_no TEXT PRIMARY KEY,
                    user_id TEXT,
                    user_name TEXT,
                    user_private_id TEXT,
                    plan_id TEXT,
                    plan_title TEXT,
                    month INTEGER,
                    total_amount REAL,
                    show_amount REAL,
                    status INTEGER,
                    product_type INTEGER,
                    discount REAL,
                    remark TEXT,
                    redeem_id TEXT,
                    sku_detail TEXT,
                    address_person TEXT,
                    address_phone TEXT,
                    address_address TEXT,
                    create_time INTEGER
                )
            """)

            # 索引
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_user_id ON afdian_orders(user_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_create_time ON afdian_orders(create_time)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_remark ON afdian_orders(remark)"
            )
            conn.commit()

    def save_order(self, order: OrderDict):
        """保存订单信息"""
        fields = {
            "out_trade_no": order.get("out_trade_no") or "",
            "user_id": order.get("user_id") or "",
            "user_name": order.get("user_name") or "",
            "user_private_id": order.get("user_private_id") or "",
            "plan_id": order.get("plan_id") or "",
            "plan_title": order.get("plan_title") or "",
            "month": order.get("month") or 0,
            "total_amount": self._safe_float(order.get("total_amount")),
            "show_amount": self._safe_float(order.get("show_amount")),
            "status": order.get("status") or 0,
            "product_type": order.get("product_type") or 0,
            "discount": self._safe_float(order.get("discount")),
            "remark": order.get("remark") or "",
            "redeem_id": order.get("redeem_id") or "",
            "sku_detail": json.dumps(order.get("sku_detail") or [], ensure_ascii=False),
            "address_person": order.get("address_person") or "",
            "address_phone": order.get("address_phone") or "",
            "address_address": order.get("address_address") or "",
            "create_time": int(order.get("create_time") or 0),
        }

        placeholders = ", ".join("?" * len(fields))
        columns = ", ".join(fields.keys())

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                f"""
                INSERT OR REPLACE INTO afdian_orders
                ({columns})
                VALUES ({placeholders})
                """,
                tuple(fields.values()),
            )
            conn.commit()

    def get_all_orders(self) -> list[sqlite3.Row]:
        """获取所有订单（按时间降序）"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM afdian_orders ORDER BY create_time DESC")
            return cursor.fetchall()

    def get_order_by_id(self, out_trade_no: str) -> sqlite3.Row | None:
        """根据订单号获取订单"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM afdian_orders WHERE out_trade_no = ?", (out_trade_no,)
            )
            return cursor.fetchone()

    def get_orders_by_user(self, user_id: str) -> list[sqlite3.Row]:
        """获取指定用户的所有订单"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM afdian_orders WHERE user_id = ? ORDER BY create_time DESC",
                (user_id,),
            )
            return cursor.fetchall()

    def get_orders_by_status(self, status: int) -> list[sqlite3.Row]:
        """按订单状态筛选"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM afdian_orders WHERE status = ? ORDER BY create_time DESC",
                (status,),
            )
            return cursor.fetchall()

    @staticmethod
    def _safe_float(value: str | float | int | Decimal | None) -> float:
        """将任意值转换为 float，失败则返回 0.0"""
        try:
            return float(value) # type: ignore
        except (ValueError, TypeError):
            return 0.0
