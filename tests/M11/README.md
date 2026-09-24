# M11 测试

本目录验证 M11 真实数据规模化的离线治理合同。

- 默认使用 `tmp_path`，不访问网络、不使用凭据、不触碰学习状态库。
- 真实下载用例必须带 `online` marker 并默认跳过，不能进入 blocking CI。
- 3K Gate 的绝对阈值和人工签署不由本目录自动推断或代签。
- `test_candidate_pipeline.py` 驱动 `platform/app/m11_candidate_pipeline.py`：只把本地、evidence 匹配、白名单内的输入规范化为 candidate；不写 approved、不切 generation、不触碰学习状态库。重跑同一 candidate 保持 source/document identity；空文档、digest mismatch、非白名单和 parser 失败只进 rejected。公开入口 `normalize_bound_candidate()` 必须命中冻结 evidence：MIT OCW、RFC、IANA 使用 SHA-256 manifest，OpenDSA 使用 pinned path manifest 的 Git blob SHA-1。测试同时覆盖恶意 source/asset identifier 不得逃出 rejected 根目录或泄露原值、unbound helper 不得公开导出、manifest asset/path 唯一性与 source allowlist 一致性。RFC TXT、IANA CSV、OpenDSA RST 走 txt parser；PDF/TXT 在 parser 不可用时稳定码 `SOURCE_PARSER_UNAVAILABLE` fail-closed，可用时产出 candidate。结果路径只返回相对 artifact 名。`parser_status_for_candidates()` 报告 md/txt/pdf 可用性，集合必须非空。
