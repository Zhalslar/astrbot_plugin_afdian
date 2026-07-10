
<div align="center">

![:name](https://count.getloli.com/@astrbot_plugin_afdian?name=astrbot_plugin_afdian&theme=minecraft&padding=6&offset=0&align=top&scale=1&pixelated=1&darkmode=auto)

# astrbot_plugin_afdian

_✨ 爱发电插件 ✨_  

[![License](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0.html)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![AstrBot](https://img.shields.io/badge/AstrBot-4.0%2B-orange.svg)](https://github.com/Soulter/AstrBot)
[![GitHub](https://img.shields.io/badge/作者-Zhalslar-blue)](https://github.com/Zhalslar)

</div>

## 🤝 介绍

对接爱发电平台，接受用户打赏，实时推送订单情况

## 📦 安装

在astrbot的插件市场搜索astrbot_plugin_afdian，点击安装

## ⌨️ 使用说明

### Webhook 配置

本插件会单独启动一个爱发电 Webhook 服务，默认监听 `0.0.0.0:6500`。

要接收订单通知，请确保爱发电服务器能从公网访问你的回调地址：

1. 在插件配置中设置 `webhook.host` 和 `webhook.port`，一般保持 `host=0.0.0.0`，按需修改 `port`。
2. 在服务器防火墙、安全组、路由器中放行该端口，例如默认的 `6500`。
3. 在爱发电开发者设置中填写回调地址，例如 `http://你的公网IP:6500/` 或 `https://你的域名/afdian/`。
4. 如果没有公网 IP 或不想直接开放端口，请先配置反向代理、内网穿透、frp、ngrok、cloudflared 等工具，把公网地址转发到插件监听端口。

不要填写 `localhost`、`127.0.0.1` 或内网 IP 作为爱发电回调地址，否则爱发电无法访问，订单通知会失败。没有可公网访问的 Webhook 时，查询订单等主动 API 功能仍可用，但实时订单通知和赞助成功自动回复不可用。

### 命令表

| 命令 | 说明 |
|:--:|:--|
| `发电 [金额]` | 向创作者发电, 别名：`赞助` |
| `爱发电通知` | 开启当前会话的爱发电订单通知（仅管理员可用） |
| `爱发电测试` | 手动触发一次测试通知，测试通知功能是否正常（仅管理员可用） |
| `查询订单 <订单号>` | 查询指定订单的详情信息（仅管理员可用） |
| `查询发电` | 查询默认账号收到的赞助记录（仅管理员可用）。别名：`查询赞助`仅管理员可用） |

### 示例图

## 👥 贡献指南

- 🌟 Star 这个项目！（点右上角的星星，感谢支持！）
- 🐛 提交 Issue 报告问题
- 💡 提出新功能建议
- 🔧 提交 Pull Request 改进代码

## 📌 注意事项

- 想第一时间得到反馈的可以来作者的插件反馈群（QQ群）：460973561
