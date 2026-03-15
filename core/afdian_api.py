from __future__ import annotations

import hashlib
import json
import time
from typing import Any

import aiohttp
from astrbot import logger


class AfdianAPIClient:
    def __init__(self, user_id: str, token: str, base_url: str = "https://ifdian.net"):
        self.user_id = user_id
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.api_base_url = f"{self.base_url}/api/open"
        self.order_base_url = f"{self.base_url}/order/create"
        self.session = aiohttp.ClientSession()

    async def close(self):
        await self.session.close()

    def _generate_sign(self, params: dict[str, Any], ts: int) -> str:
        params_str = json.dumps(params, separators=(",", ":"))
        kv_string = f"params{params_str}ts{ts}user_id{self.user_id}"
        sign_raw = self.token + kv_string
        return hashlib.md5(sign_raw.encode("utf-8")).hexdigest()

    async def _post(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        ts = int(time.time())
        sign = self._generate_sign(params, ts)
        payload = {
            "user_id": self.user_id,
            "params": json.dumps(params, separators=(",", ":")),
            "ts": ts,
            "sign": sign,
        }

        url = f"{self.api_base_url}{endpoint}"
        try:
            async with self.session.post(url, json=payload, timeout=10) as resp:  # type: ignore[arg-type]
                resp.raise_for_status()
                return await resp.json()
        except aiohttp.ClientError as exc:
            logger.error(f"[Afdian] Request failed: {exc}")
            return {"ec": -1, "em": str(exc)}

    async def ping(self) -> dict[str, Any]:
        return await self._post("/ping", {"a": 114514})

    async def query_order(
        self, page: int = 1, out_trade_no: str = "", per_page: int = 50
    ) -> list[dict[str, Any]]:
        response = await self.query_order_response(
            page=page,
            out_trade_no=out_trade_no,
            per_page=per_page,
        )
        return response.get("data", {}).get("list", [])

    async def query_order_response(
        self, page: int = 1, out_trade_no: str = "", per_page: int = 50
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if out_trade_no:
            params["out_trade_no"] = out_trade_no
        response = await self._post("/query-order", params)
        logger.info(f"[Afdian] Query order {out_trade_no} response: {response}")
        return response

    async def query_sponsor(
        self, page: int = 1, sponsor_user_ids: str = "", per_page: int = 20
    ) -> dict[str, Any]:
        response = await self.query_sponsor_response(
            page=page,
            sponsor_user_ids=sponsor_user_ids,
            per_page=per_page,
        )
        return response.get("data", {})

    async def query_sponsor_response(
        self, page: int = 1, sponsor_user_ids: str = "", per_page: int = 20
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "page": page,
            "user_id": sponsor_user_ids,
            "per_page": per_page,
        }
        response = await self._post("/query-sponsor", params)
        logger.info(
            f"[Afdian] Query sponsor ({sponsor_user_ids}) response: {response}"
        )
        return response

    def generate_payment_url(self, price: float, remark: str):
        price_str = f"{round(price, 2):.2f}"
        url = (
            f"{self.order_base_url}?"
            f"user_id={self.user_id}"
            f"&remark={remark}"
            f"&custom_price={price_str}"
        )
        logger.debug(f"Generated payment url: {url}")
        return url
