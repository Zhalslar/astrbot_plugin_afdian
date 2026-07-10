import asyncio
import errno
import json

from aiohttp import web

from astrbot.api import logger

from .config import PluginConfig
from .order_db import OrderDB


class AfdianWebhookServer:
    def __init__(self, config: PluginConfig, db: OrderDB):
        self.cfg = config.webhook
        self.db = db
        self._order_callback = None
        self.app = web.Application()
        self.runner = None
        self.site = None
        self._started = False
        self._callback_tasks = set()
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
            resp = {"ec": 200, "em": ""}
            logger.info(f"响应：{json.dumps(resp, ensure_ascii=False)}")
            return web.json_response(resp)

        except Exception as e:
            logger.error(f"处理通知失败: {e}")
            return web.json_response({"ec": 500, "em": "server error"}, status=500)

    async def handle_order(self, order: dict):
        self.db.save_order(order)  # type: ignore
        logger.info(f"订单保存成功：{order.get('out_trade_no')}")

        if self._order_callback:
            if callable(self._order_callback):
                if hasattr(self._order_callback, "__call__"):
                    res = self._order_callback(order)
                    if hasattr(res, "__await__"):
                        task = asyncio.create_task(res)  # type: ignore
                        self._callback_tasks.add(task)

                        def on_callback_done(task: asyncio.Task) -> None:
                            self._callback_tasks.discard(task)
                            try:
                                task.result()
                            except asyncio.CancelledError:
                                pass
                            except Exception as e:
                                logger.error(f"订单回调处理失败: {e}")

                        task.add_done_callback(on_callback_done)

    async def start(self) -> bool:
        """Start the aiohttp webhook service.

        Returns:
            Whether the webhook service was started.

        Raises:
            OSError: The configured address cannot be bound for reasons other than
                being occupied.
        """
        if self._started:
            logger.warning("Webhook 已经启动，无需重复绑定")
            return True

        if self.runner or self.site:
            await self.stop()

        self.runner = web.AppRunner(self.app)
        try:
            await self.runner.setup()
            self.site = web.TCPSite(self.runner, host=self.cfg.host, port=self.cfg.port)
            await self.site.start()
            self._started = True
        except OSError as e:
            if self.runner:
                await self.runner.cleanup()
            self.runner = None
            self.site = None
            self._started = False

            if e.errno == errno.EADDRINUSE:
                logger.error(
                    f"爱发电 Webhook 端口已被占用，插件继续载入但不会启动监听："
                    f"{self.cfg.host}:{self.cfg.port}"
                )
                return False
            raise
        except Exception:
            if self.runner:
                await self.runner.cleanup()
            self.runner = None
            self.site = None
            self._started = False
            raise
        logger.info(f"爱发电 Webhook 服务已启动：监听 {self.cfg.host}:{self.cfg.port}")
        return True

    async def stop(self):
        """Stop the aiohttp webhook service."""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        for task in self._callback_tasks:
            task.cancel()
        self._callback_tasks.clear()
        self.runner = None
        self.site = None
        self._started = False
        logger.info("爱发电 Webhook 服务已关闭")
