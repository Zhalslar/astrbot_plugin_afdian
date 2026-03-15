from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any, Callable

from aiohttp import ClientSession, ClientTimeout, web
from astrbot import logger

from .order_db import OrderDB


class AfdianWebhookServer:
    def __init__(
        self,
        host: str,
        port: int,
        db_path: str | Path,
        forward_config: dict[str, Any] | None = None,
    ):
        self.host = host
        self.port = port
        self.db = OrderDB(db_path)
        self._order_callback: Callable[..., Any] | None = None
        self.app = web.Application()
        self.runner: web.AppRunner | None = None
        self.site: web.TCPSite | None = None

        self.forward_config = forward_config or {}
        self.forward_enabled = bool(self.forward_config.get("enabled"))
        self.forward_url = str(self.forward_config.get("url", "")).strip()
        self.forward_timeout = int(self.forward_config.get("timeout", 10) or 10)
        self.forward_session: ClientSession | None = None

        authorization = str(self.forward_config.get("authorization", "")).strip()
        self.forward_headers: dict[str, str] = {}
        if authorization:
            self.forward_headers["Authorization"] = authorization

        self.app.add_routes(
            [
                web.post("/", self.receive_webhook),
                web.get("/orders", self.list_orders),
            ]
        )

    def register_order_callback(self, callback: Callable[..., Any]) -> None:
        self._order_callback = callback

    async def list_orders(self, request: web.Request) -> web.Response:
        orders = self.db.get_all_orders()
        return web.json_response([dict(order) for order in orders])

    async def receive_webhook(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
        except Exception as exc:
            logger.error(f"Failed to parse webhook body: {exc}")
            return web.json_response({"ec": 400, "em": "invalid json"}, status=400)

        try:
            logger.info(
                "Received Afdian webhook: "
                f"{json.dumps(data, ensure_ascii=False, separators=(',', ':'))}"
            )

            await self.forward_webhook(data)

            order_info = data.get("data", {}).get("order", {})
            if not isinstance(order_info, dict) or not order_info:
                logger.warning("No order info found in webhook payload")
                return web.json_response({"ec": 200, "em": "no order"})

            await self.handle_order(order_info, data)
            return web.json_response({"ec": 200, "em": ""})
        except Exception as exc:
            logger.error(f"Failed to handle webhook: {exc}")
            return web.json_response({"ec": 500, "em": "server error"}, status=500)

    async def handle_order(self, order: dict[str, Any], payload: dict[str, Any]) -> None:
        self.db.save_order(order)  # type: ignore[arg-type]
        logger.info(f"Order saved successfully: {order.get('out_trade_no')}")
        await self.dispatch_order_callback(order, payload)

    async def dispatch_order_callback(
        self, order: dict[str, Any], payload: dict[str, Any]
    ) -> None:
        if not self._order_callback:
            return

        callback = self._order_callback
        parameters = inspect.signature(callback).parameters
        if len(parameters) >= 2:
            result = callback(order, payload)
        else:
            result = callback(order)

        if inspect.isawaitable(result):
            await result

    async def forward_webhook(self, payload: dict[str, Any]) -> None:
        if not self.forward_enabled or not self.forward_url:
            return

        if not self.forward_session:
            timeout = ClientTimeout(total=self.forward_timeout)
            self.forward_session = ClientSession(timeout=timeout)

        try:
            async with self.forward_session.post(
                self.forward_url,
                json=payload,
                headers=self.forward_headers or None,
            ) as response:
                response_text = await response.text()
                if response.status >= 400:
                    logger.warning(
                        "Webhook forward failed with "
                        f"status={response.status}, body={response_text}"
                    )
                    return
                logger.info(
                    "Webhook forwarded successfully: "
                    f"status={response.status}, body={response_text}"
                )
        except Exception as exc:
            logger.warning(f"Webhook forward failed: {exc}")

    async def start(self) -> None:
        if self.runner and self.site:
            logger.warning("Webhook server is already running")
            return

        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, host=self.host, port=self.port)
        await self.site.start()

        if self.forward_enabled and self.forward_url and not self.forward_session:
            timeout = ClientTimeout(total=self.forward_timeout)
            self.forward_session = ClientSession(timeout=timeout)

        logger.info(f"Afdian webhook server started on {self.host}:{self.port}")

    async def stop(self) -> None:
        if self.site:
            await self.site.stop()
            self.site = None

        if self.runner:
            await self.runner.cleanup()
            self.runner = None

        if self.forward_session:
            await self.forward_session.close()
            self.forward_session = None

        logger.info("Afdian webhook server stopped")
