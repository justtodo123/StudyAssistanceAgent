# data/manifests/

本目录只保存可入 Git 的来源元数据、许可核验结果、revision、digest 和审核状态，不保存正文。

- `sources/m11-p0-candidate-assets-v1.json`：四类 P0 来源的 candidate asset 清单；owner 于 2026-09-24 批准其进入 candidate pipeline，但当前仍不含 approved asset。
- 每个外部 asset 必须同时通过 license、revision、robots 和（适用时）notice/IPR/schema 审查；任一字段为 `pending` 或 digest 缺失时，保持 `approved: false`。
- `data/manifests/m11-p0-digest-evidence-v1.json` 是可提交的 26 项 digest 汇总；`artifacts/` 下的逐批 receipt 仅为本机审计留痕。
- `sources/m11-opendsa-rst-paths-v1.json` 固定 pinned commit 的 861 个 RST 路径与 blob SHA；已获 candidate pipeline 授权，但不是内容批准。candidate asset 清单中的 `rst_en_blobs: 865` 只是更宽的树统计；多出的 4 个 blob 不在显式 path manifest 中，不能执行、计数或静默扩入 candidate scope。
- `m11-p0-asset-review-v1.json` 是 `REVIEW_REQUIRED` 的 metadata-only review manifest，覆盖 887 条冻结 P0 记录；approved asset/document/chunk 均为 0，formal run 与 publication 均未授权。
- `m11-p0-human-review-26-authority-v1.json` 是 2026-09-26 的 26 资产 `human_review` 执行 authority：MIT OCW 20 PDF + RFC 3 + IANA 3，含两份已 `REJECTED` 的 MIT OCW PDF，不含 OpenDSA。它授权人工核验准备，不授权 Formal Gate 0、晋升或 publication。
- `m11-p0-human-review-rfc-iana-6-v1.json` 是 2026-09-26 的 RFC 3 + IANA 3 `DEFER` 切片：无 candidate 文档/chunks，无 ACQUIRED receipt。
- `m11-p0-human-review-mit-ocw-20-v1.json` 是 2026-09-26 的 MIT OCW 20 `DEFER` 切片：无 committed candidate 文档/chunks，无 ACQUIRED receipt；含两份已 REJECTED 的 PDF。至此 26 项决策均已写入且全部为 `DEFER`。`DEFER` 不关闭 887 条 review 字段，不执行 Formal Gate 0。
- `platform/app/m11_candidate_pipeline.py` 是编排层：复用 M7 parser/normalized identity，只物化 candidate/rejected 证据，禁止 publication 和 approved 晋升。公开入口仅有 `normalize_bound_candidate()`：MIT OCW、RFC 与 IANA 必须命中 `m11-p0-digest-evidence-v1.json` 的 SHA-256，OpenDSA 必须命中 pinned path manifest 并按 Git blob SHA-1 验证本地 bytes；无 evidence 绑定的规范化仅保留为私有 hermetic helper。当前 CPython 3.13.3 上 TXT parser 按 M7 合同不可用，RFC/IANA/OpenDSA 文本路径 fail-closed；Markdown 仍可规范化。
- 2026-09-24 受控 metadata 获取先执行 HEAD，26/26 asset 与 3/3 robots 入口可达；receipt 位于 gitignored 的 `artifacts/m11-controlled-metadata-acquisition-v1.json`。
- 随后按小批次临时获取 bytes 并立即删除：MIT OCW 20/20 PDF、RFC 3/3 TXT、IANA 3/3 格式均取得 SHA-256；IANA 三格式 schema 探针通过，PDF 魔数通过。receipts 均位于 gitignored 的 `artifacts/`。这只关闭 revision/digest 证据，不自动关闭 license、robots、notice/IPR 或 publication。

M11 v1.1 的 P0 inventory 先以 `sources/m11-p0-inventory.yaml` 记录 Gate 0 待核验项；当前已记录官方入口与 provisional license basis，
但仍为 `REVIEW_REQUIRED`。在逐 asset 的官方许可、revision 和 robots 核验完成前，来源不得进入 approved；已捕获的 digest 证据不等于资产批准。除已登记的受控 metadata 获取外，任何进一步真实下载仍需单独确认。