# 入库收件箱（不检索）

本目录只接收待审核候选，**不会进入检索索引**。

- crawler 默认输出仍在 `platform/.cache/crawler-candidates/`
- 若需暂存到仓库内，只能放这里，且 frontmatter 保持 `source_type: web_candidate`、`ingest_status: candidate`
- 审核通过后，精炼成课程笔记，改为 `source_type: web_reviewed`、`ingest_status: approved`，再移到 `knowledge/{course}/`
- 不要把 AI 生成草稿直接放到课程目录

规则见 [knowledge/README.md](../README.md)。
