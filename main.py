from astrbot import logger
from astrbot.api.event import filter
from astrbot.api.star import Context, Star
from astrbot.core.config.astrbot_config import AstrBotConfig
from astrbot.core.message.components import Image, Plain
from astrbot.core.message.message_event_result import MessageChain
from astrbot.core.platform.astr_message_event import AstrMessageEvent
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)

from .core.afdian_api import AfdianAPIClient
from .core.afdian_webhook import AfdianWebhookServer
from .core.config import PluginConfig
from .core.order_db import OrderDB
from .core.utils import parse_order, parse_sponsors


class AfdianPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.context = context
        self.cfg = PluginConfig(config, context)
        # 数据库
        self.db = OrderDB(self.cfg.db_path)
        # WebHook方案
        self.server = AfdianWebhookServer(self.cfg, self.db)
        # API方案
        self.client = AfdianAPIClient(self.cfg)
        # remark -> session_id
        self.pending_orders: dict[str, str] = {}
        # 当前机器人
        self.bots = []

    async def initialize(self):
        """插件加载时"""
        await self.server.start()
        self.server.register_order_callback(self.on_new_order)

    async def terminate(self):
        """插件卸载时"""
        await self.server.stop()
        await self.client.close()


    async def on_new_order(self, order: dict | None = None):
        """
        处理新订单的回调。通知订阅者，但失败不会影响主流程。
        """
        logger.info(f"新订单：{order}")
        message = parse_order(order) if order else "爱发电测试"
        image = await self.text_to_image(message)

        # 通知所有订阅者（失败不会中断流程）
        for umo in self.cfg.notice_sessions:
            try:
                await self.context.send_message(
                    session=umo, message_chain=MessageChain(chain=[Image(image)])
                )
            except Exception as e:
                logger.warning(f"[通知失败] 订阅者 {umo}：{e}")

        # 检查是否为特定用户的订单（通过 remark 作为 sender_id）
        if order:
            sender_id = order.get("remark") or ""
            if sender_id in self.pending_orders:
                umo = self.pending_orders.pop(sender_id)
                try:
                    await self.context.send_message(
                        session=umo,
                        message_chain=MessageChain(chain=[Plain(self.cfg.pay.default_reply)]),
                    )
                except Exception as e:
                    # 不太优雅的备用方案
                    if self.bots:
                        await self.bots[0].send_private_msg(
                            user_id=int(sender_id), message=message
                        )
                    else:
                        logger.warning(f"[通知失败] 特定用户 {umo}：{e}")

    @filter.command("发电", alias={"赞助"})
    async def create_order(self, event: AstrMessageEvent, price: int | None = None):
        """
        /发电 金额数（元） -向创作者发电(备注里填用户ID，如QQ号)
        """
        self.pending_orders[event.get_sender_id()] = event.unified_msg_origin
        if event.get_platform_name() == "aiocqhttp":
            assert isinstance(event, AiocqhttpMessageEvent)
            self.bots.clear()
            self.bots.append(event.bot)
        url = self.client.generate_payment_url(
            price=price or self.cfg.pay.default_price, remark=event.get_sender_id()
        )
        yield event.plain_result(url)

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("查询订单")
    async def query_order(self, event: AstrMessageEvent, out_trade_no: str):
        """查询订单"""
        orders = await self.client.query_order(out_trade_no=out_trade_no)
        if not orders:
            yield event.plain_result("未找到该订单")
            return
        for order in orders:
            image = await self.text_to_image(text=parse_order(order))
            yield event.image_result(image)

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("查询发电", alias={"查询赞助"})
    async def query_sponsor(
        self, event: AstrMessageEvent, sponsor_user_ids: str | None = None
    ):
        """
        查询自己的收到的发电情况
        """
        sponsor_user_ids = sponsor_user_ids or self.cfg.api.user_id
        sponsors = await self.client.query_sponsor(sponsor_user_ids=sponsor_user_ids)
        if not sponsors:
            yield event.plain_result("未找到该订单")
            return
        sponsor_list = parse_sponsors(sponsors)
        sponsor_str = "\n\n".join(sponsor_list)
        image = await self.text_to_image(text=sponsor_str)
        yield event.image_result(image)

