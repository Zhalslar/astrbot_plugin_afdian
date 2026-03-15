from __future__ import annotations

from astrbot import logger
from astrbot.api.event import filter
from astrbot.api.star import Context, Star, StarTools, register
from astrbot.core.config.astrbot_config import AstrBotConfig
from astrbot.core.message.components import Image, Plain
from astrbot.core.message.message_event_result import MessageChain
from astrbot.core.platform.astr_message_event import AstrMessageEvent
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)

from data.plugins.astrbot_plugin_afdian.core.afdian_api import AfdianAPIClient
from data.plugins.astrbot_plugin_afdian.core.afdian_webhook import AfdianWebhookServer
from data.plugins.astrbot_plugin_afdian.core.utils import (
    parse_order,
    parse_structured_payload,
    parse_webhook_payload,
)


@register(
    "astrbot_plugin_afdian",
    "Zhalslar",
    "爱发电插件",
    "1.0.4",
    "https://github.com/Zhalslar/astrbot_plugin_afdian",
)
class AfdianPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.plugin_data_dir = StarTools.get_data_dir("astrbot_plugin_afdian")

        self.webhook_config = config.get("webhook_config", {})
        self.host = self.webhook_config.get("host", "0.0.0.0")
        self.port = self.webhook_config.get("port", 6500)
        self.forward_config = self.webhook_config.get("forward", {})

        api_config = config.get("api_config", {})
        self.user_id: str = api_config.get("user_id", "")
        self.token: str = api_config.get("token", "")
        self.base_url: str = api_config.get("base_url", "https://ifdian.net")

        pay_config = config.get("pay_config", {})
        self.default_price: int = pay_config.get("default_price", 5)
        self.default_reply: str = pay_config.get("default_reply", "赞助成功")

        self.notice_sessions: list[str] = list(config.get("notices", []))
        self.pending_orders: dict[str, str] = {}
        self.bots = []
        self.server: AfdianWebhookServer | None = None
        self.client: AfdianAPIClient | None = None

    async def initialize(self):
        db_path = self.plugin_data_dir / "orders.db"
        self.server = AfdianWebhookServer(
            host=self.host,
            port=self.port,
            db_path=db_path,
            forward_config=self.forward_config,
        )
        self.server.register_order_callback(self.on_new_order)
        await self.server.start()

        self.client = AfdianAPIClient(
            user_id=self.user_id,
            token=self.token,
            base_url=self.base_url,
        )

    async def on_new_order(
        self,
        order: dict | None = None,
        payload: dict | None = None,
    ):
        logger.info(f"New Afdian order received: {order}")

        if payload:
            message = parse_webhook_payload(payload)
        elif order:
            message = parse_order(order)
        else:
            message = "Afdian webhook test"

        image = await self.text_to_image(message)

        for session_id in set(self.notice_sessions):
            try:
                await self.context.send_message(
                    session=session_id,
                    message_chain=MessageChain(chain=[Image(image)]),
                )
            except Exception as exc:
                logger.warning(f"[Notice failed] session={session_id}, error={exc}")

        if not order:
            return

        sender_id = order.get("remark") or ""
        if sender_id not in self.pending_orders:
            return

        session_id = self.pending_orders.pop(sender_id)
        try:
            await self.context.send_message(
                session=session_id,
                message_chain=MessageChain(chain=[Plain(self.default_reply)]),
            )
        except Exception as exc:
            if self.bots:
                await self.bots[0].send_private_msg(
                    user_id=int(sender_id), message=self.default_reply
                )
            else:
                logger.warning(
                    f"[Notice failed] pending session={session_id}, error={exc}"
                )

    @filter.command("发电", alias={"赞助"})
    async def create_order(self, event: AstrMessageEvent, price: int | None = None):
        if not self.client:
            yield event.plain_result("爱发电客户端尚未初始化")
            return

        self.pending_orders[event.get_sender_id()] = event.unified_msg_origin

        if event.get_platform_name() == "aiocqhttp":
            assert isinstance(event, AiocqhttpMessageEvent)
            self.bots.clear()
            self.bots.append(event.bot)

        url = self.client.generate_payment_url(
            price=price or self.default_price,
            remark=event.get_sender_id(),
        )
        yield event.plain_result(url)

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("查询订单")
    async def query_order(self, event: AstrMessageEvent, out_trade_no: str):
        if not self.client:
            yield event.plain_result("爱发电客户端尚未初始化")
            return

        response = await self.client.query_order_response(out_trade_no=out_trade_no)
        orders = response.get("data", {}).get("list", [])
        if not orders:
            yield event.plain_result("未找到该订单")
            return

        image = await self.text_to_image(parse_structured_payload("API query-order response", response))
        yield event.image_result(image)

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("查询发电", alias={"查询赞助"})
    async def query_sponsor(
        self, event: AstrMessageEvent, sponsor_user_ids: str | None = None
    ):
        if not self.client:
            yield event.plain_result("爱发电客户端尚未初始化")
            return

        response = await self.client.query_sponsor_response(
            sponsor_user_ids=sponsor_user_ids or ""
        )
        sponsors = response.get("data", {}).get("list", [])
        if not sponsors:
            yield event.plain_result("未找到赞助记录")
            return

        image = await self.text_to_image(
            parse_structured_payload("API query-sponsor response", response)
        )
        yield event.image_result(image)

    async def terminate(self):
        if self.server:
            await self.server.stop()
            self.server = None

        if self.client:
            await self.client.close()
            self.client = None
