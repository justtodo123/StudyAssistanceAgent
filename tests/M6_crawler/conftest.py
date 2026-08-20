"""M6 爬虫测试 conftest — 爬虫模块 fixtures。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "tools"

# 确保 tools/ 可 import
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture
def sample_html() -> str:
    """示例 HTML 页面（模拟博客文章）。"""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>TCP三次握手详解 - CSDN博客</title></head>
    <body>
    <nav>导航栏</nav>
    <article>
        <h1>TCP三次握手详解</h1>
        <p>TCP（Transmission Control Protocol）是一种面向连接的、可靠的、基于字节流的传输层通信协议。</p>
        <p>TCP三次握手的过程如下：</p>
        <h2>第一次握手</h2>
        <p>客户端发送一个SYN报文段到服务器，等待服务器确认。SYN=1，seq=x。</p>
        <h2>第二次握手</h2>
        <p>服务器收到SYN报文段后，发送SYN+ACK报文段。SYN=1，ACK=1，seq=y，ack=x+1。</p>
        <h2>第三次握手</h2>
        <p>客户端收到SYN+ACK后，发送ACK报文段。ACK=1，seq=x+1，ack=y+1。</p>
        <h2>为什么是三次而不是两次</h2>
        <p>两次握手无法防止已失效的连接请求报文到达服务器，导致服务器错误建立连接。</p>
    </article>
    <footer>页脚信息</footer>
    <script>console.log("test");</script>
    </body>
    </html>
    """


@pytest.fixture
def sample_text() -> str:
    """示例清洗后文本。"""
    return """TCP三次握手详解

TCP（Transmission Control Protocol）是一种面向连接的、可靠的、基于字节流的传输层通信协议。

TCP三次握手的过程如下：

第一次握手
客户端发送一个SYN报文段到服务器，等待服务器确认。SYN=1，seq=x。

第二次握手
服务器收到SYN报文段后，发送SYN+ACK报文段。SYN=1，ACK=1，seq=y，ack=x+1。

第三次握手
客户端收到SYN+ACK后，发送ACK报文段。ACK=1，seq=x+1，ack=y+1。

为什么是三次而不是两次
两次握手无法防止已失效的连接请求报文到达服务器，导致服务器错误建立连接。"""


@pytest.fixture
def sample_url_entries() -> list[dict]:
    """示例 URL 列表条目。"""
    return [
        {
            "url": "https://example.com/tcp-handshake",
            "topic": "TCP三次握手详解",
            "course": "network",
            "tags": ["TCP", "三次握手"],
            "difficulty": "中等",
        },
        {
            "url": "https://example.com/tcp-handshake-2",
            "topic": "TCP三次握手",  # 与上面标题相似
            "course": "network",
            "tags": ["TCP"],
            "difficulty": "中等",
        },
    ]
