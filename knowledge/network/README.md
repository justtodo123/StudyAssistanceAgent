# 计算机网络 · 知识库导航

> 408 考研四门核心课之一。覆盖物理层→应用层全部考点。

## 课程简介

计算机网络是研究计算机互联的学科，核心内容包括网络体系结构、各层协议原理、网络安全等。
408 考试重点：TCP/IP 协议栈、IP 地址与子网划分、TCP 连接管理与拥塞控制、应用层协议。

## 章节地图

### 第 1 章：概述与体系结构
| 条目 | 文件 | 难度 | 核心考点 |
|---|---|---|---|
| 计算机网络概述 | [overview.md](overview.md) | 入门 | 网络定义、分类、发展阶段 |
| OSI 与 TCP/IP 体系结构 | [architecture.md](architecture.md) | 入门 | 七层模型、四层模型、协议数据单元 |
| 网络性能指标 | [performance.md](performance.md) | 中等 | 时延、带宽、吞吐量、信道利用率 |

### 第 2 章：物理层
| 条目 | 文件 | 难度 | 核心考点 |
|---|---|---|---|
| 物理层基础 | [physical-layer.md](physical-layer.md) | 入门 | 物理层功能、传输介质、接口特性 |
| 数据编码方式 | [encoding.md](encoding.md) | 中等 | NRZ、曼彻斯特编码、差分曼彻斯特 |
| 信道容量 | [channel-capacity.md](channel-capacity.md) | 中等 | 奈奎斯特定理、香农定理、信道复用 |

### 第 3 章：数据链路层
| 条目 | 文件 | 难度 | 核心考点 |
|---|---|---|---|
| 数据链路层概述 | [data-link-layer.md](data-link-layer.md) | 入门 | 成帧、透明传输、差错检测 |
| 差错控制与 CRC | [error-control.md](error-control.md) | 中等 | 奇偶校验、CRC 计算、海明码 |
| 流量控制 | [flow-control.md](flow-control.md) | 中等 | 停等协议、GBN、SR、滑动窗口 |
| CSMA/CD 协议 | [csma-cd.md](csma-cd.md) | 中等 | 载波监听、碰撞检测、二进制退避 |
| 以太网与 VLAN | [ethernet.md](ethernet.md) | 中等 | MAC 地址、以太网帧、VLAN 划分、STP |

### 第 4 章：网络层
| 条目 | 文件 | 难度 | 核心考点 |
|---|---|---|---|
| 网络层概述 | [network-layer.md](network-layer.md) | 入门 | 网络层功能、虚电路与数据报 |
| IP 协议与地址 | [ip-protocol.md](ip-protocol.md) | 中等 | IP 数据报格式、分类地址、特殊地址 |
| 子网划分与 CIDR | [subnetting.md](subnetting.md) | 中等 | 子网掩码、CIDR、路由聚合 |
| ARP 与 ICMP | [arp-icmp.md](arp-icmp.md) | 中等 | ARP 工作原理、ICMP 报文类型 |
| 路由算法 | [routing.md](routing.md) | 进阶 | RIP、OSPF、BGP、距离向量与链路状态 |
| NAT 与 IPv6 | [nat.md](nat.md) | 中等 | NAT 原理、IPv6 地址格式、过渡技术 |

### 第 5 章：传输层
| 条目 | 文件 | 难度 | 核心考点 |
|---|---|---|---|
| 传输层概述 | [transport-layer.md](transport-layer.md) | 入门 | 传输层功能、端口号、复用与分用 |
| TCP 连接管理 | [tcp-connection.md](tcp-connection.md) | 中等 | 三次握手、四次挥手、SYN 洪泛 |
| TCP 可靠传输 | [tcp-reliable.md](tcp-reliable.md) | 中等 | 序号、确认、超时重传、滑动窗口 |
| TCP 拥塞控制 | [tcp-congestion.md](tcp-congestion.md) | 进阶 | 慢启动、AIMD、快重传、快恢复 |
| UDP 协议 | [udp.md](udp.md) | 入门 | UDP 特点、校验和、应用场景 |

### 第 6 章：应用层
| 条目 | 文件 | 难度 | 核心考点 |
|---|---|---|---|
| 应用层概述 | [application-layer.md](application-layer.md) | 入门 | C/S 与 P2P 模型、应用层协议分类 |
| DNS 域名系统 | [dns.md](dns.md) | 中等 | 域名结构、递归/迭代查询、DNS 缓存 |
| HTTP/HTTPS 协议 | [http.md](http.md) | 中等 | 请求/响应格式、持久连接、HTTPS 握手 |
| FTP 与 SMTP | [ftp-smtp.md](ftp-smtp.md) | 中等 | FTP 工作模式、SMTP/POP3/IMAP |
| Socket 编程 | [socket.md](socket.md) | 中等 | Socket API、TCP/UDP 编程模型 |

### 第 7 章：网络安全
| 条目 | 文件 | 难度 | 核心考点 |
|---|---|---|---|
| 网络安全概述 | [security-overview.md](security-overview.md) | 入门 | 安全威胁、安全服务、攻击类型 |
| 加密与数字签名 | [encryption.md](encryption.md) | 中等 | 对称/非对称加密、RSA、数字签名 |
| 防火墙与 VPN | [firewall-vpn.md](firewall-vpn.md) | 中等 | 包过滤、状态检测、IPSec VPN |

### 第 8 章：真题复盘
| 条目 | 文件 | 难度 | 核心考点 |
|---|---|---|---|
| 408 网络真题复盘 | [exam-review.md](exam-review.md) | 进阶 | 历年高频题型、解题思路、易错点 |

## 重点 / 难点

**高频考点（必掌握）**：
- TCP 三次握手 / 四次挥手（连接管理）
- TCP 拥塞控制四阶段
- IP 地址分类、子网划分、CIDR
- CRC 差错检测计算
- CSMA/CD 工作原理
- DNS 查询过程
- HTTP 请求/响应格式

**易混淆概念**：
- 流量控制 vs 拥塞控制
- 停等协议 vs GBN vs SR
- RIP vs OSPF vs BGP
- TCP vs UDP

## 外部资料指针

参考原始资料索引：`docs/reference/network.md`
