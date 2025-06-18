import asyncio
from astrbot.api.star import Context, Star, register
from astrbot.core.config.astrbot_config import AstrBotConfig
from astrbot.core.message.components import Plain
from astrbot.core.message.message_event_result import MessageChain
from astrbot.core.platform.astr_message_event import AstrMessageEvent
from astrbot.api.event import filter
from astrbot import logger

from data.plugins.astrbot_plugin_afdian.core.afdian_api import AfdianAPIClient
from data.plugins.astrbot_plugin_afdian.core.afdian_webhook import AfdianWebhookServer
from data.plugins.astrbot_plugin_afdian.core.utils import parse_order, parse_sponsors


@register(
    "astrbot_plugin_afdian",
    "Zhalslar",
    "爱发电插件",
    "1.0.0",
    "https://github.com/Zhalslar/astrbot_plugin_afdian",
)
class AfdianPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

        # WebHook方案
        webhook_config = config.get("webhook_config", {})
        self.host: str = webhook_config.get("host", "")
        self.port: int = webhook_config.get("port", 6500)
        self.server = AfdianWebhookServer(self.host, self.port)
        asyncio.create_task(self.server.start())
        self.server.register_order_callback(self.on_new_order)

        # API方案
        api_config = config.get("api_config", {})
        self.user_id: str = api_config.get("user_id", "")
        self.token: str = api_config.get("token", "")
        self.client = AfdianAPIClient(self.user_id, self.token)

        # 支付设置
        pay_config = config.get("pay_config", {})
        self.default_price: int = pay_config.get("default_price", 5)
        self.default_remark: str = pay_config.get("default_remark", [])

        # 接收爱发电通知的会话
        self.notices: list[str] = config.get("notices", [])

    async def on_new_order(self, order) -> None:
        """
        处理新订单的回调。

        Args:
            order (AfdianOrder): 新订单对象
        """
        logger.info(f"新订单：{order}")
        message_chain = MessageChain(chain=[Plain(parse_order(order))])
        for umo in set(self.notices):
            try:
                await self.context.send_message(
                    session=umo, message_chain=message_chain
                )
            except:  # noqa: E722
                pass

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("爱发电通知")
    async def afdian_notice(self, event: AstrMessageEvent):
        umo = event.unified_msg_origin
        if umo in self.notices:
            yield event.plain_result("当前会话无需重复开启爱发电")
            return
        self.notices.append(umo)
        self.config.save_config()
        yield event.plain_result(
            f"已在当前会话({event.unified_msg_origin})开启爱发电通知"
        )

    @filter.command("爱发电测试")
    async def test(self, event: AstrMessageEvent):
        """测试哪些会话接收爱发电订单通知"""
        await self.on_new_order(self.notices)
        event.stop_event()


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
        sponsor_user_ids = sponsor_user_ids or self.user_id
        sponsors = await self.client.query_sponsor(sponsor_user_ids=sponsor_user_ids)
        if not sponsors:
            yield event.plain_result("未找到该订单")
            return
        sponsor_list = parse_sponsors(sponsors)
        sponsor_str = "\n\n".join(sponsor_list)
        image = await self.text_to_image(text=sponsor_str)
        yield event.image_result(image)


    @filter.command("发电", alias={"赞助"})
    async def create_order(
        self, event: AstrMessageEvent, price: int = 5, remark: str | None = None
    ):
        """
        /发电 金额数（元） -向创作者发电
        """
        url = self.client.generate_payment_url(
            price=price or self.default_price,
            remark=remark or self.default_remark
        )
        yield event.plain_result(url)


    async def terminate(self):
        """
        当插件被禁用、重载插件时，会调用这个方法优雅地关闭爱发电 Webhook 服务。
        """
        await self.server.stop()
        await self.client.close()
