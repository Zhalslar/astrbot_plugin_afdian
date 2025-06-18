import os
import sqlite3
import json
from typing import List, Optional, Union


class OrderDB:
    def __init__(self):
        self.db_path = os.path.join(os.getcwd(), "orders.db")
        self._init_db()

    def _init_db(self):
        """初始化订单表结构，并创建索引"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS afdian_orders (
                out_trade_no TEXT PRIMARY KEY,               -- 订单唯一编号
                user_id TEXT,                                -- 用户ID
                user_name TEXT,                              -- 用户名
                user_private_id TEXT,                        -- 用户私密ID
                plan_id TEXT,                                -- 方案ID
                plan_title TEXT,                             -- 方案名称
                month INTEGER,                               -- 订阅时长（月）
                total_amount REAL,                           -- 实际支付金额
                show_amount REAL,                            -- 展示金额（含折扣前）
                status INTEGER,                              -- 订单状态（如 2 = 成功）
                product_type INTEGER,                        -- 产品类型（0=虚拟，1=实体）
                discount REAL,                               -- 折扣金额
                remark TEXT,                                 -- 用户备注
                redeem_id TEXT,                              -- 兑换码ID
                sku_detail TEXT,                             -- SKU详情（JSON字符串）
                address_person TEXT,                         -- 收货人
                address_phone TEXT,                          -- 电话
                address_address TEXT,                        -- 地址
                create_time INTEGER                          -- 创建时间戳
            )
        """)

        # 可选索引（优化查询）
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_user_id ON afdian_orders(user_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_create_time ON afdian_orders(create_time)"
        )
        conn.commit()
        conn.close()

    def save_order(self, order: dict):
        """保存订单信息"""
        fields = {
            "out_trade_no": order.get("out_trade_no"),
            "user_id": order.get("user_id"),
            "user_name": order.get("user_name"),
            "user_private_id": order.get("user_private_id"),
            "plan_id": order.get("plan_id"),
            "plan_title": order.get("plan_title"),
            "month": order.get("month"),
            "total_amount": self._safe_float(order.get("total_amount")),
            "show_amount": self._safe_float(order.get("show_amount")),
            "status": order.get("status"),
            "product_type": order.get("product_type"),
            "discount": self._safe_float(order.get("discount")),
            "remark": order.get("remark"),
            "redeem_id": order.get("redeem_id"),
            "sku_detail": json.dumps(order.get("sku_detail", []), ensure_ascii=False),
            "address_person": order.get("address_person"),
            "address_phone": order.get("address_phone"),
            "address_address": order.get("address_address"),
            "create_time": int(order.get("create_time", 0)),
        }

        placeholders = ", ".join("?" * len(fields))
        columns = ", ".join(fields.keys())

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"""
                INSERT OR REPLACE INTO afdian_orders
                ({columns})
                VALUES ({placeholders})
                """,
                tuple(fields.values()),
            )
            conn.commit()
        finally:
            conn.close()

    def get_all_orders(self) -> List[sqlite3.Row]:
        """获取所有订单（按时间降序）"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM afdian_orders ORDER BY create_time DESC")
        rows = cursor.fetchall()
        conn.close()
        return rows

    def get_order_by_id(self, out_trade_no: str) -> Optional[sqlite3.Row]:
        """根据订单号获取订单"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM afdian_orders WHERE out_trade_no = ?", (out_trade_no,)
        )
        row = cursor.fetchone()
        conn.close()
        return row

    def get_orders_by_user(self, user_id: str) -> List[sqlite3.Row]:
        """获取指定用户的所有订单"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM afdian_orders WHERE user_id = ? ORDER BY create_time DESC",
            (user_id,),
        )
        rows = cursor.fetchall()
        conn.close()
        return rows

    def get_orders_by_status(self, status: int) -> List[sqlite3.Row]:
        """按订单状态筛选（如已支付 status=2）"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM afdian_orders WHERE status = ? ORDER BY create_time DESC",
            (status,),
        )
        rows = cursor.fetchall()
        conn.close()
        return rows

    def _safe_float(self, value: Union[str, float, int, None]) -> float:
        """辅助方法：将数值转换为 float，失败时返回 0.0"""
        try:
            return float(value) # type: ignore
        except (ValueError, TypeError):
            return 0.0
