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
- `m11-p0-acquisition-26-authority-v1.json` 是独立的 26 资产 `acquisition` authority；它与 HUMAN_REVIEW authority 共享冻结 scope digest，但不能互相复用或替代。未来 Formal Gate 0 必须另持 `operation=gate0` authority，并显式提供本 acquisition authority 来验证 receipts；共享 scope digest 不使三种 authority 可互换。IANA CSV/XML/TXT 通过 resolver 的 registry name + format 规则绑定到三项冻结 asset。
- `m11-p0-acquisition-26-receipts-v1.json` 是 26 条 `ACQUIRED` receipt 的无正文 wrapper；raw bodies 与逐 asset reports 保留在 gitignored 层，不进入 Git，也不构成 publication。
- `m11-p0-human-review-acq-defer-26-v1.json` 是获取后的 26 项再核验切片：全部 `DEFER`，逐条 `supersedes` 历史 review；ACQUIRED receipts 与 DEFER reviews 仍不足以执行 Formal Gate 0。
- `m11-p0-evidence-closure-26-v1.json` 是严格 metadata-only 的 26 项八类证据闭环投影：所有 substantive evidence 保持 `PENDING`，结果为 `REVIEW_REQUIRED`，不执行 Formal Gate 0，也不产生晋升或 publication 授权。
- `m11-p0-human-review-closure-defer-26-v1.json` 是对应的最终 superseding review slice：26 条记录仍为 `DEFER`，逐条引用 closure matrix 并 supersede 获取后再核验记录；不创建 document/chunk。
- `m11-p0-official-source-observations-26-v1.json` 是 append-only、metadata-only 的官方来源观察层：记录 robots digest match、政策元数据、RFC 日期和 IANA XML 日期冲突；不把 source-level observation 当作八类资产级证据闭合，closure 仍全为 `PENDING`，IANA 冲突保持 `UNRESOLVED`。
- `m11-p0-human-review-official-observation-defer-26-v1.json` 是观察后的 successor review slice：26 条仍为 `DEFER`，逐条 supersede closure slice，不创建 document/chunk；观察层和该 slice 均不授权 Gate 0、晋升、publication、来源扩张或新的网络获取。
- `m11-p0-rfc-iana-evidence-review-application-v1.json` 是 2026-09-27 RFC 9110/9293/1034 与 IANA CSV/XML/TXT exact-six evidence review 的非执行申请；版本化 batch digest 绑定父 scope 与六项 candidate/receipt/revision identity，申请本身不产生 authority。
- `m11-p0-rfc-iana-evidence-review-authority-v1.json` 是该 exact-six 批次的专用 `human_review` authority：仍绑定冻结的 26 项父 scope digest，但 source/asset 集合精确等于六项；不授权 Gate 0、晋升或 publication。
- `m11-p0-rfc-iana-evidence-review-result-v1.json` 记录六项核验结果：48 个 evidence cell 全部保持 `PENDING`，结果为 `REVIEW_REQUIRED`、closure effect 为 `NONE`，IANA XML 冲突保持 `UNRESOLVED`，IANA TXT parser 保持 `FAIL_CLOSED`。
- `m11-p0-rfc-candidate-materialization-v1.json` 记录 2026-09-28 在冻结 CPython 3.11.9 parser 环境下重放 RFC 1034/9110/9293 的 metadata-only checkpoint：3 个 current-schema candidate artifacts、3 个 candidate chunks、0 rejected；approved documents/chunks 仍为 0，`counts_toward_3k=false`，不执行 Gate 0，也不授权 promotion 或 publication。
- `m11-p0-rfc-content-quality-sampling-v1.json` 是 metadata-only content-quality sampling checkpoint：exact-three candidate census（3 chunks），只记录结构、digest、validator、parser environment 和 false-escalation flags；`content_quality` 仍为 3 个 `PENDING`，不读取正文入 tracked artifacts，不创建 authority，不执行 Gate 0。
- `m11-p0-rfc-content-quality-sampling-result-v1.json` 是 local body census 后生成的 privacy-safe technical result：3 个 candidate bodies 均非空、identity/digest/schema/structure checks 全部通过，`technical_sampling_status=VERIFIED`；只保存 bounded counts/digests，不保存正文。
- `m11-p0-rfc-content-quality-review-authority-v1.json` 与对应 result 记录 owner 选择「全部 VERIFIED」：三个 RFC 的 `content_quality` cells 改为 `VERIFIED`；累积状态为 12 `VERIFIED` + 3 `NOT_APPLICABLE` + 9 `PENDING`，剩余仅 license/robots_terms/notice_ipr，不写 successor、不执行 Gate 0、不晋升或发布。
- `m11-p0-rfc-legal-policy-census-v1.json` 是 exact-three offline notice/robots census：RFC 9110/9293 分类为 modern IETF Trust/BCP78 family，RFC 1034 分类为 pre-Trust unlimited-distribution family；只保存 booleans/year/digest/policy，不保存正文。
- `m11-p0-rfc-legal-policy-review-authority-v1.json` 与对应 result 记录 owner 选择「全部 9 项 VERIFIED」：三个 RFC 的 license/robots_terms/notice_ipr 全部闭合；累积为 21 `VERIFIED` + 3 `NOT_APPLICABLE` + 0 `PENDING`。evidence complete 但当时不写 successor、不执行 Gate 0、不晋升或发布。
- `m11-p0-rfc-exact-three-accept-authority-v1.json`、`m11-p0-rfc-exact-three-accept-result-v1.json` 与 `m11-p0-human-review-rfc-exact-three-accept-3-v1.json` 记录后续独立 owner decision：RFC 三个 current heads 均为 `ACCEPT_FOR_PROMOTION_REVIEW`，IANA/MIT heads 仍 `DEFER`；不执行 Gate 0、不授权 promotion/publication。
- `m11-p0-rfc-evidence-closure-packet-draft-v1.json` 是非执行 RFC exact-three review packet：绑定 refreshed candidates 和新 batch digest，但 `authority_issued=false`，24 个 evidence cells 全部 `PENDING`，不产生 owner authority、Gate 0、晋升或 publication。
- `m11-p0-rfc-schema-review-authority-v1.json` 与 `m11-p0-rfc-schema-review-result-v1.json` 记录 owner 于 2026-09-28 选择「仅批准 schema N/A」：exact-three `human_review` authority 只覆盖 RFC 1034/9110/9293，三项 `schema` cells 改为 `NOT_APPLICABLE`，其余 21 cells 当时保持 `PENDING`；`closure_effect=PARTIAL`，不写 successor，不执行 Gate 0、不晋升或发布。
- `m11-p0-rfc-technical-evidence-review-authority-v1.json` 与对应 result 记录后续 owner 选择「批准 9 个 VERIFIED」：三个 RFC 的 `revision`、`provenance`、`parser` 共 9 cells 改为 `VERIFIED`；累积状态为 9 `VERIFIED` + 3 `NOT_APPLICABLE` + 12 `PENDING`，不写 successor，不执行 Gate 0、不晋升或发布。
- `m11-p0-human-review-rfc-iana-evidence-defer-6-v1.json` 是 exact-six 结果后的 successor slice：六条仍为 `DEFER`，逐条 supersede 当前 official-observation head，不创建 document/chunk；Gate 0 保持 `BLOCKED` 且 reviewed count 为 0。
- `m11-p0-mit-ocw-evidence-review-application-v1.json` 是 2026-09-27 MIT OCW 20 个冻结 PDF 的 exact-20 非执行申请；版本化 batch digest 绑定父 scope 与 20 项 candidate/receipt/revision identity，范围保留 `digital_answers` 与 `information_worksheet`，不含 RFC、IANA、OpenDSA 或其他来源。
- `m11-p0-mit-ocw-evidence-review-authority-v1.json` 是 exact-20 专用 `human_review` authority：source/asset 集合必须精确等于 MIT 20 项，不授权 Gate 0、晋升、publication 或来源扩张。
- `m11-p0-mit-ocw-evidence-review-result-v1.json` 记录 MIT exact-20 资产级核验结果：160 个 evidence cell 全部保持 `PENDING`，20 项 determination 全为 `DEFER`，`closure_effect=NONE`、third-party rights 为 `UNRESOLVED`；两项 normalization rejection 仅作为 pipeline disposition 原样保留，不自动变为 HUMAN_REVIEW `REJECT`。
- `m11-p0-mit-ocw-candidate-materialization-v1.json` 是 2026-09-28 的 metadata-only candidate checkpoint：20 项输入中 18 项生成并通过当前 candidate artifact validator，共 93 个 candidate chunks；`digital_answers` / `information_worksheet` 分别因 `SOURCE_PARSE_FAILED` / `INVALID_CANDIDATE_INPUT` 保持 rejected。该记录明确 approved documents/chunks 均为 0，不计入 3K，不执行 Gate 0，也不授权 promotion 或 publication。
- `m11-p0-human-review-mit-ocw-evidence-defer-20-v1.json` 是 exact-20 结果后的 successor slice：20 条仍为 `DEFER`，逐条 supersede 对应 MIT official-observation head，不创建 document/chunk，也不改写 RFC/IANA 六个 current head；Gate 0 保持 `BLOCKED` 且 reviewed count 为 0。
- `platform/app/m11_candidate_pipeline.py` 是编排层：复用 M7 parser/normalized identity，只物化 candidate/rejected 证据，禁止 publication 和 approved 晋升。公开入口仅有 `normalize_bound_candidate()`：MIT OCW、RFC 与 IANA 必须命中 `m11-p0-digest-evidence-v1.json` 的 SHA-256，OpenDSA 必须命中 pinned path manifest 并按 Git blob SHA-1 验证本地 bytes；无 evidence 绑定的规范化仅保留为私有 hermetic helper。当前 CPython 3.13.3 上 TXT parser 按 M7 合同不可用，RFC/IANA/OpenDSA 文本路径 fail-closed；Markdown 仍可规范化。
- 2026-09-24 受控 metadata 获取先执行 HEAD，26/26 asset 与 3/3 robots 入口可达；receipt 位于 gitignored 的 `artifacts/m11-controlled-metadata-acquisition-v1.json`。
- 随后按小批次临时获取 bytes 并立即删除：MIT OCW 20/20 PDF、RFC 3/3 TXT、IANA 3/3 格式均取得 SHA-256；IANA 三格式 schema 探针通过，PDF 魔数通过。receipts 均位于 gitignored 的 `artifacts/`。这只关闭 revision/digest 证据，不自动关闭 license、robots、notice/IPR 或 publication。

M11 v1.1 的 P0 inventory 先以 `sources/m11-p0-inventory.yaml` 记录 Gate 0 待核验项；当前已记录官方入口与 provisional license basis，
但仍为 `REVIEW_REQUIRED`。在逐 asset 的官方许可、revision 和 robots 核验完成前，来源不得进入 approved；已捕获的 digest 证据不等于资产批准。除已登记的受控 metadata 获取外，任何进一步真实下载仍需单独确认。
