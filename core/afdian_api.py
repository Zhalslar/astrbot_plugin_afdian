import time
import hashlib
import json
import aiohttp
from astrbot import logger


class AfdianAPIClient:
    def __init__(self, user_id: str, token: str):
        """
        Afdian 异步 API 客户端
        :param user_id: 爱发电用户 ID
        :param token: 爱发电开放平台 Token，用于签名
        """
        self.user_id = user_id
        self.token = token
        self.base_url = "https://afdian.com/api/open"
        self.session = aiohttp.ClientSession()

    async def close(self):
        """关闭 aiohttp 会话（建议在应用退出时调用）"""
        await self.session.close()

    def _generate_sign(self, params: dict, ts: int) -> str:
        """
        生成请求签名 sign
        :param params: 请求参数 dict
        :param ts: 秒级时间戳
        :return: MD5 签名字符串
        """
        params_str = json.dumps(params, separators=(",", ":"))
        kv_string = f"params{params_str}ts{ts}user_id{self.user_id}"
        sign_raw = self.token + kv_string
        return hashlib.md5(sign_raw.encode("utf-8")).hexdigest()

    async def _post(self, endpoint: str, params: dict) -> dict:
        """
        发起 POST 请求
        :param endpoint: API 接口路径（如 /ping）
        :param params: 请求参数
        :return: 响应 dict
        """
        ts = int(time.time())
        sign = self._generate_sign(params, ts)
        payload = {
            "user_id": self.user_id,
            "params": json.dumps(params, separators=(",", ":")),
            "ts": ts,
            "sign": sign,
        }

        url = self.base_url + endpoint
        try:
            async with self.session.post(url, json=payload, timeout=10) as resp: # type: ignore
                resp.raise_for_status()
                return await resp.json()
        except aiohttp.ClientError as e:
            logger.error(f"[Afdian] 请求失败: {e}")
            return {"ec": -1, "em": str(e)}

    async def ping(self) -> dict:
        """测试接口连通性及签名是否正确"""
        return await self._post("/ping", {"a": 114514})

    async def query_order(
        self, page: int = 1, out_trade_no: str = "", per_page: int = 50
    ) -> list[dict]:
        """
        查询订单列表
        :param page: 页码
        :param out_trade_no: 指定订单号（可多个，用英文逗号分隔）
        :param per_page: 每页数量（默认50，最大100）
        :return: 订单信息列表
        """
        params: dict = {"page": page, "per_page": per_page}
        if out_trade_no:
            params["out_trade_no"] = out_trade_no
        res = await self._post("/query-order", params)
        logger.info(f"[Afdian] 查询订单 {out_trade_no} 结果: {res}")
        return res.get("data", {}).get("list", [])

    async def query_sponsor(
        self, page: int = 1, sponsor_user_ids: str = "", per_page: int = 20
    ) -> dict:
        """
        查询赞助者列表
        :param page: 页码
        :param sponsor_user_ids: 用户ID，多个用英文逗号分隔
        :param per_page: 每页数量
        :return: 返回 data 字典
        """
        params: dict = {"page": page, "user_id": sponsor_user_ids, "per_page": per_page}
        sponsors = await self._post("/query-sponsor", params)
        logger.info(f"[Afdian] 查询赞助者({sponsor_user_ids}) 结果: {sponsors}")
        return sponsors.get("data", {})


    def generate_payment_url(self, price: float, remark: str):
        """
        快速生成支付跳转链接（适合手动支付流程，无需签名）

        :param order_no: 自定义订单号
        :param amount: 金额（单位：元）
        :return: 跳转链接
        """
        price_str = f"{round(price, 2):.2f}"
        url = (
            f"https://afdian.com/order/create?"
            f"user_id={self.user_id}"
            f"&remark={remark}"
            f"&custom_price={price_str}"
        )
        logger.debug(f"生成跳转链接：{url}")
        return url


