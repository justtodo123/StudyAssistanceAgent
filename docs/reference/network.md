# 计算机网络 — 外部资料登记

- **外部路径**：`D:\111_Others_Subjects\ComputingNet`
- **知识库入口**：[knowledge/network/README.md](../../knowledge/network/README.md)（31 篇，408 全章节覆盖）
- **整理状态**：📝 笔记已建

## 资料构成

| 类别 | 数量级 | 说明 |
| --- | --- | --- |
| 课件 | PPT 压缩包 | PPT.zip |
| 实验 | winpcap/NPCAP | 网络实验指导 doc、个人实验整理 |
| 复习/练习 | doc | 复习文档、练习1 |

## 顶层文件速览

```
PPT.zip
U202317272_李江华_软件2302.docx
winpcap（NPCAP）计算机网络实验.doc
关于计算机网络实验的说明（winpcap（NPCAP））.doc
复习文档.doc
练习1.doc
```

## 可精炼的候选知识点

- [ ] 物理层/数据链路层：封装、差错检测（CRC）
- [ ] 网络层：IP、子网划分、路由（RIP/OSPF）
- [ ] 传输层：TCP 三次握手、拥塞控制、UDP
- [ ] 应用层：DNS/HTTP/FTP
- [ ] winpcap 抓包实验要点

## 整理记录

| 日期 | 动作 | 对应知识库文件 |
| --- | --- | --- |
| 2026-08-10 | 初始化登记 | — |
| 2026-08-20 | 网络爬取 + LLM 精炼，31 篇条目进入知识库目录 | knowledge/network/ 全部 31 个文件 |
| 2026-08-31 | 建立逐文档治理登记；因原始 URL 与许可证证据缺失，全部降为 candidate | docs/reference/document-mapping.json |

## 文档级治理结论

课程级索引和外部目录不能证明 31 篇网络条目各自的原始来源。当前没有足够证据为任一条目填写可核验
`canonical_url`，也不能把“网络爬取 + LLM 精炼”改称项目原创。因此
[`document-mapping.json`](document-mapping.json) 将 31 篇统一登记为：

- `provenance: web_derived_ai_assisted`；
- `project_authored: false`；
- `review_status: review`；
- `ingest_status: candidate`；
- `license_status: unresolved`。

该结论是 fail-closed 的待解决状态，不表示已满足“原始 URL 或项目原创”门禁。逐篇补齐来源和许可证并完成人工审核前，
这些条目不得视为生产批准；外部原始资料仍只作只读索引，不复制进仓库。
