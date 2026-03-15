# astrbot_plugin_afdian

AstrBot 爱发电插件，支持：

- 生成爱发电支付链接
- 接收 webhook 订单通知
- 将 webhook 的完整 JSON 内容渲染成图片发送到会话
- API 查询结果按完整返回结构展示
- 可选把收到的原始 webhook JSON 转发到另一台服务器
- 支持自定义爱发电根域名，兼容平台换域名

## 安装

```bash
cd /AstrBot/data/plugins
git clone https://github.com/Zhalslar/astrbot_plugin_afdian
```

重启 AstrBot 后完成加载。

## 命令

- `发电 [金额]`
- `赞助 [金额]`
- `查询订单 <订单号>`
- `查询发电`
- `查询赞助`

## 配置

### 基础配置

```json
{
  "api_config": {
    "user_id": "你的 user_id",
    "token": "你的 token",
    "base_url": "https://ifdian.net"
  },
  "webhook_config": {
    "host": "0.0.0.0",
    "port": 6500
  }
}
```

### 启用完整 webhook 转发

```json
{
  "webhook_config": {
    "host": "0.0.0.0",
    "port": 6500,
    "forward": {
      "enabled": true,
      "url": "https://example.com/webhook",
      "timeout": 10,
      "authorization": ""
    }
  }
}
```

说明：

- 会话通知图片展示的是收到的完整 webhook payload。
- `查询订单` 和 `查询发电/查询赞助` 展示的是 API 原始返回结构，不再只显示摘要字段。
- `api_config.base_url` 是爱发电根地址，默认是 `https://ifdian.net`，修改后会同时影响 API 请求地址和支付链接地址。
- 转发功能为可选配置，开启后会把收到的原始 JSON body 原样 `POST` 到目标地址。
- 如果转发失败，只会记录日志，不会影响当前 webhook 对爱发电返回成功响应。
