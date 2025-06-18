
import json
from aiohttp import web
from astrbot import logger
from data.plugins.astrbot_plugin_afdian.core.order_db import OrderDB


class AfdianWebhookServer:
    def __init__(self, host="0.0.0.0", port=6500):
        self.host = host
        self.port = port
        self.db = OrderDB()
        self._order_callback = None
        self.app = web.Application()
        self.runner = None
        self.site = None
        self.app.add_routes(
            [
                web.post("/", self.receive_webhook),
                web.get("/orders", self.list_orders),
            ]
        )

    def register_order_callback(self, callback):
        """注册订单回调函数（异步或同步函数均可）"""
        self._order_callback = callback

    async def list_orders(self, request: web.Request):
        orders = self.db.get_all_orders()
        return web.json_response(orders)

    async def receive_webhook(self, request: web.Request):
        try:
            data = await request.json()
            logger.info(f"收到爱发电订单通知：{json.dumps(data, ensure_ascii=False)}")

            order_info = data.get("data", {}).get("order", {})
            if not order_info:
                logger.warning("未找到订单信息")
                return web.json_response({"ec": 200, "em": "无订单"})

            await self.handle_order(order_info)
            return web.json_response({"ec": 200, "em": ""})

        except Exception as e:
            logger.error(f"处理通知失败: {e}")
            return web.json_response({"ec": 500, "em": "server error"}, status=500)

    async def handle_order(self, order: dict):
        self.db.save_order(order)
        logger.info(f"订单保存成功：{order.get('out_trade_no')}")

        if self._order_callback:
            if callable(self._order_callback):
                if hasattr(self._order_callback, "__call__"):
                    res = self._order_callback(order)
                    if hasattr(res, "__await__"):
                        await res  # 兼容 async 回调

    async def start(self):
        """异步启动 aiohttp Webhook 服务"""
        if self.runner and self.site:
            logger.warning("Webhook 已经启动，无需重复绑定")
            return
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, host=self.host, port=self.port)
        await self.site.start()
        logger.info(f"爱发电 Webhook 服务已启动：监听 {self.host}:{self.port}")

    async def stop(self):
        """异步关闭 Webhook 服务"""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        logger.info("爱发电 Webhook 服务已关闭")


