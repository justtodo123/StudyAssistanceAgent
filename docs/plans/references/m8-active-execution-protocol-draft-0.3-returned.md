# M8 active execution protocol 草案

> 文档性质：规范性 protocol blob；本文件不记录当前授权、审查结论、实验身份或阶段状态。
> 文档版本：`draft-0.3`（仅为文档修订号，不是 experiment ID 或 executable protocol ID）。
> 起草日期：2026-09-11。本文所有摘要均由外部记录保存，本文不自哈希。
> 政策依据：[`m8-decision-closure-v1.md`](m8-decision-closure-v1.md)。
> 路线图权威：[`docs/PLAN.md`](../../PLAN.md)。

## 1. 范围、零授权与术语

本文定义 M8 specialized storage 的技术审查口径、输入/输出 schema、生命周期和证据规则。
`protocol_blob_sha256` 是本文件完整 canonical bytes 的 SHA-256；文件名、metadata 和外部记录不进入该摘要。
任一字节变化都会使绑定旧摘要的 P0 记录失效，并要求新修订和重新审查。

本文不承载 P0–P9/P7A 的当前事实，不复用 V1–V13 的 identity、binding、root、source、artifact、report 或结果。
reviewer、approver、timestamp、decision、experiment identity、repository binding 和动态状态只能存在于外部、
按本协议校验且绑定 `protocol_blob_sha256` 的记录中。历史 returned 文件只能追溯，不得 binding 或授权。

本文自身不授权创建 identity/binding/root，获取或安装依赖，生成 source/corpus/query/gold，运行 preflight 或
benchmark，发布证据，改变 M8 registry，准入 M8，选择后端或生产开工。P0 只接受技术文字；即使 P0 接受，
P1–P9/P7A 仍须另行形成满足前置关系的外部记录。

本协议中的 `artifact` 是一个完整 canonical JSON 文档。`artifact digest` 永远是该文档完整字节的 SHA-256，
由引用它的外部记录或 manifest 保存；artifact 不含自己的 digest 字段。禁止 self-hash、置空字段重算、digest
alias 和循环引用。

## 2. Canonical bytes 与类型系统

### 2.1 `sa-json-c14n-v1`

所有 machine artifact、gate record 和 package member 均按以下步骤产生唯一字节：

1. 文档是 UTF-8，无 BOM，使用 LF，且恰有一个末尾 LF；不做 Unicode normalization。
2. JSON 文本只允许 RFC 8259 的 object、array、string、boolean、null 和 number 语法；本协议 schema 禁止 null。
3. 解析器必须拒绝 duplicate object key、lone surrogate、NaN、Infinity、`-Infinity` 和 negative zero。
4. 重序列化不输出任何空白；object key 按 Unicode code point ordinal 升序比较；数组不排序，按其 schema 的
   comparator 顺序写出。
5. 字符串使用 UTF-8 scalar；`U+0000..U+001F` 统一写为小写 `\u00xx`，反斜杠写 `\\`，引号写 `\"`，其余
   Unicode scalar 直接写出。禁止 `\/`、大写 hex、短转义 `\b\f\n\r\t` 和非必要 `\u` 转义。
6. number 只允许 JSON integer；使用任意精度十进制解析，重序列化为无前导零的 ASCII 十进制整数；`-0` 拒绝。
   本协议所有计数和纳秒量均在实现语言中按任意精度解析后再检查边界，不得先转 IEEE-754 double。
7. 每个 reader 必须执行 strict parse、closed-schema/语义校验、canonical reserialization、逐字节 equality 和
   外部 SHA-256 校验；任何一步失败即 fail closed。
8. JSONL 每行是一个 canonical object，行内不含 LF；每行以一个 LF 结束（因此 N 行恰有 N 个行尾 LF），文件不得有额外空行，并按 schema 的唯一 key 排序。JSONL 的外部 commitment 使用该完整字节序列；它不是本节 envelope artifact，不能用 `REF` 伪装为 envelope 引用。

### 2.2 原子类型

- `BOOL`：JSON boolean。
- `INT[n,m]`：闭区间任意精度 JSON integer。
- `ASCII[n,m]`：U+0020–U+007E，长度按 code point 计算。
- `UTF8[n,m]`：Unicode scalar 长度按 code point 计算，不含 lone surrogate。
- `ID`：ASCII[1,128]，匹配 `[a-z0-9][a-z0-9-]{0,127}`。
- `SCHEMA_ID`：ASCII[1,128]，匹配 `[a-z0-9][a-z0-9.-]{0,127}`，且不得连续 `..`、以 `.` 结尾。
- `CODE`：ASCII[1,96]，匹配 `[A-Z][A-Z0-9_:-]{0,95}`。
- `HEX16`/`HEX32`/`HEX64`：分别为 16/32/64 个小写十六进制字符。
- `GIT_OID`：40 或 64 个小写十六进制字符；记录 `oid_algorithm` 为 `sha1` 或 `sha256`。
- `DEC`：有限十进制字符串 `-?(0|[1-9][0-9]*)(\.[0-9]{1,9})?`，范围 `[-10^18,10^18]`，禁止 `-0`。`canonical_dec(x)` 是唯一用于 digest、ID、equation operand 和比较序列化的表示：先以任意精度计算，再 half-even 舍入到恰好九位小数，补足尾零，删除负号前的零值，且整数部分不带前导零；例如 `1` canonicalize 为 `1.000000000`，`1.2` 与 `1.20` canonicalize 为 `1.200000000`，零为 `0.000000000`。
- `TS`：`YYYY-MM-DDTHH:MM:SSZ`，按 Gregorian UTC 校验日期，禁止闰秒，固定秒精度。
- `REPO_PATH`：1–240 个字符的 repository-relative POSIX path；禁止 `\\`、空 segment、`.`、`..`、绝对路径、drive 和 UNC。
- `TARGET_COMPONENT`：1–255 个 UTF-8 scalar 的单一 filename component；禁止 `/`、`\\`、`.`、`..`、NUL、ADS 分隔符和
  reparse syntax。它只在 verified parent handle 下使用，不是绝对路径。
- `LOGICAL_NAME`：1–240 个 ASCII 小写字符、数字、`.`、`/`、`-`、`_`，首尾不得为 `/`，不得出现 `//` 或值为
  `.`/`..` 的 path segment。
- `HTTPS_URL`：`https://` URL，长度 9–2048；无 userinfo、fragment 和 query；host 1–253，ASCII lower-case DNS 或
  bracketed IPv6，禁止 IDN、默认端口和尾部空白。
- `WORKLOAD`：`1k-correctness`、`10k-single-user`、`100k-capacity`、`100k-filtered`。
- `BACKEND`：`sqlite-linear-exact`、`lancedb-embedded-exact`。
- `GATE`：`P0`、`P1`、`P2`、`P3`、`P4`、`P5`、`P6`、`P7`、`P7A`、`P8`、`P9`；仅用于 external authorization record。
- `TECH_GATE_ID`：`identity-count`、`metadata-filter-gold`、`fault-lifecycle`、`reopen-parity`、`exact-top-k`、`recall-at-1`、`recall-at-3`、`recall-at-5`、`mrr`、`no-hit-precision`、`unfiltered-p95`、`unfiltered-p99`、`filtered-p95`、`filtered-p99`、`build-p95`、`rebuild-p95`、`repetition-ratio`、`rss-cap`、`disk-cap`、`network-zero`、`listener-zero`、`service-process-zero`、`production-write-zero`、`residual-zero`、`sqlite-ratio`、`adoption`。
- `QUERY_ROLE`：`measured-hit`、`measured-filtered-hit`、`measured-deny-owner`、`measured-deny-source`、`warmup`。
- `QUERY_KIND`：`hit`、`filtered-hit`、`deny-owner`、`deny-source`、`warmup`。
- `QUERY_CLASS`：`unfiltered`、`filtered`、`deny`。
- `LIFECYCLE_OPERATION`：`incremental-upsert`、`replace`、`tombstone`、`hard-delete`、`reopen`、`rebuild`、`rollback-after-failed-candidate`。
- `FAULT_FIXTURE_ID`：the sixteen IDs listed in §8, each matching exactly one registry entry.
- `FAULT_INJECTION_POINT`：`input-owner-metadata`、`input-source-metadata`、`input-generation-metadata`、`input-snapshot-metadata`、`input-vector-dimension`、`input-vector-profile`、`candidate-tombstone`、`candidate-hard-delete`、`candidate-partial-build`、`manifest-read`、`index-read`、`build-worker`、`publish-worker`、`cutover-worker`、`dependency-acquisition`、`network-egress`。
- `OBS_PHASE`：`warmup`、`measured`。
- `OBS_STATUS`：`completed`、`failed`、`timed-out`、`aborted`、`not-run`。
- `STABLE_CODE`：`CODE` constrained to one of the exact 48 failure/status values in the closed status-map artifact; every source-domain status maps to exactly one stable code for each applicable phase. It never includes `NONE`.
- `RESULT_CODE`：闭合 scalar union `oneOf[STABLE_CODE,literal["NONE"]]`。`NONE` 是唯一非失败 sentinel；只可用于成功，或用于 raw evidence 完整但 performance/adoption predicate 为 false 的非错误阈值结果。failed、timed-out、aborted、not-run、violation 以及 hard/resource predicate false 必须使用 status-map 或 predicate registry 声明的 `STABLE_CODE`。
- `TECH_GATE_OPERAND`：closed discriminated union：`{name:ID,type:"INT",value_int:INT[-1000000000000000000,1000000000000000000]}`、`{name:ID,type:"DEC",value_dec:DEC}`、`{name:ID,type:"BOOL",value_bool:BOOL}` 或 `{name:ID,type:"HEX64",value_hex64:HEX64}`；variant 之外的 value field 禁止出现。
- `TECH_GATE_RESULT`：`{gate_id:TECH_GATE_ID,class:enum[hard,performance,resource,adoption],predicate_id:ID,operands:A<TECH_GATE_OPERAND;1..16;order=key(name);unique=key(name)>,equation:ASCII[1,512],expected:true,actual:BOOL,passed:BOOL,failed_stable_code:RESULT_CODE,evidence_refs:A<REF;1..4096;order=key(logical_name,schema_id,sha256);unique=key(logical_name)>}`。`actual` 是 registry equation 对 typed operands 的唯一求值结果；`passed=actual`。
- `LAYER`：`L0`、`L1`、`L2`、`L3`、`L4`。
- `TARGET_SLOT`：`oneOf[TARGET,literal["not-applicable"]]`；only P7A branch slot arrays use this union. A slot is either the exact reserved TARGET or the single sentinel; no other placeholder is valid.
- `MUTATION_SPEC`：`{mutation_id:FAULT_FIXTURE_ID,encoding:"canonical-json",target_field:ID,original_value:CODE,replacement_value:CODE}`；its canonical bytes are the canonical UTF-8 JSON bytes of this exact object and are never inferred from prose.

所有 object 都是 `additionalProperties=false` 的 closed object。未声明 `optional` 的字段 required、non-null。
`A<T;n..m;order=O;unique=U>` 表示长度闭区间、元素类型 T、顺序规则 O 和唯一性投影 U；空数组只能写 `[]`。

### 2.3 数组顺序与唯一性 DSL

O/U 只允许以下语法，schema validator 必须先验证投影对元素类型有效，再验证数组：

- `order=ordinal`：数组位置就是规范性声明顺序，不重排；只适用于协议另行冻结了逐位置语义的序列。
- `order=value`：原子值按类型全序；整数按数值，BOOL 按 `false < true`，ASCII/ID/CODE/HEX/SCHEMA_ID/
  LOGICAL_NAME 按 UTF-8 bytes，enum 按 schema 声明顺序。object 不得使用 `value`。
- `order=key(f1,...,fn)`：object 按所列 required scalar field 依次比较；每个字段使用其原子类型全序。字段必须存在，
  该 tuple 必须对允许的元素集合形成全序；否则 schema 非法。
- `unique=value`：原子值逐字唯一；object 不得使用。
- `unique=key(f1,...,fn)`：object 的指定 required scalar tuple 唯一；字段必须存在。
- `unique=not-applicable`：不施加元素唯一性约束；仅可与 `order=ordinal` 一起使用。

禁止未注册的说明词（如 `gate`、`path`、`layer`）作为 comparator，禁止 comparator 隐式读取 REF 指向的内容。
若语义要求 gate/layer/workload 的固定顺序，object 必须自带相应 enum 字段并使用 `key(...)`；enum 的 schema
声明顺序就是比较顺序。`order=ordinal` 的数组仍由完整 JSON array 顺序唯一决定，不能声称由元素值重新排序。

### 2.4 Length prefix、reference、identity 与 target schema

`LP(X)` 精确定义为 `u64le(len(UTF8(X))) || UTF8(X)`；长度是 bytes 数，`u64le` 为无符号 64-bit little-endian。
当参数是 canonical JSON bytes 或原始 bytes 时，LP 直接使用该 byte string，不做文本解码。所有 `||` 都是无分隔 byte
concatenation，domain 字符串逐字区分大小写。

`REF` 是 `{schema_id:SCHEMA_ID,logical_name:LOGICAL_NAME,sha256:HEX64}`，只引用一个带本节 envelope 的 canonical JSON
artifact。reader 必须验证被引用 artifact 的 envelope `schema_id`、logical-name binding 和完整 digest；REF 不表示 filesystem path。
`JSONL_COMMITMENT` 是 `{schema_id:"sa.m8.jsonl-commitment.v1",logical_name:LOGICAL_NAME,media_type:"application/x-ndjson",canonicalization_id:"sa-json-c14n-v1-jsonl",sha256:HEX64,size_bytes:INT[1,2147483648],row_count:INT[1,100000]}`；它承诺 §2.1(8) 的完整 raw JSONL bytes，不是 `REF`，不得作为 artifact 解引用。`schema_id` 是该承诺描述类型的固定字面量，不使它成为可解引用 artifact，也不得被当作 envelope schema。

`FILE_IDENTITY` 是 `{volume_serial:HEX16,filesystem:enum[ntfs,refs],file_id:HEX32,acl_sha256:HEX64}`。`file_id`
是 Windows 128-bit file ID；`acl_sha256` 的 preimage 是 `NtQuerySecurityObject` 返回的 self-relative security descriptor bytes。

下列 artifact 使用统一 envelope
`{schema_id:SCHEMA_ID,schema_version:INT[1,1],canonicalization_id:"sa-json-c14n-v1",logical_name:LOGICAL_NAME,payload:OBJECT}`：

- `sa.m8.experiment-identity.v1.payload`：
  `{experiment_id:ID,reviewed_protocol_path:REPO_PATH,reviewed_protocol_sha256:HEX64,identity_nonce:HEX64,created_at:TS,
  forbidden_history_ids:A<ID;13..13;order=value;unique=value>}`。
- `sa.m8.repository-binding.v1.payload`：
  `{identity_ref:REF,reviewed_protocol_path:REPO_PATH,reviewed_protocol_sha256:HEX64,repository_commit:GIT_OID,
  oid_algorithm:enum[sha1,sha256],repository_dirty:false,experiment_parent_binding:REF,
  publication_parent_bindings:A<{purpose:enum[package,normal-receipt,nonpublication-receipt,abort-receipt,failure-receipt],
  binding_ref:REF};5..5;order=key(purpose);unique=key(purpose)>}`。
- `sa.m8.parent-binding.v1.payload`：
  `{volume_root:FILE_IDENTITY,components:A<TARGET_COMPONENT;1..32;order=ordinal;unique=not-applicable>,parent:FILE_IDENTITY,
  opened_by:"NtCreateFile",walk:"volume-root-component-walk",root_directory_relative:true,share_mask:"read-write-delete",no_follow:true}`。
  validator 必须从 `volume_root` 按 `components` 复走并得到 exact `parent` identity。
- `sa.m8.genesis-layer.v1.payload`：
  `{identity_ref:REF,binding_ref:REF,authorized_by_p6:REF,next_layer:"L0"}`。
- `sa.m8.child-allowlist.v1.payload`：
  `{identity_ref:REF,binding_ref:REF,allowed_images:A<{role:enum[coordinator,provisioner,query-worker,lifecycle-worker,
  fault-worker,report-writer,package-writer,cleanup-writer],source_sha256:HEX64};8..8;order=key(role);unique=key(role)>,
  open_profiles:A<NT_OPEN_PROFILE;10..10;order=key(profile_id);unique=key(profile_id)>,
  operations:A<CONTAINMENT_OPERATION;20..20;order=key(operation_id);unique=key(operation_id)>,
  environment:{inherited_handles:"none-except-audited-control-handles",inherited_handle_ids:A<ID;0..8;order=value;unique=value>,
  variables:A<{name:enum[TEMP,TMP,PIP_CACHE_DIR,ARROW_HOME,LANCE_HOME],target:TARGET};5..5;order=key(name);unique=key(name)>,
  child_current_directory_target:TARGET,library_path_policy:"frozen-system-and-wheel-paths-only"},
  interposition:{required:true,coverage:"all-allowlisted-file-process-network-symbols",symbols:A<INTERPOSITION_SYMBOL;14..14;order=key(module,symbol);unique=key(module,symbol)>,resolver_policy:"frozen-import-table-no-dynamic-resolution",unsupported_code:"CONTAINMENT_UNSUPPORTED"},
  process_policy:{max_active_children:INT[1,1],create_api:"CreateProcessW-with-explicit-handle-list",graceful_terminate_s:INT[5,5],forced_kill_s:INT[10,10]},
  control_evidence:{environment:{api:enum[GetSystemInfo,GlobalMemoryStatusEx,GetLogicalProcessorInformationEx,GetLocaleInfoEx,GetTimeZoneInformation,GetExtendedTcpTable],net_api:"GetExtendedTcpTable",capture:"preflight-post-child-exit"},
  resource_watchdog:{cadence_s:INT[1,1],api:enum[GetProcessMemoryInfo,GetProcessHandleCount,GetDiskFreeSpaceExW,NtQueryDirectoryFile],sample_root_size_api:"enumerate-by-handle"},
  process_inventory:{api:enum[CreateToolhelp32Snapshot,Process32NextW,QueryFullProcessImageNameW],capture:"preflight-post-child-exit",match:"allowlisted-source-sha256-only"},
  network_inventory:{api:"GetExtendedTcpTable"},interposition_ledger:{api:"frozen-wrapper-ledger-v1"}},
  status_map_ref:REF,writer_results_schema:"sa.m8.writer-result.v1",cleanup_failure_schema:"sa.m8.cleanup-failure-record.v1"}`。

  `INTERPOSITION_SYMBOL` exact fields：`{module:enum[ntdll.dll,kernel32.dll,ws2_32.dll,iphlpapi.dll],symbol:enum[NtCreateFile,NtOpenFile,NtReadFile,NtWriteFile,FlushFileBuffers,NtQueryInformationFile,NtQuerySecurityObject,NtSetInformationFile,NtClose,CreateProcessW,TerminateProcess,GetExtendedTcpTable,WSAConnect,connect],wrapper:ID,deny_code:STABLE_CODE,pre_open_check:enum[none,root-handle,opened-handle,control-handle],post_open_identity_check:BOOL}`。`symbols` 必须恰好包含 14 个唯一 tuple：`parent-walk/post-delete-reopen→NtCreateFile(root-handle,post-check true)`、`open-file→NtCreateFile(root-handle,post-check true)`、`readback-file→NtOpenFile(root-handle,post-check true)`、`read-file→NtReadFile(opened-handle,post-check false)`、`write-file/append-file→NtWriteFile(opened-handle,post-check false)`、`flush-file→FlushFileBuffers(opened-handle,post-check false)`、`enumerate-parent/query-file-metadata/query-streams→NtQueryInformationFile(opened-handle,post-check true)`、`query-security→NtQuerySecurityObject(opened-handle,post-check true)`、`rename-no-replace/delete-disposition→NtSetInformationFile(opened-handle,post-check true)`、`close-handle→NtClose(none,post-check false)`、`create-process→CreateProcessW(control-handle,post-check false)`、`terminate-process→TerminateProcess(control-handle,post-check false)`、`network-control→GetExtendedTcpTable(control-handle,post-check false)`、`network-control→WSAConnect(control-handle,post-check false)`、`network-control→connect(control-handle,post-check false)`；除 `NtCreateFile` 与 `NtOpenFile` 的 `module` 为 `ntdll.dll`、`FlushFileBuffers`/`CreateProcessW`/`TerminateProcess` 为 `kernel32.dll`、`GetExtendedTcpTable` 为 `iphlpapi.dll`、`WSAConnect`/`connect` 为 `ws2_32.dll` 外，其余 `ntdll.dll` 符号同表。`wrapper` 必须分别为 `containment-<symbol-lower>-v1`，`deny_code` 对所有网络 outbound alternatives 为 `OUTBOUND_BLOCKED`，其余按 operation 的 expected-status set 绑定。任何 module/symbol/wrapper/deny_code/前后检查不匹配均为 `CONTAINMENT_UNSUPPORTED`。

  `NT_OPEN_PROFILE` exact fields：`{profile_id:enum[parent-directory-open,child-directory-create,child-directory-open,child-file-create,child-file-open,child-file-readback,enumeration-open,rename-source-open,delete-source-open,post-delete-reopen],api:"NtCreateFile",leaf_kind:enum[file,directory],disposition:enum[FILE_CREATE,FILE_OPEN],desired_access:ASCII[1,256],
  share_access:"READ|WRITE|DELETE",create_options:A<enum[FILE_OPEN_REPARSE_POINT,FILE_SYNCHRONOUS_IO_NONALERT,FILE_DIRECTORY_FILE,FILE_NON_DIRECTORY_FILE];3..3;order=value;unique=value>,root_directory_required:true,
  relative_unicode_string_required:true,obj_case_insensitive:false}`。
  Exact matrix（tuple=`leaf_kind,disposition,desired_access,type flag`）：
  `parent-directory-open=(directory,FILE_OPEN,FILE_LIST_DIRECTORY|FILE_READ_ATTRIBUTES|SYNCHRONIZE,FILE_DIRECTORY_FILE)`；
  `child-directory-create=(directory,FILE_CREATE,FILE_ADD_SUBDIRECTORY|FILE_LIST_DIRECTORY|FILE_READ_ATTRIBUTES|FILE_WRITE_ATTRIBUTES|SYNCHRONIZE,FILE_DIRECTORY_FILE)`；
  `child-directory-open=(directory,FILE_OPEN,FILE_LIST_DIRECTORY|FILE_READ_ATTRIBUTES|FILE_WRITE_ATTRIBUTES|SYNCHRONIZE,FILE_DIRECTORY_FILE)`；
  `enumeration-open=child-directory-open`；
  `child-file-create=(file,FILE_CREATE,FILE_READ_DATA|FILE_WRITE_DATA|FILE_APPEND_DATA|FILE_READ_ATTRIBUTES|FILE_WRITE_ATTRIBUTES|DELETE|SYNCHRONIZE,FILE_NON_DIRECTORY_FILE)`；
  `child-file-open=(file,FILE_OPEN,FILE_READ_DATA|FILE_WRITE_DATA|FILE_READ_ATTRIBUTES|FILE_WRITE_ATTRIBUTES|DELETE|SYNCHRONIZE,FILE_NON_DIRECTORY_FILE)`；
  `child-file-readback=(file,FILE_OPEN,FILE_READ_DATA|FILE_READ_ATTRIBUTES|SYNCHRONIZE,FILE_NON_DIRECTORY_FILE)`；
  `rename-source-open=child-file-open`；`delete-source-open=child-file-open`；`post-delete-reopen=child-file-readback`。
  Every row has share `READ|WRITE|DELETE` and the two common options plus the tuple type flag. Rights are the exact token sequence shown,
  including `SYNCHRONIZE`; arbitrary ASCII masks are invalid. `FILE_OPEN_IF`, overwrite, supersede, duplicate options, and mismatched type flags fail preflight.
  The required interposition coverage is the complete allowlisted operation set: every descendant file/directory open and create,
  read, write, append, flush, metadata/reparse/link/stream/security query, enumeration, no-replace rename, delete/disposition,
  post-delete reopen, process create/terminate, listener inventory, and outbound-call denial. Mapping views, hard-link creation, alternate data
  streams, path-based fallback APIs, unlisted process launch or network APIs, and any operation bypassing the allowlisted wrapper
  are forbidden; absent coverage for any one operation yields `CONTAINMENT_UNSUPPORTED` and `ABORTED_PREFLIGHT`.

  `CONTAINMENT_OPERATION` is a closed discriminator union:
  - `FILE_OPERATION`：`{operation_id:enum[parent-walk,create-directory,create-file,open-file,read-file,write-file,append-file,flush-file,readback-file,
    enumerate-parent,query-file-metadata,query-streams,query-security,rename-no-replace,delete-disposition,post-delete-reopen],profile_id:enum[parent-directory-open,child-directory-create,child-directory-open,
    child-file-create,child-file-open,child-file-readback,enumeration-open,rename-source-open,delete-source-open,post-delete-reopen],
    api:enum[NtCreateFile,NtOpenFile,NtReadFile,NtWriteFile,FlushFileBuffers,NtQueryInformationFile,NtQuerySecurityObject,NtSetInformationFile],
    information_class:enum[none,FileRenameInformationEx,FileDispositionInformationEx],authoritative_handle_source:enum[root-directory-handle,opened-file-handle],root_handle_required:true,
    relative_name_required:true,no_follow_required:true,expected_statuses:A<STABLE_CODE;1..8;order=value;unique=value>}`；
  - `HANDLE_CLOSE_OPERATION`：`{operation_id:"close-handle",api:"NtClose",authoritative_handle_source:"audited-handle-ledger",
    root_handle_required:false,relative_name_required:false,no_follow_required:false,profile_id:"not-applicable",
    expected_statuses:A<STABLE_CODE;1..8;order=value;unique=value>}`；
  - `PROCESS_OPERATION`：`{operation_id:enum[create-process,terminate-process],api:enum[CreateProcessW,TerminateProcess],
    authoritative_handle_source:enum[audited-control-handle,explicit-inherited-handle-list],root_handle_required:false,
    relative_name_required:false,no_follow_required:false,profile_id:"not-applicable",expected_statuses:A<STABLE_CODE;1..8;order=value;unique=value>}`；
  - `NETWORK_OPERATION`：`{operation_id:"network-control",apis:A<enum[GetExtendedTcpTable,WSAConnect,connect];3..3;order=value;unique=value>,
    listener_inventory_api:"GetExtendedTcpTable",outbound_deny_apis:A<enum[WSAConnect,connect];2..2;order=value;unique=value>,
    authoritative_handle_source:"process-network-inventory",root_handle_required:false,relative_name_required:false,
    no_follow_required:false,profile_id:"not-applicable",expected_statuses:A<STABLE_CODE;1..8;order=value;unique=value>}`。
  Exact file mapping is `parent-walk→parent-directory-open/NtCreateFile/root-directory-handle`,
  `create-directory→child-directory-create/NtCreateFile/root-directory-handle`,
  `create-file→child-file-create/NtCreateFile/root-directory-handle`, `open-file→child-file-open/NtCreateFile/root-directory-handle`,
  `read-file→child-file-open/NtReadFile/opened-file-handle`, `write-file→child-file-open/NtWriteFile/opened-file-handle`,
  `append-file→child-file-open/NtWriteFile/opened-file-handle`, `flush-file→child-file-open/FlushFileBuffers/opened-file-handle`,
  `readback-file→child-file-readback/NtOpenFile/root-directory-handle`,
  `enumerate-parent→enumeration-open/NtQueryInformationFile/opened-file-handle`,
  `query-file-metadata/query-streams→child-file-open/NtQueryInformationFile/opened-file-handle`,
  `query-security→child-file-open/NtQuerySecurityObject/opened-file-handle`,
  `rename-no-replace→rename-source-open/NtSetInformationFile(FileRenameInformationEx)/opened-file-handle`,
  `delete-disposition→delete-source-open/NtSetInformationFile(FileDispositionInformationEx)/opened-file-handle`, and
  `post-delete-reopen→post-delete-reopen/NtCreateFile/root-directory-handle`.
  A rename operation additionally carries `{destination_parent_binding:REF,destination_leaf:TARGET_COMPONENT,
  destination_parent_identity:FILE_IDENTITY,source_identity_before:FILE_IDENTITY,source_identity_after:FILE_IDENTITY}` and requires same-volume,
  no-replace, destination-absence, and identity equality before/after. The 20 operation rows are exactly the 16 file rows, one close row,
  two process rows, and one network row. The network row covers both listener inventory and outbound-call denial through its closed API alternatives; any `WSAConnect` or `connect` call is intercepted before network access and maps to `OUTBOUND_BLOCKED`. Any missing discriminator field, mismatched matrix value, or unlisted operation fails closed.

`TARGET` 是 `{parent_binding:REF,components:A<TARGET_COMPONENT;1..32;order=ordinal;unique=not-applicable>,
leaf_kind:enum[file,directory],leaf_name:TARGET_COMPONENT}`；`components` 是从 verified parent handle 开始的相对打开顺序，
最后一个元素必须等于 `leaf_name`。experiment root、package 和 receipt 只能通过 TARGET 表达。`parent_binding` 必须是
`schema_id=sa.m8.parent-binding.v1` 的 REF。P4 的 experiment/acquisition/dependency/source/input targets 使用 P2 `experiment_parent_binding`；P4 abort/failure receipt targets
分别使用 P2 `purpose=abort-receipt` 与 `purpose=failure-receipt` 的 `binding_ref`。P7A package、normal、nonpublication、abort
和 failure targets 分别使用 P2 `purpose=package/normal-receipt/nonpublication-receipt/abort-receipt/failure-receipt` 的
`binding_ref`。上述关系全部逐字比较 REF，不得以路径或位置推断绑定。

## 3. External gate record schema

All eleven external gate records use the §2.4 envelope with the one and only envelope `schema_id`
`sa.m8.external-gate-record.v1`; `logical_name` is
`external-gates/<gate-id-lower>/<record_id>.json`. The envelope does not contain its own digest. `GATE_PAYLOAD` below is a
closed union discriminated by `payload.gate_id`, and that value must equal the outer payload `gate_id`; no per-gate envelope
schema ID exists.

`GATE_DECISION` is the closed enum, in this order:
`P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY,P0_NOT_ACCEPTED,AUTHORIZED,NOT_AUTHORIZED,VERIFIED,REJECTED,
PUBLICATION_REFUSED,ADMITTED,NOT_ADMITTED,SELECT_LANCEDB_EXACT_FLAT,SELECT_SQLITE_NO_CHANGE`.
`NEXT_ACTION` is the closed enum, in this order:
`none,request-p1,request-p2,request-p3,request-p4,request-p5,request-p6,run-l0,request-p7a,write-package,
run-nonpublication-cleanup,run-abort-cleanup,request-p8,request-p9,stop`.

`sa.m8.external-gate-record.v1.payload` exact fields are:

- `record_id:ID`, `gate_id:GATE`, `reviewed_protocol_path:REPO_PATH`, `reviewed_protocol_sha256:HEX64`;
- `predecessors:A<{gate_id:GATE,record_id:ID,record_sha256:HEX64,expected_decision:GATE_DECISION,
  expected_next_action:NEXT_ACTION};0..1;order=key(gate_id);unique=key(gate_id)>`;
- `actor:{name:ASCII[1,128],role:enum[owner,independent-reviewer,independent-verifier]}`;
- `independence:{required:BOOL,satisfied:BOOL,basis:UTF8[1,1024]}`;
- `timestamp:TS`, `decision:GATE_DECISION`, `reason:UTF8[1,4096]`, `allowed_next_action:NEXT_ACTION`;
- `scope:{workloads:A<WORKLOAD;0..4;order=value;unique=value>,allow_network:BOOL,allow_production_write:false,
  operations:A<enum[review,identity,binding,acquire,prepare,execute,verify,publish,cleanup,admit,select];1..3;
  order=value;unique=value>,write_targets:A<TARGET;0..23;order=ordinal;unique=not-applicable>,
  read_refs:A<REF;0..64;order=key(logical_name,schema_id,sha256);unique=key(logical_name)>}`;
- `payload:GATE_PAYLOAD`.

The eleven `GATE_PAYLOAD` variants are the following exact closed objects. Their serialized `gate_id` is the union
discriminator and is not inferred from the logical name.

| gate | exact predecessor | exact payload after discriminator | decision / next action |
| --- | --- | --- | --- |
| P0 | `[]` | `{gate_id:"P0",review_kind:"P0_TECHNICAL_SCOPE_REVIEW",finding_ids:A<ID;0..64;order=value;unique=value>}` | `P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY/request-p1` or `P0_NOT_ACCEPTED/stop` |
| P1 | `[P0]` | `{gate_id:"P1",identity_ref:REF,forbidden_history_ids:A<ID;13..13;order=value;unique=value>}` | `AUTHORIZED/request-p2` or `NOT_AUTHORIZED/stop` |
| P2 | `[P1]` | `{gate_id:"P2",binding_ref:REF,repository_commit:GIT_OID,oid_algorithm:enum[sha1,sha256]}` | `AUTHORIZED/request-p3` or `NOT_AUTHORIZED/stop` |
| P3 | `[P2]` | `{gate_id:"P3",binding_ref:REF,text_audit_ref:REF}` | `VERIFIED/request-p4` or `REJECTED/stop` |
| P4 | `[P3]` | `{gate_id:"P4",acquisition_target:TARGET,experiment_root_target:TARGET,dependency_lock_target:TARGET,source_target:TARGET,input_targets:A<TARGET;17..17;order=ordinal;unique=not-applicable>,abort_receipt_target:TARGET,failure_receipt_target:TARGET}` | `AUTHORIZED/request-p5` or `NOT_AUTHORIZED/stop` |
| P5 | `[P4]` | `{gate_id:"P5",dependency_lock:REF,source_inventory:REF,corpus_manifests:A<REF;4..4;order=key(logical_name);unique=key(logical_name)>,query_gold_manifests:A<REF;4..4;order=key(logical_name);unique=key(logical_name)>,sample_plans:A<REF;4..4;order=key(logical_name);unique=key(logical_name)>,sample_inventory:REF,fault_registry:REF,status_map:REF,deadline_plan:REF,child_allowlist:REF}` | `VERIFIED/request-p6`; rejection is `REJECTED/run-abort-cleanup` if anything was created, otherwise `REJECTED/stop` |
| P6 | `[P5]` | `{gate_id:"P6",authorized_layers:A<LAYER;5..5;order=value;unique=value>,execution_deadline_s:INT[2952330,2952330],post_execution_deadline_s:INT[1500,1500],preparation_through_cleanup_deadline_s:INT[2956230,2956230],deadline_plan_ref:REF,child_allowlist_ref:REF,p4_cleanup_authorization_ref:REF}` | `AUTHORIZED/run-l0` or `NOT_AUTHORIZED/stop` |
| P7 | `[P6]` plus exact L0–L4 chain | `{gate_id:"P7",execution_report:REF,verification_report:REF,layer_members:A<REF;5..5;order=key(logical_name,schema_id,sha256);unique=key(logical_name)>,evidence_disposition:enum[VALID_ADOPTION_ELIGIBLE,VALID_NOT_ADOPTION_ELIGIBLE]}` | `VERIFIED/request-p7a`; rejection is `REJECTED/run-abort-cleanup` if anything exists, otherwise `REJECTED/stop` |
| P7A | `[P7]` | `{gate_id:"P7A",repository_binding_ref:REF,package_target:TARGET,normal_receipt_target:TARGET,nonpublication_receipt_target:TARGET,abort_receipt_target:TARGET,failure_receipt_target:TARGET,selected_write_targets:A<TARGET_SLOT;5..5;order=ordinal;unique=not-applicable>,written_targets:A<TARGET_SLOT;5..5;order=ordinal;unique=not-applicable>,package_schema:"sa.m8.durable-package.v1",normal_receipt_schema:"sa.m8.cleanup-receipt.v1",nonpublication_receipt_schema:"sa.m8.nonpublication-cleanup-receipt.v1",abort_receipt_schema:"sa.m8.abort-cleanup-receipt.v1",failure_receipt_schema:"sa.m8.cleanup-failure-record.v1",source_inventory_ref:REF,package_writer_source_sha256:HEX64,cleanup_writer_source_sha256:HEX64}` | `AUTHORIZED/write-package`, `PUBLICATION_REFUSED/run-nonpublication-cleanup`, or `NOT_AUTHORIZED/run-nonpublication-cleanup` |
| P8 | `[P7A]` plus `CLEANUP_VERIFIED` writer results | `{gate_id:"P8",package_ref:REF,receipt_ref:REF,durable_package_sha256:HEX64,cleanup_receipt_sha256:HEX64,package_writer_result_ref:REF,normal_receipt_writer_result_ref:REF,counterbalance_arms:A<{workload:WORKLOAD,repetition:INT[0,5],arm:enum[AB,BA]};20..20;order=key(workload,repetition);unique=key(workload,repetition)>,admission_scope:UTF8[1,1024]}` | `ADMITTED/request-p9` or `NOT_ADMITTED/stop` |
| P9 | `[P8]` | `{gate_id:"P9",package_ref:REF,receipt_ref:REF,durable_package_sha256:HEX64,cleanup_receipt_sha256:HEX64,selected_backend:BACKEND}` | `SELECT_LANCEDB_EXACT_FLAT/none` or `SELECT_SQLITE_NO_CHANGE/none` |

The predecessor row is not a claim copied from the successor. It must resolve to the one external gate artifact named by
`record_id` and `record_sha256`; `expected_decision` and `expected_next_action` must byte-for-byte equal that artifact's actual
fields. The only gate edges are `P0→P1→P2→P3→P4→P5→P6→P7→P7A→P8→P9`. P0 alone has no predecessor. P7's layer
chain and P8's cleanup evidence are additional typed preconditions, never substitute gate predecessors. A predecessor whose
decision/action is not the accepting pair for that edge cannot be spliced into a successor.

P0/P3/P5/P7 require `independence={required:true,satisfied:true,...}`; every other gate requires
`required=false,satisfied=false`. Exact operation sets are P0/P3/P5=`[review]`, P1=`[identity]`, P2=`[binding]`,
P4=`[acquire,prepare]`, P6=`[execute]`, P7=`[verify]`, P7A=`[cleanup,publish]`, P8=`[admit]`, and P9=`[select]`.
P0–P3 workloads are `[]`; P4–P9 contain all four WORKLOAD values.

P4 `input_targets` positions are exactly: four corpus manifests, four query/gold manifests, four sample plans, sample
inventory, fault registry, status map, deadline plan, and child allowlist. Dependency lock and source inventory are represented
only by their scalar targets and are not duplicated. P4 `scope.write_targets` is exactly, in order, acquisition target,
experiment-root target, dependency-lock target, source target, the 17 input targets, abort receipt target, and failure receipt
target. P4 alone may set `allow_network=true`, solely for dependency acquisition from the ordered lock hosts. Every other gate
sets it false.

P0–P3 and P5–P7 have empty `write_targets`; their `read_refs` are the exact REFs they inspect. P1/P2 administrative artifact
creation is represented by the referenced artifact plus its external record, not by a filesystem TARGET. P7A `scope.write_targets` is the five reserved scalar targets in the fixed order package, normal receipt, nonpublication receipt,
abort receipt, failure receipt; it is not an assertion that all five are selected or written. P7A payload
`selected_write_targets` and `written_targets` are parallel five-slot arrays in that order, using only the exact target or
`"not-applicable"`. For `AUTHORIZED`, both arrays are `[package,normal,not-applicable,not-applicable,not-applicable]`; for
`PUBLICATION_REFUSED` or `NOT_AUTHORIZED`, both are `[not-applicable,not-applicable,nonpublication,not-applicable,not-applicable]`;
for an abort cleanup branch they are `[not-applicable,not-applicable,not-applicable,abort,not-applicable]`; for a cleanup-failure
branch they are `[not-applicable,not-applicable,not-applicable,not-applicable,failure]`. A package-failure branch has selected
`[package,normal,not-applicable,not-applicable,failure]` and written
`[package,not-applicable,not-applicable,not-applicable,failure]`. A slot not in the branch's exact array must be the sentinel,
and a real target in any other slot is `INVALID_PROTOCOL_DEVIATION`. P8/P9 have empty `write_targets` and read exactly their
package/receipt/writer-result authority REFs. All records bind the same protocol path and digest. Missing refs, extra refs or targets,
wrong order, wrong predecessor, digest mismatch, or scope expansion is a gate stop.

The P7A schema literals must equal the corresponding artifact envelope schema IDs. Its abort and failure targets must be
byte-for-byte equal to P4's frozen targets. Its package and all three publication-receipt targets use P2's corresponding
publication parent binding as specified in §2.4. P9 decision/backend obeys the iff: `SELECT_LANCEDB_EXACT_FLAT` iff
`lancedb-embedded-exact`; otherwise only `SELECT_SQLITE_NO_CHANGE/sqlite-linear-exact` is valid. P8's 20 arms are exactly six
rows each for 1K and 10K and four each for both 100K workloads; repetition ordinals are contiguous from zero, even means `AB`,
and odd means `BA`. P9 must byte-for-byte reuse P8's package/receipt four-tuple.

`sa.m8.writer-result.v1` is an out-of-band envelope and is never referenced by the artifact bytes it attests. Its exact
payload is a closed discriminated union on `status`:

- success variant:
  `{writer_role:enum[launcher,harness,generator,validator,writer,configuration],performing_child_role:enum[coordinator,provisioner,query-worker,lifecycle-worker,fault-worker,report-writer,package-writer,cleanup-writer],authorization_ref:REF,execution_authorization_refs:A<REF;0..1;order=key(logical_name,schema_id,sha256);unique=key(logical_name)>,operation_id:CONTAINMENT_OPERATION_ID,target_binding:REF,target_leaf:TARGET_COMPONENT,target_identity:FILE_IDENTITY,lifecycle_state_from:enum[UNBOUND_DRAFT,P0_ACCEPTED,IDENTITY_AUTHORIZED,BINDING_FROZEN,TEXT_AUDITED,PREPARATION_AUTHORIZED,INPUTS_PREPARED,INPUTS_FROZEN,EXECUTION_AUTHORIZED,L0_PASSED,L1_PASSED,L2_PASSED,L3_PASSED,L4_PASSED,EXECUTION_RECORDED,RAW_VERIFIED,PUBLICATION_AUTHORIZED,PACKAGE_WRITTEN,CLEANUP_IN_PROGRESS,CLEANUP_VERIFIED,NONPUBLICATION_CLEANUP_IN_PROGRESS,ABORT_CLEANUP_IN_PROGRESS,CLEANUP_FAILURE_RECORD,P8_DECIDED],lifecycle_state_to:enum[P0_ACCEPTED,IDENTITY_AUTHORIZED,BINDING_FROZEN,TEXT_AUDITED,PREPARATION_AUTHORIZED,INPUTS_PREPARED,INPUTS_FROZEN,EXECUTION_AUTHORIZED,L0_PASSED,L1_PASSED,L2_PASSED,L3_PASSED,L4_PASSED,EXECUTION_RECORDED,RAW_VERIFIED,PUBLICATION_AUTHORIZED,PACKAGE_WRITTEN,CLEANUP_IN_PROGRESS,CLEANUP_VERIFIED,NONPUBLICATION_CLEANUP_IN_PROGRESS,ABORT_CLEANUP_IN_PROGRESS,CLEANUP_FAILURE_RECORD,P8_DECIDED,P9_RECORDED,ABORTED_CLEANUP_VERIFIED,ABORTED_PREFLIGHT,ABORTED_RUNTIME,INVALID_PROTOCOL_DEVIATION,REJECTED_INPUT_AUDIT,REJECTED_RAW_EVIDENCE,VALID_EVIDENCE_NOT_PUBLISHED,CLEANUP_INCOMPLETE],writer_source_sha256:HEX64,create_disposition:"CREATE_NEW",write_count:INT[1,1],flush_verified:true,close_verified:true,reopen_verified:true,readback_verified:true,status:"WRITTEN",bytes_sha256:HEX64,byte_count:INT[1,268435456],stable_code:"NONE"}`;
- failure variant:
  `{writer_role:enum[launcher,harness,generator,validator,writer,configuration],performing_child_role:enum[coordinator,provisioner,query-worker,lifecycle-worker,fault-worker,report-writer,package-writer,cleanup-writer],authorization_ref:REF,execution_authorization_refs:A<REF;0..1;order=key(logical_name,schema_id,sha256);unique=key(logical_name)>,operation_id:CONTAINMENT_OPERATION_ID,target_binding:REF,target_leaf:TARGET_COMPONENT,lifecycle_state_from:enum[PUBLICATION_AUTHORIZED,PACKAGE_WRITTEN,CLEANUP_IN_PROGRESS,NONPUBLICATION_CLEANUP_IN_PROGRESS,ABORT_CLEANUP_IN_PROGRESS,CLEANUP_FAILURE_RECORD],lifecycle_state_to:enum[NONPUBLICATION_CLEANUP_IN_PROGRESS,CLEANUP_FAILURE_RECORD,CLEANUP_INCOMPLETE],writer_source_sha256:HEX64,create_disposition:"CREATE_NEW",write_count:INT[0,1],failure_stage:enum[create,write,flush,close,reopen,readback,validation],status:"WRITE_FAILED",stable_code:STABLE_CODE}`.

For every normal, nonpublication, abort, and failure receipt, the exact `receipt_writer_result_ref` resolves to one success
variant whose binding, role, authorization, state transition, byte digest/count, create, flush, close, reopen and readback facts
equal the actual receipt. Omission or mismatch is `INVALID_PROTOCOL_DEVIATION`. The failure variant has no target identity,
artifact digest/count, success booleans, or artifact REF; its `status` is a writer result status, while branch triggers and
terminal states use their separately declared enums. Success has `stable_code="NONE"`; failure must use the phase-mapped
`STABLE_CODE`; the variants may not mix fields.
`CONTAINMENT_OPERATION_ID` is the closed 20-value operation ID enum in §2.4.

A writer result must be emitted by the allowlisted image for `performing_child_role`. `writer_source_sha256` equals that image
digest. Package/cleanup writers additionally equal P7A's role-specific digest and source inventory writer entry. A preparation
write uses the P4 record as `authorization_ref` and has no execution authorization. A P6 execution write uses P6 in both
authority fields. Package and normal/nonpublication publication cleanup writes use P7A and P6 respectively as applicable.
Abort/failure writes use P4 as standing cleanup authority before P6, and P4 plus P6 after P6. The rejected P5 or P7 record is
never treated as authority. Each attestation's target fields, operation, source, state transition, byte digest and byte count
must equal the actual handle-relative operation and target artifact. For a receipt or failure record that contains
`receipt_writer_result_ref` or `failure_record_writer_result_ref`, `bytes_sha256` is the SHA-256 of the deterministic
attestation projection: canonical bytes with that one writer-result REF value replaced by the fixed ASCII sentinel
`WRITER_RESULT_REF_EXCLUDED` before hashing; `byte_count` is the projection byte count. The projection preserves every
other field and is not an artifact or REF. The writer-result REF itself is excluded only from this projection, never from
the stored receipt bytes. Thus receipt bytes reference the detached result, while the result attests an acyclic projection
that cannot contain its own digest. For targets without such a field, `bytes_sha256` and `byte_count` cover the exact
stored canonical bytes. Non-`WRITTEN` status creates no usable target REF.

A writer-result REF has a `writer-results/` logical-name prefix and `.json` suffix and is not one of the eleven external gate
records. Each authorized target has exactly one result; no result may attest two targets. Layer/result artifacts never contain
their own writer-result REF, preventing digest cycles. Execution report, package/receipt authority, and P7/P8 refer to the
out-of-band results required for their branch.

## 4. Inputs 与 generator 规则

### 4.1 Dependency/source inventory

`sa.m8.dependency-lock.v1.payload` exact fields：

`{platform:{os:"windows-11",kernel:"10.0.26200",arch:"x86_64",python_abi:"cp311"},
python:{implementation:"cpython",version:"3.11.9",bits:INT[64,64],executable_sha256:HEX64},
packages:A<{name:ID,version:ASCII[1,32],filename:ASCII[1,240],size_bytes:INT[1,2147483648],extracted_size_bytes:INT[1,2147483648],sha256:HEX64,
license_spdx:ASCII[1,64],source_url:HTTPS_URL};4..32;order=key(name,version,sha256);unique=key(name)>,
direct_packages:A<ID;4..4;order=ordinal;unique=value>,size_digest:HEX64,extracted_size_digest:HEX64,cache_size_digest:HEX64,network_policy:{hosts:A<ASCII[1,253];1..8;order=ordinal;unique=value>,
redirect_limit:INT[2,2],tls_required:true,proxy:enum[none,explicit-allowlist],sdist_allowed:false,vcs_allowed:false,
editable_allowed:false,retries:INT[2,2]}}`。

direct package 顺序和值固定为 `lancedb,numpy,psutil,pyarrow`，版本分别为 `0.38.0,2.4.6,7.2.2,25.0.1`。依赖锁还必须包含 `size_digest`、`extracted_size_digest` 和 `cache_size_digest` 三个 `HEX64` 字段：分别为按 packages 声明顺序计算的
`SHA256(LP("sa-m8-dependency-size-v1")||逐项 LP(name)||LP(canonical_dec(size_bytes)))`、
`SHA256(LP("sa-m8-dependency-extracted-size-v1")||逐项 LP(name)||LP(canonical_dec(extracted_size_bytes)))` 和
`SHA256(LP("sa-m8-dependency-cache-size-v1")||LP(canonical_dec(total cache bytes)))`。`total cache bytes` 是依赖缓存目录
中所有 regular file 的 handle-relative enumeration size 总和；每个 digest 必须在 P5、resource_metrics 和 execution report 中逐字相等。
transitive wheels 必须显式存在于 packages，禁止运行时解析、替换或联网补取；P4 acquisition 的 hosts 也必须是
实际请求 host 的完整有序 allowlist。`sum(packages.size_bytes)`、每个解压后 dependency footprint 以及所有 dependency
cache bytes 均必须不超过 `2147483648`；P4/P5 必须写出逐 package size digest、extracted-size digest 和总和，任一
总和或 hard-cap proof 不一致即 `DEPENDENCY_VERIFY_TIMEOUT`/preflight abort。

`sa.m8.source-inventory.v1.payload` exact fields：
`{files:A<{relative_name:REPO_PATH,size_bytes:INT[1,1073741824],sha256:HEX64,
role:enum[launcher,harness,generator,validator,writer,configuration]};6..1000;order=key(relative_name,size_bytes,sha256);unique=key(relative_name)>,
writer_sources:A<{role:enum[package-writer,cleanup-writer],relative_name:REPO_PATH,sha256:HEX64};2..2;order=key(role);unique=key(role)>,
generator_source_sha256:HEX64,validator_source_sha256:HEX64,
repository_commit:GIT_OID,repository_dirty:false}`。
P0–P3 issuer provenance does not depend on this future artifact: those records are signed administrative JSON and require no
executable issuer source field. P4 authorizes production of this inventory; P5 independently verifies it. P4–P9 actor records
likewise contain no self-asserted actor-source digest. Executable provenance exists only on generated artifacts and writer
results and must equal a source-inventory/child-allowlist digest after those artifacts exist.

### 4.2 Corpus

四个 `sa.m8.corpus-manifest.v1` payload 均为：
`{workload:WORKLOAD,namespace:"sa-m8-active-corpus-20260911",row_count:INT[1000,100000],corpus_jsonl:JSONL_COMMITMENT,vector_profile:{name:"synthetic-shake256-unit-vector-512-f32-v1",
dimension:INT[512,512],dtype:"float32-le",normalization:"float64-l2-then-float32",metric:"cosine"},
rows:A<CORPUS_ROW;1000..100000;order=key(chunk_id);unique=key(chunk_id)>,identity_set_sha256:HEX64,
metadata_sha256:HEX64,raw_vector_bytes:INT[2048000,204800000],metadata_bytes:INT[1,1073741824],
canonical_jsonl_bytes:INT[1,2147483648],generator_source_sha256:HEX64}`。

`CORPUS_ROW` exact fields：`{chunk_id:ID,owner_id:ID,source_id:ID,generation_id:ID,snapshot_id:ID,tombstoned:BOOL,
vector_profile:"synthetic-shake256-unit-vector-512-f32-v1",dimension:INT[512,512],normalization:"l2",
content_fingerprint:HEX64,vector_bytes_sha256:HEX64}`。workload 的 `row_count` 分别固定为 1,000、10,000、100,000、
100,000；`len(rows)=row_count`，生成时所有 row 均 `tombstoned=false`。`chunk_id` 全局唯一；四个 workload 使用互不相交的
`chunk_id`，但后端比较必须使用同一 workload 的同一 corpus artifact。`corpus_jsonl.row_count=row_count=len(rows)` and
`corpus_jsonl.size_bytes=canonical_jsonl_bytes`. Decoding the external JSONL yields exactly `row_count` rows in manifest `rows`
order; projecting away `vector_b64` is byte-for-byte equal to each manifest `CORPUS_ROW`. Its ordered chunk-ID set equals the
manifest set, with no missing, extra, or reordered row.

canonical JSONL 每行除上述字段再有 `vector_b64:ASCII[2732,2732]`。identity ordinal 定义在 `i∈{0,…,row_count−1}`；row `i` 的 `chunk_id` 使用 identity ordinal `i`；
`owner_id` 使用 `floor(i/20)`，`source_id` 使用 `floor(i/100)`，`generation_id` 与 `snapshot_id` 使用 `floor(i/1000)`。
每个字段均为 `id-<kind>-` 加
`SHA256(LP("sa-m8-corpus-id-v1")||LP("1")||LP(namespace)||LP(workload)||LP(kind)||LP(decimal(identity_ordinal)))`
的完整 64 hex 后缀；`kind` 是 `chunk,owner,source,generation,snapshot`，所有 ordinal 都是无前导零 ASCII 十进制。
因此每个 owner group 恰有 20 rows，足以为 filtered top-5 形成完整 gold；末组也完整，因为四个 row count 均可被 20 整除。
向量 preimage 为
`LP("sa-m8-vector-v1")||LP(namespace)||LP(workload)||LP(chunk_id)||LP("512")`，SHAKE256 输出 4,096 bytes，
依次解释为 512 个 little-endian u64；每项映射为 `(u64+1)/18446744073709551616`，按 binary64 L2 归一化后转
binary32 little-endian，要求所有值 finite 且最终 2,048 bytes 不全零。

`content_fingerprint` 的 preimage 是
`LP("sa-m8-content-fingerprint-v1")||LP(canonical metadata without content_fingerprint/vector_b64)||LP(decoded 2048 bytes)`；
`vector_bytes_sha256` 的 preimage 是解码后的 2,048 bytes。`identity_set_sha256` 是按 manifest `rows` 顺序连接每个
`LP(chunk_id)` 的 SHA-256；`metadata_sha256` 是按同一顺序连接每个不含 vector bytes/b64 的 canonical `CORPUS_ROW`
bytes 的 `LP` 后所得 SHA-256。两者承诺外部 JSONL，不是 artifact 自身摘要。

### 4.3 Query/gold

`sa.m8.query-gold-manifest.v1.payload` exact fields：
`{workload:WORKLOAD,seed:INT[20260911,20260911],namespace:"sa-m8-active-corpus-20260911",
eligible_ids:A<ID;220..1100;order=value;unique=value>,eligible_identity_sha256:HEX64,
queries:A<QUERY;220..1100;order=key(query_id);unique=key(query_id)>,gold:A<GOLD;220..1100;order=key(gold_id);unique=key(gold_id)>,
counts:{eligible:INT[220,1100],measured_hit:INT[100,800],measured_filtered_hit:INT[0,400],
measured_deny_owner:INT[25,100],measured_deny_source:INT[25,100],measured_unique:INT[200,1000],warmup:INT[20,100],manifest_total:INT[220,1100]},
generator_source_sha256:HEX64,oracle:"numpy-float64-exhaustive",score_tolerance:"0.00001",tie_tolerance:"0.000001"}`。

`QUERY` exact fields：`{query_id:ID,role:QUERY_ROLE,role_ordinal:INT[0,1099],query_kind:QUERY_KIND,query_class:QUERY_CLASS,target_chunk_id:ID,
vector_bytes_sha256:HEX64,filter:{owner_id:ID,source_id:ID,generation_id:ID,snapshot_id:ID,tombstoned:false,
filter_mode:enum[exact,deny-owner,deny-source,none]},top_k:INT[1,5],score_threshold:DEC,warmup:BOOL,gold_id:ID}`。

`GOLD` exact fields：`{gold_id:ID,query_id:ID,target_chunk_id:ID,top_k:INT[1,5],score_threshold:DEC,
ids:A<ID;0..5;order=ordinal;unique=value>,scores_f64_le_hex:A<HEX16;0..5;order=ordinal;unique=not-applicable>,oracle_empty:BOOL}`。
`ids` and `scores_f64_le_hex` lengths must be equal. For `measured-hit`, `measured-filtered-hit`, and `warmup`,
`oracle_empty=false` and both lengths equal `top_k`; for both deny roles, `oracle_empty=true`, `ids=[]`, and
`scores_f64_le_hex=[]`. A non-deny gold with fewer than `top_k` exhaustive eligible results is invalid and fails closed.

The allocator performs exactly one eligible-ID sort by `SHA256(LP("sa-m8-eligible-v1")||LP(namespace)||LP(workload)||
LP(chunk_id))` bytes ascending, then chunk ID on equal digest, and takes the first `manifest_total` active rows. `eligible_ids`
is that ordered prefix sorted into canonical `order=value` only for serialization; `eligible_identity_sha256` is
`SHA256(LP("sa-m8-eligible-set-v1")||LP(namespace)||LP(workload)||LP(concatenation of LP(chunk_id) in allocator order))`.
The allocator-order list is then partitioned without replacement, in table order, into measured-hit, measured-filtered-hit,
measured-deny-owner, measured-deny-source, and warmup. The frozen partition offsets are the cumulative counts in the manifest's
`counts` object, in that exact role order; each slice receives role ordinals `0..count-1`, and no validator may choose a new seed,
repartition, or derive an alternate order. The role sets are pairwise disjoint and their union is exactly
`eligible_ids`; `len(eligible_ids)=len(queries)=len(gold)=manifest_total=counts.eligible`.
`counts.measured_unique=counts.measured_hit+counts.measured_filtered_hit+counts.measured_deny_owner+counts.measured_deny_source`,
`counts.manifest_total=counts.measured_unique+counts.warmup`, and the two deny counts are equal.

Within each role, `role_ordinal` is the zero-based position in that role's allocator-order slice and is a required serialized `QUERY.role_ordinal:INT[0,1099]` field; validators recompute it and require byte equality before assigning top-k or IDs. For every selected identity:
`query_id="q-"+SHA256(LP("sa-m8-query-id-v1")||LP("1")||LP(namespace)||LP(seed)||LP(workload)||LP(role)||
LP(query_kind)||LP(target_chunk_id)||LP(canonical_dec(role_ordinal)))`; and
`gold_id="g-"+SHA256(LP("sa-m8-gold-id-v1")||LP("1")||LP(namespace)||LP(workload)||LP(query_id)||LP(target_chunk_id)||
LP(canonical_dec(top_k))||LP(canonical_dec(score_threshold)))`. The `canonical_dec` arguments are typed INT or DEC before conversion;
no raw JSON spelling, implicit string conversion, or alternate decimal spelling is accepted.
Every QUERY's `gold_id` and every GOLD's `query_id` form a true two-way one-to-one mapping; their query, target, top-k and
threshold values are byte-for-byte equal. IDs are globally unique across all four manifests.

The complete iff mapping is:

| role | query_kind | query_class | filter_mode | warmup | top_k | score_threshold | gold invariant |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `measured-hit` | `hit` | `unfiltered` | `none` | `false` | role ordinal: 1/3/5 | `-1` | nonempty, exact `top_k` |
| `measured-filtered-hit` | `filtered-hit` | `filtered` | `exact` | `false` | role ordinal: 1/3/5 | `-1` | nonempty, exact `top_k`, every ID passes filter |
| `measured-deny-owner` | `deny-owner` | `deny` | `deny-owner` | `false` | `5` | `0.999999` | empty, `oracle_empty=true` |
| `measured-deny-source` | `deny-source` | `deny` | `deny-source` | `false` | `5` | `0.999999` | empty, `oracle_empty=true` |
| `warmup` | `warmup` | `unfiltered` | `none` | `true` | `1` | `-1` | nonempty, exact `1` |

Each row must satisfy this table in both directions; a field combination not listed is invalid. For hit, filtered-hit, and
warmup, `ids[0]` is the target chunk. `none` means the filter identity fields remain equal to the target row and
`tombstoned=false`, but the backend ignores them; `exact` applies all four identity fields as AND. Deny roles replace only
the corresponding owner/source identity with `id-deny-<kind>-` plus
`SHA256(LP("sa-m8-deny-id-v1")||LP(namespace)||LP(workload)||LP(kind)||LP(target_chunk_id)||LP(decimal(role_ordinal)))`,
where kind is `owner` or `source`, and apply all four fields as AND. The replacement must be absent from every corpus identity
of that kind; collision is input-freeze failure and may not trigger seed or suffix changes. The oracle must independently scan
all active corpus rows and prove the four-field deny predicate has cardinality zero.

The oracle decodes each `HEX16` as exactly eight little-endian IEEE-754 binary64 bytes and rejects NaN, either infinity, and
negative zero. It computes normalized dot products in NumPy float64, applies filter and score threshold before sorting, and
sorts by descending unrounded score then ascending chunk ID. `score_tolerance=0.00001` is used only to compare a recomputed
finite score with the stored score: absolute error must be at most that value. `tie_tolerance=0.000001` never changes ranking;
it is an audit assertion that any adjacent scores whose absolute difference is at most that value appear in chunk-ID order.
A stored score outside tolerance or a near-tie violating that ordering fails input freeze. Query vector bytes equal the target
row bytes exactly.

Gold/query fields are bidirectionally equal under the ID equations above. Warmup replays the same frozen manifest identities
inside every backend/repetition and is excluded from latency, Recall, MRR, no-hit precision and repetition-ratio populations.
Recall@1/3/5 and MRR use only measured hit/filtered-hit; no-hit precision uses only both deny roles with fixed denominators.
Any non-finite float, tolerance failure, collision, role overlap, cardinality mismatch, set/bijection failure, deny cardinality
nonzero, or digest mismatch fails input freeze.

For each nonempty hit or filtered-hit role with count `N`, `N mod 5=0`; zero-based role ordinal `r` receives top-k 1 iff
`0<=r<N/5`, top-k 3 iff `N/5<=r<3N/5`, and top-k 5 iff `3N/5<=r<N`. Thus counts are exactly 20%/40%/40%. `100k-capacity` has zero filtered-hit items;
its zero count is explicit and no filtered role may be generated.

| workload | hit | filtered-hit | deny-owner | deny-source | measured unique | warmup | total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `1k-correctness` | 100 | 50 | 25 | 25 | 200 | 20 | 220 |
| `10k-single-user` | 300 | 100 | 50 | 50 | 500 | 50 | 550 |
| `100k-capacity` | 800 | 0 | 100 | 100 | 1,000 | 100 | 1,100 |
| `100k-filtered` | 400 | 400 | 100 | 100 | 1,000 | 100 | 1,100 |

## 5. Sample plan、inventory 与公平性

`sa.m8.sample-plan.v1.payload` exact fields：
`{workload:WORKLOAD,logical_repetitions:INT[4,6],backend_order:A<{repetition:INT[0,5],order:A<BACKEND;2..2;order=ordinal;unique=value>};4..6;order=key(repetition);unique=key(repetition)>,
query_warmup_per_run:INT[20,100],query_measured_per_run:INT[200,1000],build_warmup_per_backend:INT[1,1],build_measured_per_backend:INT[4,6],
lifecycle_operations:A<LIFECYCLE_OPERATION;7..7;order=ordinal;unique=value>,lifecycle_warmup_per_operation_backend:INT[1,1],
lifecycle_measured_per_operation_backend:INT[6,20],affinity:{logical_cpu_set:A<INT[0,15];1..1;order=value;unique=value>,thread_count:INT[1,1]},
cache_policy:"cold-open-then-in-process-warmup",measurement_boundary:"after-warmup-before-cleanup",root_policy:"new-root-per-sample"}`。
`lifecycle_operations` 的七个 ordinal 位置固定为 `[incremental-upsert,replace,tombstone,hard-delete,reopen,rebuild,
rollback-after-failed-candidate]`；任何重排、缺项或重复均使 sample plan 无效。

下表是上述区间字段的唯一 workload 常量；validator 必须逐字段 exact equality：

| workload | repetitions | query warmup/run | query measured/run | build measured/backend | lifecycle measured/operation/backend |
| --- | ---: | ---: | ---: | ---: | ---: |
| `1k-correctness` | 6 | 20 | 200 | 6 | 20 |
| `10k-single-user` | 6 | 50 | 500 | 6 | 10 |
| `100k-capacity` | 4 | 100 | 1,000 | 4 | 6 |
| `100k-filtered` | 4 | 100 | 1,000 | 4 | 6 |

所有 workload 的 build warmup/backend 和 lifecycle warmup/operation/backend 均为 1，logical CPU set 固定 `[0]`。
偶数 repetition 的 backend order 为 `[sqlite-linear-exact,lancedb-embedded-exact]`，奇数为反向；该 AB/BA order 是
确定性的 counterbalance assignment，不是额外的 repetition 或 sample multiplication factor。

四类 sample plan item 是 closed discriminated variants；不适用字段禁止出现：

- `QUERY_REPETITION_ITEM`：`{sample_id:ID,kind:"query-repetition",workload:WORKLOAD,backend:BACKEND,
  repetition:INT[0,5],phase:"measured",query_warmup_count:INT[20,100],query_measured_count:INT[200,1000],
  provisioning_included:true}`。一个 item 是一个 backend×logical repetition root，先按同一 frozen manifest 执行该 repetition 的全部 warmup，再执行全部 measured query；warmup 不另建 item。
- `BUILD_ITEM`：`{sample_id:ID,kind:"build",workload:WORKLOAD,backend:BACKEND,repetition:INT[0,5],phase:enum[warmup,measured],
  provisioning_included:true}`。每 workload/backend 恰有一个 warmup item；measured build item 与 logical repetition 一一对应，禁止 R² multiplication。
- `LIFECYCLE_ITEM`：`{sample_id:ID,kind:"lifecycle",workload:WORKLOAD,backend:BACKEND,operation:LIFECYCLE_OPERATION,
  repetition:INT[0,5],phase:enum[warmup,measured],within_repetition_ordinal:INT[0,19],counterbalance_arm:enum[AB,BA],
  provisioning_included:true}`。每 operation/backend 恰有一个 warmup item；每 logical repetition 有固定 M 个 measured item，ordinal 为
  `0..M-1`，与 operation/backend/repetition 唯一确定。AB/BA 只记录 backend order assignment。
- `FAULT_ITEM`：`{sample_id:ID,kind:"fault",workload:WORKLOAD,backend:BACKEND,fixture_id:FAULT_FIXTURE_ID,
  fixture_instance_id:ID,fixture_instance_ordinal:INT[0,2],probe_count:INT[10,20],phase:"measured",repetition:INT[0,0],
  provisioning_included:true}`。fault instance 由 registry 的 applicability 唯一决定，不乘 backend 或 query repetition；backend 固定为
  `lancedb-embedded-exact`，仅代表 candidate injection target。

`SAMPLE_PLAN_ITEM` is the discriminated union above. Its sample-ID preimage contains every identity key. Define
`arm(w,r)="AB"` for even r and `"BA"` for odd r. For lifecycle items `counterbalance_arm=arm(workload,repetition)` and
`LP(counterbalance_arm)` appears immediately after `LP(decimal(repetition))`; other variants use `LP("")` there. Warmup
lifecycle identity uses `repetition=0,within_repetition_ordinal=0` and its backend field disambiguates the two items; measured
ordinals are exactly the declared per-repetition range. The complete derivation is
`"s-"+SHA256(LP("sa-m8-sample-id-v1")||LP(kind)||LP(workload)||LP(backend)||LP(phase)||LP(operation-or-empty)||
LP(fixture_instance_id-or-empty)||LP(decimal(repetition))||LP(counterbalance-arm-or-empty)||
LP(decimal(within_repetition_ordinal-or-zero)))`. Every variant tuple and every resulting sample ID is globally unique across
all four inventory arrays; collision fails input freeze, with no seed substitution.

计数公式严格为：
`query_items(w)=2×logical_repetitions(w)`；`build_items(w)=2×(1+logical_repetitions(w))`；
`lifecycle_items(w)=2×7×(1+logical_repetitions(w)×lifecycle_measured_per_operation_backend(w))`；
`fault_items(w)=applicable_registry_instance_count(w)`；`planned_items(w)=query_items(w)+build_items(w)+lifecycle_items(w)+fault_items(w)`。

| workload | query | build | lifecycle | fault | planned |
| --- | ---: | ---: | ---: | ---: | ---: |
| `1k-correctness` | 12 | 14 | 1,694 | 48 | 1,768 |
| `10k-single-user` | 12 | 14 | 854 | 0 | 880 |
| `100k-capacity` | 8 | 10 | 350 | 8 | 376 |
| `100k-filtered` | 8 | 10 | 350 | 0 | 368 |
| **total** | **40** | **48** | **3,248** | **56** | **3,392** |

`sa.m8.sample-inventory.v1.payload` exact fields：
`{query_items:A<QUERY_REPETITION_ITEM;40..40;order=key(workload,backend,repetition,sample_id);unique=key(workload,backend,repetition)>,
build_items:A<BUILD_ITEM;48..48;order=key(workload,backend,phase,repetition,sample_id);unique=key(workload,backend,phase,repetition)>,
lifecycle_items:A<LIFECYCLE_ITEM;3248..3248;order=key(workload,backend,operation,phase,repetition,within_repetition_ordinal,sample_id);unique=key(workload,backend,operation,phase,repetition,within_repetition_ordinal)>,
fault_items:A<FAULT_ITEM;56..56;order=key(workload,fixture_id,fixture_instance_ordinal,fixture_instance_id,sample_id);unique=key(fixture_instance_id)>,
observed:A<SAMPLE_OBS;0..3392;order=key(sample_id,status,duration_ns,child_exit_code);unique=key(sample_id)>,
not_run_gate_stop:A<{sample_id:ID,trigger:enum[L0,L1,L2,L3,L4],stable_code:"NOT_RUN_GATE_STOP"};0..3392;order=key(sample_id,trigger,stable_code);unique=key(sample_id)>,
valid_ids:A<ID;0..3392;order=value;unique=value>,invalid_ids:A<ID;0..3392;order=value;unique=value>,
warmup_sample_ids:A<ID;0..3392;order=value;unique=value>,measured_sample_ids:A<ID;0..3392;order=value;unique=value>}`。

`planned` is the typed union of the four item arrays, not a separately serialized field; its exact length is 3,392. This split makes
operation and fixture identity part of the normative order/uniqueness proof rather than trusting an opaque `sample_id`.
`SAMPLE_OBS` exact fields：`{sample_id:ID,status:enum[completed,failed,timed-out,aborted],duration_ns:INT[0,9223372036854775807],timeout_s:INT[1,7200],
child_exit_code:INT[-2147483648,2147483647],stable_code:RESULT_CODE,result_ref:REF}`；`status=completed` iff `stable_code=NONE`；其他 status 必须使用 status-map 声明的 failure `STABLE_CODE`。not-run 不产生 observation，且每个 planned item
恰好进入 observed 或 not_run，二者不相交。`valid_ids ∪ invalid_ids=observed.sample_id` 且 `valid_ids ∩ invalid_ids=∅`；`observed.sample_id ∩ not_run_gate_stop.sample_id=∅`、`valid_ids ∩ not_run_gate_stop.sample_id=∅`、`invalid_ids ∩ not_run_gate_stop.sample_id=∅`；`valid_ids ∪ invalid_ids ∪ not_run_gate_stop.sample_id=planned.sample_id`；每个 gate stop 必须逐项生成 `NOT_RUN_GATE_STOP`，其 trigger 必须是首个失败层且禁止后续层/报告声称已执行。
`warmup_sample_ids` 与 `measured_sample_ids` 按 variant phase 精确划分；query-repetition item 归入 measured，而其 query warmup observations
仍嵌在 root 内，不能伪造为独立 planned sample。gate stop 后所有下游 item 按 sample identity 逐项写入 `not_run_gate_stop`，不得省略或压缩为计数。

provisioning/build/lifecycle/fault 的时间不进入 query latency population；provisioning 与 query timing 必须分别记录。每个 item 只允许一次
observed 或 not-run 结果，abort/invalid 也必须留下对应 observation；未执行项目不得写入 valid measured data。

## 6. Result schemas

### 6.1 Layer、observations、fault 与 execution

Control-evidence artifacts are closed, typed, and independently canonicalized; each is referenced by exactly one
`control_evidence_refs` field and is never represented only by prose or a scalar summary:

- `sa.m8.environment-evidence.v1.payload`：`{capture_phase:enum[preflight,post-child-exit],os:"windows-11",kernel:"10.0.26200",cpu:ASCII[1,128],physical_cores:INT[1,256],logical_processors:INT[1,512],physical_ram_bytes:INT[1,1099511627776],python:ASCII[1,64],locale:ASCII[1,64],timezone:ASCII[1,128],network_connections:INT[0,0],listeners:INT[0,0],candidate_service_processes:INT[0,0],api_values:A<{api:enum[GetSystemInfo,GlobalMemoryStatusEx,GetLogicalProcessorInformationEx,GetLocaleInfoEx,GetTimeZoneInformation,GetExtendedTcpTable],value:ASCII[1,4096]};6..6;order=key(api);unique=key(api)>}`。
- `sa.m8.resource-watchdog-evidence.v1.payload`：`{sample_id:ID,capture_ordinal:INT[0,10000000],captured_at:TS,process_rss_bytes:INT[0,1099511627776],candidate_peak_rss_delta_bytes:INT[0,3221225472],free_disk_bytes:INT[0,1099511627776],sample_root_bytes:INT[0,8589934592],aggregate_root_bytes:INT[0,17179869184],file_count:INT[0,100000],process_count:INT[0,16],handle_count:INT[0,256],log_bytes:INT[0,536870912],remaining_deadline_s:INT[0,2956230],network_connections:INT[0,0],listeners:INT[0,0],api_values:A<{api:enum[GetProcessMemoryInfo,GetProcessHandleCount,GetDiskFreeSpaceExW,NtQueryDirectoryFile],value:ASCII[1,4096]};4..4;order=key(api);unique=key(api)>}`。
- `sa.m8.process-inventory-evidence.v1.payload`：`{capture_phase:enum[preflight,post-child-exit],processes:A<{pid:INT[0,4294967295],parent_pid:INT[0,4294967295],image_name:ASCII[1,260],image_sha256:HEX64,allowlisted:BOOL,service_process:BOOL};0..16;order=key(pid);unique=key(pid)>,api_values:A<{api:enum[CreateToolhelp32Snapshot,Process32NextW,QueryFullProcessImageNameW],value:ASCII[1,4096]};3..3;order=key(api);unique=key(api)>}`。
- `sa.m8.network-inventory-evidence.v1.payload`：`{capture_phase:enum[preflight,post-child-exit],connections:A<{local:ASCII[1,128],remote:ASCII[1,128],state:enum[CLOSED,LISTENING,SYN_SENT,SYN_RECEIVED,ESTABLISHED,FIN_WAIT1,FIN_WAIT2,CLOSE_WAIT,CLOSING,LAST_ACK,TIME_WAIT,DELETE_TCB],owner_pid:INT[0,4294967295]};0..0;order=key(local,remote,state,owner_pid);unique=key(local,remote,state,owner_pid)>,api:"GetExtendedTcpTable",outbound_attempts:INT[0,0]}`。
- `sa.m8.interposition-ledger-evidence.v1.payload`：`{resolver_policy:"frozen-import-table-no-dynamic-resolution",symbols:A<INTERPOSITION_SYMBOL;14..14;order=key(module,symbol);unique=key(module,symbol)>,operation_bindings:A<{operation_id:CONTAINMENT_OPERATION_ID,symbol:enum[NtCreateFile,NtOpenFile,NtReadFile,NtWriteFile,FlushFileBuffers,NtQueryInformationFile,NtQuerySecurityObject,NtSetInformationFile,NtClose,CreateProcessW,TerminateProcess,GetExtendedTcpTable,WSAConnect,connect],wrapper:ID};20..20;order=key(operation_id);unique=key(operation_id)>,unlisted_calls:INT[0,0],dynamic_resolution_used:false}`。

All five artifacts use the complete canonical envelope rules in §2.1, have `additionalProperties=false`, and their
REF digest covers the complete envelope bytes. `api_values.value` is the canonical serialized return value, not an
untyped prose assertion; the validator checks the declared API set, cardinality, capture phase, and zero predicates.


`sa.m8.layer-record.v1.payload` is a closed discriminated union:

- PASS: `{layer_id:LAYER,previous_layer_record:REF,required_gate_record:REF,coordinator_source_sha256:HEX64,status:"PASS",
  started_at:TS,finished_at:TS,artifact_refs:A<REF;1..32;order=key(logical_name,schema_id,sha256);unique=key(logical_name)>,
  stable_code:RESULT_CODE,threshold_failures:A<TECH_GATE_ID;0..26;order=value;unique=value>}`;
- FAIL: `{layer_id:LAYER,previous_layer_record:REF,required_gate_record:REF,coordinator_source_sha256:HEX64,status:"FAIL",
  started_at:TS,finished_at:TS,artifact_refs:A<REF;1..32;order=key(logical_name,schema_id,sha256);unique=key(logical_name)>,
  stable_code:STABLE_CODE,threshold_failures:A<TECH_GATE_ID;0..0;order=value;unique=value>,pending_terminal:enum[ABORTED_PREFLIGHT,
  ABORTED_RUNTIME,INVALID_PROTOCOL_DEVIATION],abort_cleanup_authorization_ref:REF}`.

`required_gate_record` is exact P6; threshold failures under complete raw evidence never cause FAIL. Hard safety, integrity,
resource or protocol failures alone use FAIL. `coordinator_source_sha256` equals the coordinator allowlist digest. L0 previous
REF is the genesis layer; each later PASS/FAIL points to the immediately preceding PASS. The layer artifact does not contain a
writer-result REF. Its out-of-band writer result commits the final layer bytes digest, eliminating a digest cycle. FAIL forbids
later layers and P7 but authorizes the abort-report and abort-cleanup transitions below through P4/P6 standing authority.

Each observation artifact is closed and source-identifiable:

- `sa.m8.query-observations.v1.payload`：`{sample_id:ID,workload:WORKLOAD,backend:BACKEND,repetition:INT[0,5],
  timeout_s:INT[5,5],observations:A<{query_id:ID,role:QUERY_ROLE,query_kind:QUERY_KIND,query_class:QUERY_CLASS,
  phase:OBS_PHASE,ordinal:INT[0,1099],duration_ns:INT[0,5000000000],status:OBS_STATUS,stable_code:RESULT_CODE,
  candidate_ids:A<ID;0..5;order=ordinal;unique=value>,candidate_scores_f64_le_hex:A<HEX16;0..5;order=ordinal;unique=not-applicable>};
  220..1100;order=key(phase,ordinal,query_id);unique=key(phase,query_id)>}`。warmup and measured counts equal the sample plan; IDs and role fields equal the frozen manifest. Candidate arrays have equal length; timed-out/failed/aborted/not-run rows use both empty. Once a query root starts, its artifact emits one row for every manifest ordinal: completed rows cover the executed prefix; the currently attempted query, if interrupted, is `status=aborted` with the exact causal `STABLE_CODE`; every later unattempted ordinal is `status=not-run` with `stable_code=NOT_RUN_GATE_STOP`. Both suffix variants have zero duration. A query root stopped before child start produces no query-observation artifact and exists only in sample inventory `not_run_gate_stop`. Thus query observation cardinality remains exactly the frozen manifest count whenever its root observation exists, and no missing suffix is inferred.
- `sa.m8.build-observation.v1.payload`：`{sample_id:ID,workload:WORKLOAD,backend:BACKEND,repetition:INT[0,5],phase:OBS_PHASE,
  duration_ns:INT[0,7200000000000],timeout_s:INT[120,1800],status:enum[completed,failed,timed-out,aborted],stable_code:RESULT_CODE,
  canonical_input_bytes:INT[0,2147483648],index_bytes:INT[0,8589934592]}`。`status=aborted` requires the exact causal failure `STABLE_CODE`, may appear only after the item started, and must not use `NOT_RUN_GATE_STOP`; `canonical_input_bytes=0` is allowed only when that started item was aborted before input materialization. An item stopped before start produces no build-observation artifact and exists only in sample inventory `not_run_gate_stop`. `status=completed` iff `stable_code=NONE`; failed/timed-out rows require their declared stable failure code.
- `sa.m8.lifecycle-observation.v1.payload`：`{sample_id:ID,workload:WORKLOAD,backend:BACKEND,operation:LIFECYCLE_OPERATION,
  repetition:INT[0,5],phase:OBS_PHASE,within_repetition_ordinal:INT[0,19],counterbalance_arm:enum[AB,BA],
  duration_ns:INT[0,2400000000000],timeout_s:INT[60,2400],status:enum[completed,failed,timed-out,aborted],stable_code:RESULT_CODE,
  operation_pass:BOOL,query_verify_pass:BOOL,reopen_pass:BOOL,rollback_required:BOOL,rollback_pass:BOOL}`。`status=aborted` requires the exact causal failure `STABLE_CODE`, may appear only after the item started, and must not use `NOT_RUN_GATE_STOP`; all pass booleans must be `false` for an aborted row. An item stopped before start produces no lifecycle-observation artifact and exists only in sample inventory `not_run_gate_stop`. `status=completed` iff `stable_code=NONE`; failed/timed-out rows require their declared stable failure code.
- `sa.m8.fault-fixture-receipt.v1.payload`：`{registry_ref:REF,status_map_ref:REF,sample_id:ID,fixture_instance_id:ID,
  fixture_id:FAULT_FIXTURE_ID,fixture_instance_ordinal:INT[0,2],workload:WORKLOAD,backend:"lancedb-embedded-exact",
  mutation_sha256:HEX64,injection_point:FAULT_INJECTION_POINT,precondition:CODE,precondition_visible:BOOL,
  probe_kind:enum[query-assertion,metadata-assertion,launcher-assertion,network-assertion],probe_count:INT[10,20],
  passed_probe_count:INT[0,20],expected_codes:A<{phase:enum[preflight,runtime,cleanup],stable_code:STABLE_CODE};1..3;
  order=key(phase);unique=key(phase)>,actual_codes:A<{phase:enum[preflight,runtime,cleanup],stable_code:STABLE_CODE};1..3;
  order=key(phase);unique=key(phase)>,candidate_accessed:BOOL,postcondition:CODE,postcondition_pass:BOOL,
  reopen_required:BOOL,reopen_pass:BOOL,rollback_required:BOOL,rollback_pass:BOOL}`。

Observation `sample_id` and all identity fields must equal exactly one sample inventory item. `duration_ns <= timeout_s×1000000000` for
completed/failed; timed-out rows use the exact timeout duration and `*_TIMEOUT` stable code. Timed-out/failed observations never enter valid
latency percentiles or correctness numerators and increment their dedicated counts. A root-level SAMPLE_OBS `result_ref` resolves to the applicable
observation artifact; query roots contain the full query-observation array.

Metric schemas are mechanically recomputable:

- `QUERY_METRIC`：`{workload:WORKLOAD,backend:BACKEND,repetition:INT[0,5],query_class:QUERY_CLASS,
  source_sample_id:ID,source_query_ids:A<ID;1..1000;order=value;unique=value>,measured_count:INT[1,1000],completed_count:INT[0,1000],
  timeout_count:INT[0,1000],failed_count:INT[0,1000],p50_ns:INT[0,5000000000],p95_ns:INT[0,5000000000],p99_ns:INT[0,5000000000],
  recall_at_1:DEC,recall_at_3:DEC,recall_at_5:DEC,mrr:DEC,no_hit_precision:DEC}`. For an inapplicable aggregate, the value is the closed sentinel `"-1"`: Recall/MRR are applicable only to unfiltered/filtered, and no-hit precision only to deny. `100k-capacity` has no filtered row.
- `QUERY_REPETITION_RATIO`：`{workload:WORKLOAD,backend:BACKEND,query_class:QUERY_CLASS,source_sample_ids:A<ID;4..6;order=value;unique=value>,
  repetition_count:INT[4,6],max_p95_ns:INT[0,5000000000],min_p95_ns:INT[1,5000000000],ratio:DEC}`; `ratio=max_p95_ns/min_p95_ns`
  using exact decimal division rounded half-even to nine fractional digits. Missing/zero valid p95 fails the technical gate.
- `BUILD_METRIC`：`{workload:WORKLOAD,backend:BACKEND,phase:OBS_PHASE,source_sample_ids:A<ID;1..6;order=value;unique=value>,
  measured_count:INT[1,6],completed_count:INT[0,6],timeout_count:INT[0,6],failed_count:INT[0,6],p50_ns:INT[0,7200000000000],
  p95_ns:INT[0,7200000000000],p99_ns:INT[0,7200000000000],index_bytes_max:INT[0,8589934592],canonical_input_bytes:INT[1,2147483648]}`。
- `LIFECYCLE_METRIC`：`{workload:WORKLOAD,backend:BACKEND,operation:LIFECYCLE_OPERATION,repetition:INT[0,5],phase:OBS_PHASE,
  counterbalance_arm:enum[AB,BA],source_sample_ids:A<ID;1..20;order=value;unique=value>,measured_count:INT[1,20],completed_count:INT[0,20],
  timeout_count:INT[0,20],failed_count:INT[0,20],success_count:INT[0,20],reopen_required_count:INT[0,20],reopen_pass_count:INT[0,20],
  rollback_required_count:INT[0,20],rollback_pass_count:INT[0,20],p50_ns:INT[0,2400000000000],p95_ns:INT[0,2400000000000],p99_ns:INT[0,2400000000000]}`。

Percentiles use only completed observations and nearest rank `ceil(p×N)` after ascending duration sort; N=0 fails closed and no percentile may
be fabricated. `measured_count=completed_count+timeout_count+failed_count`. Query source IDs exactly partition measured manifest IDs by class for
each repetition. Recall@k is the arithmetic mean of per-query `|candidate[0:d]∩gold[0:d]|/d`, `d=min(k,top_k)`; MRR is mean reciprocal rank
of target; no-hit precision is `empty_candidate_count/deny_measured_count`. All fractions use arbitrary-precision integer numerator/denominator and
half-even nine-digit DEC serialization. Warmup, provisioning, build, lifecycle, fault, failed, and timed-out rows never enter query latency/correctness.

`sa.m8.exact-flat-proof.v1.payload` exact fields：`{backend:BACKEND,workload:WORKLOAD,sample_id:ID,sample_root_target:TARGET,corpus_ref:REF,query_gold_ref:REF,provisioning_child_source_sha256:HEX64,catalog_digest:HEX64,index_inventory_digest:HEX64,query_plan_digest:HEX64,vector_index_count:INT[0,0],ann_index_count:INT[0,0],scalar_secondary_index_count:INT[0,0],search_mode:"exhaustive",distance:"cosine",dimension:INT[512,512],index_kind:"flat/no-vector-index",identity_set_sha256:HEX64,metadata_sha256:HEX64,sentinel_parity:true,provision_build_close_readback_verified:true}`。SQLite proof 必须将 `index_inventory_digest` 与 `query_plan_digest` 绑定到 linear-scan catalog；LanceDB proof 必须绑定 catalog、index inventory 和 explain plan。每个 measured backend/workload/repetition 恰有一个 proof；四类 workload 的 repetition 总数为 20，故 proof 总数恰为 40。`sample_root_target` 必须逐字等于下列唯一导出结果，不得包含任何其他 component，也不得按 run、时钟或随机数命名：

`sample_leaf = "q" + SHA256(LP("sa-m8-sample-root-v1")||LP(corpus_ref.sha256)||LP(query_gold_ref.sha256)||LP(sample_id))` 的完整 64 hex 后缀；
`sample_root_target = TARGET{parent_binding:experiment_parent_binding,components:["samples",sample_leaf],leaf_kind:"directory",leaf_name:sample_leaf}`。

其中 `experiment_parent_binding` 逐字等于 P2 repository binding 的 `experiment_parent_binding` REF，`target()` 逐字等于 §7 的 `PARENT_BINDING` 导出：`components` 从该 binding 的 verified parent handle 起按 `ordinal` 依次 ``child-directory-create``，只有最后一个 component 可在其已不存在时创建。proof 的 `sample_id`、`corpus_ref`、`query_gold_ref` 必须与其闭包到的 query sample item 及 manifest REF 逐项相等，因此 40 个 target 两两互异，且全体 target 恰为 `samples` 目录下 40 个 entry。该 target 必须在 provisioning child 启动前通过 handle identity 与 parent enumeration identity 验证、在 proof 写入前经 readback 复验，且不随 repetition 复用；任何跨 sample root 的 index、cache、已打开 handle 或 mutable state 复用均为 `INVALID_PROTOCOL_DEVIATION`。

`catalog_digest`、`index_inventory_digest` 与 `query_plan_digest` 的 preimage 是 provisioning child 在该 target 内、且在 `build` phase readback 之前所写出的 canonical bytes。三者分别必须是 closed artifacts `sa.m8.catalog-snapshot.v1`、`sa.m8.index-inventory.v1` 和 `sa.m8.query-plan.v1` 的 complete envelope SHA-256；catalog snapshot 按 declared ordinal rows 序列化，index inventory 必须含三个空数组（vector/ann/scalar-secondary），query plan 按 `(statement_ordinal,operator_ordinal,field_name)` 排序并携带 backend 与 `search_mode`。`catalog_digest` 承诺已打开的 schema/table catalog，`index_inventory_digest` 承诺该 catalog 的完整 index inventory，`query_plan_digest` 承诺检索路径的 explain output。三者必须逐字等于该 sample 的 `sa.m8.build-observation.v1` 所绑定的同一 provisioning 结果，且其 canonical bytes 作为 evidence 由 execution report 的 gate `evidence_refs` 闭包引用；只有 digest 而无该绑定链即为 `INVALID_PROTOCOL_DEVIATION`。

`sa.m8.catalog-snapshot.v1.payload` exact fields：`{backend:BACKEND,sample_id:ID,schemas:A<{schema_name:ID,tables:A<{table_name:ID,columns:A<{ordinal:INT[0,255],name:ID,type:ASCII[1,128],nullable:BOOL};1..256;order=key(ordinal);unique=key(ordinal)>};0..256;order=key(table_name);unique=key(table_name)>};0..256;order=key(schema_name);unique=key(schema_name)>,row_count:INT[0,1000000000],catalog_order:"declared-ordinal"}`。
`sa.m8.index-inventory.v1.payload` exact fields：`{backend:BACKEND,sample_id:ID,vector_indexes:A<{name:ID,table_name:ID};0..0;order=key(name);unique=key(name)>,ann_indexes:A<{name:ID,table_name:ID};0..0;order=key(name);unique=key(name)>,scalar_secondary_indexes:A<{name:ID,table_name:ID};0..0;order=key(name);unique=key(name)>,inventory_order:"declared-ordinal"}`。
`sa.m8.query-plan.v1.payload` exact fields：`{backend:BACKEND,sample_id:ID,search_mode:"exhaustive",statements:A<{statement_ordinal:INT[0,255],operators:A<{operator_ordinal:INT[0,255],field_name:ID,operation:enum[scan,filter,sort,limit,vector-distance]};1..256;order=key(operator_ordinal,field_name);unique=key(operator_ordinal,field_name)>};1..256;order=key(statement_ordinal);unique=key(statement_ordinal)>,plan_order:"statement-operator-field"}`。所有三个 envelope 均 `additionalProperties=false`，并要求 schema_id、logical_name、payload 的完整 canonical envelope。proof 的 source refs、digest 和 count 必须在 execution report、verification report 和 package 中闭包一致；缺失、重复或跨 sample root 复用均为 `INVALID_PROTOCOL_DEVIATION`。

`sa.m8.execution-report.v1.payload` exact fields：

- `identity_ref:REF`、`binding_ref:REF`；
- `authorization_refs:A<REF;7..7;order=key(logical_name,schema_id,sha256);unique=key(logical_name)>`，覆盖 P0–P6；
- `genesis_layer_ref:REF`，必须为 `schema_id=sa.m8.genesis-layer.v1` 且逐字闭包到 L0 的 `previous_layer_record`；
- `environment:{os:"windows-11",kernel:"10.0.26200",cpu:"amd-ryzen-7-7840h",physical_cores:INT[8,8],logical_processors:INT[16,16],
  physical_ram_bytes:INT[16309932032,16309932032],python:"cpython-3.11.9-x64",launcher_sha256:HEX64,locale:ASCII[1,64],timezone:ASCII[1,64],
  network_connections:INT[0,0],listeners:INT[0,0],candidate_service_processes:INT[0,0]}`；
- `input_refs:{dependency_lock:REF,source_inventory:REF,corpus_manifests:A<REF;4..4;order=key(logical_name,schema_id,sha256);unique=key(logical_name)>,
  query_gold_manifests:A<REF;4..4;order=key(logical_name,schema_id,sha256);unique=key(logical_name)>,sample_plans:A<REF;4..4;order=key(logical_name,schema_id,sha256);unique=key(logical_name)>,
  sample_inventory:REF,fault_registry:REF,status_map:REF,deadline_plan:REF,child_allowlist:REF}`；
- `control_evidence_refs:{environment:REF,resource_watchdog:REF,process_inventory:REF,network_inventory:REF,interposition_ledger:REF}`；
- `observation_refs:A<REF;0..3392;order=key(logical_name,schema_id,sha256);unique=key(logical_name)>`；
- `exact_flat_proof_refs:A<REF;0..40;order=key(logical_name,schema_id,sha256);unique=key(logical_name)>`；`execution_disposition=EXECUTION_FINISHED_PENDING_VERIFICATION` 时必须恰为 40，abort/invalid 时必须恰为失败前已完成并 durable-readback 的 proof prefix，未完成 sample 不得伪造 proof；每个已有 proof 必须闭包到相应 backend/workload/repetition sample；
- `layer_refs:A<REF;0..5;order=key(logical_name,schema_id,sha256);unique=key(logical_name)>`，非 abort report 必须恰为 L0–L4 五层的逐字 REF；
- `query_metrics:A<QUERY_METRIC;0..112;order=key(workload,backend,repetition,query_class);unique=key(workload,backend,repetition,query_class)>`；
- `query_repetition_ratios:A<QUERY_REPETITION_RATIO;0..22;order=key(workload,backend,query_class);unique=key(workload,backend,query_class)>`；
- `build_metrics:A<BUILD_METRIC;0..16;order=key(workload,backend,phase);unique=key(workload,backend,phase)>`；
- `lifecycle_metrics:A<LIFECYCLE_METRIC;0..336;order=key(workload,backend,operation,repetition,phase);unique=key(workload,backend,operation,repetition,phase)>`；
- `resource_metrics:{candidate_peak_rss_delta_bytes:INT[0,3221225472],sqlite_peak_rss_delta_bytes:INT[0,3221225472],dependency_bytes:INT[0,2147483648],max_sample_root_bytes:INT[0,8589934592],aggregate_root_peak_bytes:INT[0,17179869184],max_files:INT[0,100000],max_processes:INT[0,16],max_handles:INT[0,256],log_bytes:INT[0,536870912],report_bytes:INT[0,268435456],package_bytes:INT[0,268435456],receipt_bytes:INT[0,16777216],dependency_package_bytes:INT[0,2147483648],dependency_cache_bytes:INT[0,2147483648],dependency_size_digest:HEX64,dependency_extracted_size_digest:HEX64,dependency_cache_size_digest:HEX64}`；
- `fault_results:A<REF;0..56;order=key(logical_name,schema_id,sha256);unique=key(logical_name)>`；
- `gates:A<TECH_GATE_RESULT;26..26;order=key(gate_id);unique=key(gate_id)>`；
- `violations:A<{violation_id:ID,code:STABLE_CODE,severity:enum[error,warning],sample_id:ID,message:UTF8[1,1024]};0..10000;order=key(code,sample_id,violation_id);unique=key(violation_id)>`；
- `sample_cleanup:{residual_entries:INT[0,1000000],residual_bytes:INT[0,17179869184],open_handles:INT[0,100000],child_processes:INT[0,16]}`；
- `execution_disposition:enum[EXECUTION_FINISHED_PENDING_VERIFICATION,ABORTED_PREFLIGHT,ABORTED_RUNTIME,INVALID_PROTOCOL_DEVIATION]`。

A non-abort report has exact metric cardinalities implied by frozen plans and observations. Abort/invalid reports may have empty metric arrays and
zero counts, but inventory, violations, and disposition must identify every unrun item; no unrun item may appear as measured evidence.

### 6.2 Verification report

`sa.m8.verification-report.v1.payload`：
`{execution_report:REF,genesis_layer_ref:REF,control_evidence_refs:{environment:REF,resource_watchdog:REF,process_inventory:REF,network_inventory:REF,interposition_ledger:REF},verifier_source_sha256:HEX64,exact_flat_proof_refs:A<REF;40..40;order=key(logical_name,schema_id,sha256);unique=key(logical_name)>,recomputed_refs:A<REF;29..29;order=key(logical_name,schema_id,sha256);unique=key(logical_name)>,
inventory_counts:{planned:INT[1,3392],observed:INT[0,3392],valid:INT[0,3392],invalid:INT[0,3392],not_run:INT[0,3392]},
recomputed_metrics:A<{metric_id:TECH_GATE_ID,workload:WORKLOAD,backend:BACKEND,value:DEC,source_count:INT[0,10000]};1..1000;
order=key(workload,backend,metric_id);unique=key(workload,backend,metric_id)>,
gate_results:A<TECH_GATE_RESULT;26..26;order=key(gate_id);unique=key(gate_id)>,
expected_pre_cleanup_disposition:enum[VALID_ADOPTION_ELIGIBLE,VALID_NOT_ADOPTION_ELIGIBLE],
redaction_check:{raw_vectors_absent:true,credentials_absent:true,absolute_user_paths_absent:true,full_environment_absent:true,backend_raw_errors_absent:true}}`。

`recomputed_refs` must be exactly the following 29 logical artifacts: execution report, identity, binding, the seven P0–P6
authorization records, dependency lock, source inventory, four corpus manifests, four query/gold manifests, four sample plans,
sample inventory, fault registry, status map, deadline plan, and child allowlist. The array is serialized in its declared key order;
its length is exactly 29, with no extra or missing REF. Each recomputed metric key must match its source observation rows exactly. A verification report is reachable only from a complete `EXECUTION_FINISHED_PENDING_VERIFICATION` execution report; therefore `exact_flat_proof_refs` has schema cardinality 40, must byte-for-byte equal that execution report's 40 refs, and independently validates one proof per backend/workload/repetition. Abort/invalid reports may contain only a completed proof prefix but never reach P7 and never produce a verification report or durable package. Each typed execution-report gate must satisfy `equation(operands)=actual`,
`expected` must be the frozen predicate RHS, and `passed` must be exactly the boolean result of that comparison. A failed gate must carry the
`STABLE_CODE` declared by the predicate; a passed gate must carry `NONE`. Verification `gate_results` must byte-for-byte equal all 26 execution-gate IDs, booleans, failure-code values, and evidence REF sets. Each evidence_refs array must contain the exact source refs used by the equation; prose-only expected/actual
text or an evidence ref not consumed by the equation is invalid. P7 只读验证 raw evidence；package 和 cleanup receipt 不存在时不得引用。
technical/adoption threshold 未满足但 raw evidence 完整，只能写 `VALID_NOT_ADOPTION_ELIGIBLE`，不得改写为 verification failure；
schema、authorization、digest 或 inventory 偏离才产生 `INVALID_PROTOCOL_DEVIATION`。

### 6.3 Self-contained durable evidence package

`sa.m8.durable-package.v1.payload`：
`{identity_member:PACKAGE_MEMBER_REF,binding_member:PACKAGE_MEMBER_REF,
execution_report_member:PACKAGE_MEMBER_REF,verification_report_member:PACKAGE_MEMBER_REF,
input_members:A<PACKAGE_MEMBER_REF;19..19;order=key(logical_name,schema_id,sha256);unique=key(logical_name)>,
gate_members:A<PACKAGE_MEMBER_REF;9..9;order=key(logical_name,schema_id,sha256);unique=key(logical_name)>,
layer_members:A<PACKAGE_MEMBER_REF;5..5;order=key(logical_name,schema_id,sha256);unique=key(logical_name)>,
fault_members:A<PACKAGE_MEMBER_REF;56..56;order=key(logical_name,schema_id,sha256);unique=key(logical_name)>,
expected_pre_cleanup_disposition:enum[VALID_ADOPTION_ELIGIBLE,VALID_NOT_ADOPTION_ELIGIBLE],
transient_commitments:A<{logical_name:LOGICAL_NAME,schema_id:SCHEMA_ID,sha256:HEX64,reason:"RAW_VECTOR_BYTES_REDACTED"};4..4;order=key(logical_name,schema_id,sha256);unique=key(logical_name)>,
genesis_member:PACKAGE_MEMBER_REF,member_decoded_bytes:INT[1,268435456],proof_members:A<PACKAGE_MEMBER_REF;40..40;order=key(logical_name,schema_id,sha256);unique=key(logical_name)>,redaction:{raw_vectors_absent:true,credentials_absent:true,absolute_user_paths_absent:true,
full_environment_absent:true,backend_raw_errors_absent:true}}`。

19 个 input member 恰为 dependency lock、source inventory、4 corpus manifests、4 query/gold manifests、4 sample plans、sample inventory、fault registry、status map、deadline plan 和 child allowlist；另有且仅有一个 `genesis_member`，其 `schema_id` 必须为 `sa.m8.genesis-layer.v1`，其 logical name、digest 和 bytes 必须等于 execution report 的 genesis-layer REF，且该 member 不计入 19 个 input member。`PACKAGE_MEMBER_REF` 为
`{logical_name:LOGICAL_NAME,schema_id:SCHEMA_ID,sha256:HEX64,bytes_b64:ASCII[4,89478488]}`；`bytes_b64` 使用 RFC 4648
standard alphabet 和 required `=` padding，解码后的 member bytes 必须是对应 canonical artifact，且完整 digest 相等。
`identity_member`/`binding_member` 必须分别匹配 execution report 的 identity/binding REF；`genesis_member` 必须逐字匹配 execution report 与 verification report 的 `genesis_layer_ref`；所有 included REF 必须解析到另一 included
member。40 个 `proof_members` 必须恰为 20 个 workload×repetition arm 上各一个 SQLite proof 与一个 LanceDB proof，并逐字等于 execution/verification report 引用的 exact-flat proofs；observation_refs 不作为独立 package members，而由 execution report 的 canonical bytes 和 gate/layer/fault members 闭包承诺，其 raw observation artifacts 在 cleanup 后不可解引用，package 不得声称包含它们。四个 corpus manifest 的 `corpus_jsonl:JSONL_COMMITMENT` 不是 REF；其 `logical_name/schema_id/sha256` 必须逐项等于
`transient_commitments`，原始 vector JSONL bytes 不得进入 package。package 因此对 P8/P9 决策所需的 sanitized inputs、records、metrics、violations 和 commitments 自含，但不声称
能在 cleanup 后重放 raw benchmark。

P7 必须在 raw root 内生成 canonical execution report 与 verification report，各自不超过 32 MiB；其余 decoded package members
合计不超过 64 MiB，全部 decoded members 合计不超过 128 MiB。外层 package canonical bytes（含 base64）不得超过 256 MiB。
package 是 self-contained write-once artifact，digest 覆盖全部成员 bytes 和 manifest。任何单项或总 cap 在写前预检失败，或
CREATE_NEW/write/flush/close/reopen/canonical/digest 任一步失败，都不得留下可引用 package，必须进入
`VALID_EVIDENCE_NOT_PUBLISHED` 的 nonpublication cleanup 路径；不得通过删减 required member 适配 cap。

### 6.4 Detached cleanup receipt

`sa.m8.cleanup-receipt.v1.payload`（仅适用于已成功写入并 readback 验证的正常 package）：
`{durable_package_sha256:HEX64,identity_ref:REF,cleanup_authorization_refs:A<REF;2..2;order=key(logical_name,schema_id,sha256);unique=key(logical_name)>,receipt_writer_result_ref:REF,receipt_canonical_bytes:INT[1,16777216],before:{entries:INT[0,1000000],bytes:INT[0,17179869184],handles:INT[0,100000],processes:INT[0,16],listeners:INT[0,0],root_exists:BOOL},
attempts:A<{ordinal:INT[0,1000000],operation:enum[close-handle,graceful-terminate,forced-kill,delete-entry,delete-root],target_id:ID,attempted:true,stable_code:STABLE_CODE};1..1000000;order=key(ordinal,operation,target_id,stable_code);unique=key(ordinal)>,
after:{entries:INT[0,1000000],bytes:INT[0,17179869184],handles:INT[0,100000],processes:INT[0,16],listeners:INT[0,0],root_exists:BOOL},
package_readback_verified:true,after_zero:true,final_disposition:enum[VALID_ADOPTION_ELIGIBLE,VALID_NOT_ADOPTION_ELIGIBLE],cleanup_started_at:TS,cleanup_finished_at:TS}`。

正常 receipt schema 只表示 cleanup success，不编码失败 variant：其 `after_zero:true`、after 全零、`root_exists=false`、`package_readback_verified:true` 与有效 package disposition 必须同时成立；任一条件不成立时不得创建可引用 normal receipt，而必须尝试 `sa.m8.cleanup-failure-record.v1`。正常 receipt 的 `durable_package_sha256` 必须等于 write-once package 的完整 digest；`cleanup_authorization_refs` 必须恰为 `[P6,P7A]`；receipt 不包含任何自指字段。独立
close/fsync 后 reopen、canonical parse 和 digest 校验证明 receipt 本身。`target_id` 为 `q` 加
`SHA256(LP("sa-m8-cleanup-target-v1")||LP(parent file ID)||LP(leaf))` 的完整 64 hex 后缀，禁止临时 path 名冒充 ID。
成功时 after 的 entries/bytes/handles/processes/listeners 全为 0 且 root_exists=false，`final_disposition` 等于 package disposition；normal receipt 不存在 failure variant。若任一 success predicate 不成立，则不得创建 normal receipt，状态机必须进入 `CLEANUP_INCOMPLETE` 并按 §6.4 写入 cleanup-failure record；该 failure record 或仅内存 terminal 均不得升级、修复或重解释 package。

`sa.m8.cleanup-failure-record.v1.payload`（当 normal、nonpublication 或 abort cleanup receipt 的 CREATE_NEW/write/flush/close/reopen/readback 失败时，在预先冻结的 failure-receipt target 上尝试 CREATE_NEW 写入；它不证明 cleanup 成功）：
`{identity_ref:REF,branch:enum[normal,nonpublication,abort],trigger:enum[ABORTED_PREFLIGHT,ABORTED_RUNTIME,INVALID_PROTOCOL_DEVIATION,REJECTED_INPUT_AUDIT,REJECTED_RAW_EVIDENCE,VERIFICATION_TIMEOUT,REPORT_TIMEOUT,P7A_REFUSED,PACKAGE_TIMEOUT,PACKAGE_CREATE_FAILED,PACKAGE_WRITE_FAILED,PACKAGE_READBACK_FAILED,PACKAGE_VALIDATION_FAILED,CLEANUP_TIMEOUT,RECEIPT_CREATE_FAILED,RECEIPT_WRITE_FAILED,RECEIPT_READBACK_FAILED,RECEIPT_VALIDATION_FAILED],
pending_terminal:enum[none,ABORTED_PREFLIGHT,ABORTED_RUNTIME,INVALID_PROTOCOL_DEVIATION,REJECTED_INPUT_AUDIT,REJECTED_RAW_EVIDENCE],
cleanup_authorization_refs:A<REF;1..2;order=key(logical_name,schema_id,sha256);unique=key(logical_name)>,attempted_receipt_target:TARGET,
failure_record_target:TARGET,failure_record_writer_result_ref:REF,before:{entries:INT[0,1000000],bytes:INT[0,17179869184],handles:INT[0,100000],processes:INT[0,16],listeners:INT[0,0],root_exists:BOOL},
write_failure_code:STABLE_CODE,receipt_write_attempted:true,cleanup_proven:false,final_disposition:"CLEANUP_INCOMPLETE",created_at:TS}`。
Cross-field combinations are closed：`branch=abort` 只允许 trigger `{ABORTED_PREFLIGHT,ABORTED_RUNTIME,INVALID_PROTOCOL_DEVIATION,REJECTED_INPUT_AUDIT,REJECTED_RAW_EVIDENCE,VERIFICATION_TIMEOUT,REPORT_TIMEOUT}`，且 `pending_terminal` 必须属于非 `none` 的五个 abort terminal；`trigger=VERIFICATION_TIMEOUT` iff `pending_terminal=REJECTED_RAW_EVIDENCE`；`trigger=REPORT_TIMEOUT` iff `pending_terminal=ABORTED_RUNTIME`；其余 trigger 必须逐字等于 `pending_terminal`。authorization refs 在 P6 前恰为 `[P4]`、P6 后恰为 `[P4,P6]`。`branch=normal` 只允许 trigger `{CLEANUP_TIMEOUT,RECEIPT_CREATE_FAILED,RECEIPT_WRITE_FAILED,RECEIPT_READBACK_FAILED,RECEIPT_VALIDATION_FAILED}`，`pending_terminal="none"` 且 authorization refs 恰为 `[P6,P7A]`。`branch=nonpublication` 只允许 trigger `{P7A_REFUSED,PACKAGE_TIMEOUT,PACKAGE_CREATE_FAILED,PACKAGE_WRITE_FAILED,PACKAGE_READBACK_FAILED,PACKAGE_VALIDATION_FAILED,CLEANUP_TIMEOUT,RECEIPT_CREATE_FAILED,RECEIPT_WRITE_FAILED,RECEIPT_READBACK_FAILED,RECEIPT_VALIDATION_FAILED}`，`pending_terminal="none"`；若 `trigger=P7A_REFUSED` 则 authorization refs 恰为 `[P6]`，若是 package failure（含 `PACKAGE_TIMEOUT`）则恰为 `[P6,P7A]`，若是 cleanup/receipt failure 则 refs 必须逐字沿用被替代 nonpublication receipt 本应使用的 `[P6]` 或 `[P6,P7A]`。任何未列 branch/trigger/pending-terminal/ref tuple 都是 schema failure。attempted receipt 和 failure-record target 必须分别逐字等于适用 P4/P7A target，且互异。failure-record writer result 是 out-of-band attestation：它逐字绑定 failure-record target、canonical failure-record bytes、CREATE_NEW 结果和 readback，不得由被证明 bytes 引用自身。
该 failure record 是 `CLEANUP_INCOMPLETE` 的唯一 durable terminal evidence。若 failure record 自身无法独占写入、flush、close、reopen 或 readback，协议仍只在内存状态机中落定 `CLEANUP_INCOMPLETE` 并停止；不得新增、追加或改写 journal、gate record、receipt 或其他替代 artifact，也不得声称已有 durable cleanup evidence。failure-record writer result 仅在 failure record 成功写入并 readback 后存在；失败写入不伪造 result REF。无论 durable record 是否成功，`CLEANUP_INCOMPLETE` 永久无出边。

`sa.m8.abort-cleanup-receipt.v1.payload`（适用于 preflight/runtime abort、protocol-invalid abort 或 P5/P7 rejection 的 abort cleanup）：
`{identity_ref:REF,cleanup_authorization_refs:A<REF;1..2;order=key(logical_name,schema_id,sha256);unique=key(logical_name)>,receipt_writer_result_ref:REF,receipt_canonical_bytes:INT[1,16777216],pending_terminal:oneOf[literal["none"],TERMINAL_STATE],trigger:TRIGGER_LABEL,before:{entries:INT[0,1000000],bytes:INT[0,17179869184],handles:INT[0,100000],processes:INT[0,16],listeners:INT[0,0],root_exists:BOOL},
attempts:A<{ordinal:INT[0,1000000],operation:enum[close-handle,graceful-terminate,forced-kill,delete-entry,delete-root],target_id:ID,attempted:true,stable_code:STABLE_CODE};0..1000000;order=key(ordinal,operation,target_id,stable_code);unique=key(ordinal)>,
after:{entries:INT[0,1000000],bytes:INT[0,17179869184],handles:INT[0,100000],processes:INT[0,16],listeners:INT[0,0],root_exists:BOOL},
retained_refs:A<REF;0..32;order=key(logical_name,schema_id,sha256);unique=key(logical_name)>,after_zero:BOOL,receipt_write_readback_verified:true,final_disposition:enum[ABORTED_CLEANUP_VERIFIED,CLEANUP_INCOMPLETE],cleanup_started_at:TS,cleanup_finished_at:TS}`。
该 variant 不声明 package digest，也不构成 P8/P9 authority。P6 前 `cleanup_authorization_refs` 恰为 `[P4]`，P6 后恰为 `[P4,P6]`，按 schema key order 序列化；不得引用被拒绝的 P5/P7 作为 authority。`ABORTED_CLEANUP_VERIFIED` 仅在 `after_zero=true` 且 after 全部 residual、handle、process、listener 和 root 均为零时允许；
任何残留必须令 `after_zero=false` 且只能为 `CLEANUP_INCOMPLETE`。`trigger` 是该 abort cleanup 的直接原因，`pending_terminal` 是 cleanup 成功时必须逐字落定的最终终态；
`pending_terminal=REJECTED_INPUT_AUDIT` 仅来自 P5 rejection，`pending_terminal=REJECTED_RAW_EVIDENCE` 仅来自 P7 rejection 或
`VERIFICATION_TIMEOUT`，`pending_terminal=ABORTED_RUNTIME` 亦可来自已 durable 写入 root 后的 `REPORT_TIMEOUT`，`pending_terminal=ABORTED_PREFLIGHT`/`ABORTED_RUNTIME`/`INVALID_PROTOCOL_DEVIATION` 必须逐字等于触发该 abort 的层
FAIL `pending_terminal`；cleanup 未 verified 时不得以 `pending_terminal` 落定，`final_disposition=CLEANUP_INCOMPLETE` 永久无出边。

`sa.m8.nonpublication-cleanup-receipt.v1.payload`（适用于 P7 raw evidence 已验证，但 P7A refusal（`NOT_AUTHORIZED` 或 `PUBLICATION_REFUSED`）或 package publication/readback/validation 失败）：
`{execution_report_ref:REF,verification_report_ref:REF,identity_ref:REF,cleanup_authorization_refs:A<REF;1..2;order=key(logical_name,schema_id,sha256);unique=key(logical_name)>,publication_failure:enum[P7A_REFUSED,PACKAGE_CREATE_FAILED,PACKAGE_WRITE_FAILED,PACKAGE_READBACK_FAILED,PACKAGE_VALIDATION_FAILED],
partial_target_deletions:A<{target_id:ID,delete_attempted:true,reopen_not_found:true,stable_code:STABLE_CODE};0..32;order=key(target_id,stable_code);unique=key(target_id)>,
zero_residual_inventory:{entries:INT[0,0],bytes:INT[0,0],handles:INT[0,0],processes:INT[0,0],listeners:INT[0,0],root_exists:false},
receipt_writer_result_ref:REF,receipt_canonical_bytes:INT[1,16777216],package_digest:enum["none"],
receipt_write_readback_verified:true,final_disposition:enum[VALID_EVIDENCE_NOT_PUBLISHED,CLEANUP_INCOMPLETE],cleanup_started_at:TS,cleanup_finished_at:TS}`。
`cleanup_authorization_refs` 必须在 P7A refusal 时恰为 `[P6]`，在 package failure 时恰为 `[P6,P7A]`；它们分别表示 cleanup-only standing authority 与已存在的 P7A authorization，禁止将拒绝的 P7A decision 当作授权；`P7A_REFUSED` 的 failure-record branch=nonpublication 也必须逐字保持 `[P6]`，package failure 则必须保持 `[P6,P7A]`。
否则只能为 `CLEANUP_INCOMPLETE`。该 terminal 不产生 P8/P9 出边；任何未成功写入或 readback 的 package 不得伪造 digest。

## 7. Windows handle-relative / no-follow

containment 的唯一权威是 handle identity；字符串仅可作脱敏诊断。P2 必须冻结 experiment parent 的
`FILE_IDENTITY` 和 `PARENT_BINDING`，P4/P7A 的每个 target 必须拥有独立的 verified parent binding，publication parent
不得仅因位于 experiment parent 外就被默认信任。

父目录从 volume/device root 逐 component 使用 `NtCreateFile` 打开；禁止 absolute-once 让中间 junction/reparse 被跟随。
每次 open/create 使用 `OBJECT_ATTRIBUTES.RootDirectory`、relative `UNICODE_STRING` 和 allowlist 中该 `profile_id` 冻结的 exact
`create_options`（`FILE_OPEN_REPARSE_POINT`、`FILE_SYNCHRONOUS_IO_NONALERT` 与该 `leaf_kind` 的唯一 type flag）；创建只用
`FILE_CREATE`，禁止 `FILE_OPEN_IF`、overwrite、supersede，禁止在同一次 open 同时使用 `FILE_DIRECTORY_FILE` 与
`FILE_NON_DIRECTORY_FILE`。parent share 固定 `READ|WRITE|DELETE`；child access/share、
`OBJ_CASE_INSENSITIVE`、`NtWriteFile` offset=0 的单次完整写、`FlushFileBuffers`、close 顺序和失败码必须在
child allowlist artifact 中逐项冻结，缺项即 preflight abort。

每次 open/create/write/rename/delete/reopen 均复验 volume serial、128-bit file ID、parent enumeration identity、type/tag、
`NumberOfLinks=1` 和 unnamed stream；`FileStreamInformation` 不得出现 named stream。禁止 symlink、junction、mount point、
任何其他 reparse、ADS、hard link、跨卷、case-alias collision 和 identity swap。rename 使用
`NtSetInformationFile(FileRenameInformationEx)` no-replace、同一 verified parent；delete 使用 `NtSetInformationFile(FileDispositionInformationEx)` 的
`DELETE|POSIX_SEMANTICS|IGNORE_READONLY_ATTRIBUTE`，并在 close 后 relative reopen 得 `STATUS_OBJECT_NAME_NOT_FOUND`。

child `TEMP/TMP`、pip cache、Arrow/Lance temp 只有在经审计的 syscall interposition/allowlist wrapper 能保证上述
handle-relative contract 时才允许；否则实现必须在 candidate import 前写 `CONTAINMENT_UNSUPPORTED` 并 `ABORTED_PREFLIGHT`，
不得把库自行的 path open 宣称为 containment。所有 `STATUS_*`、access denied、sharing、collision、disk full、flush
失败均映射为稳定 CODE；执行前为 `ABORTED_PREFLIGHT`，执行中为 `INVALID_PROTOCOL_DEVIATION`，cleanup 失败为
`CLEANUP_INCOMPLETE`。普通 `CreateFileW`、path join、`resolve()` 和 prefix check 永远不是 fallback。

## 8. Closed atomic fault registry and status map

`sa.m8.fault-registry.v1.payload` exact fields：
`{entries:A<FAULT_REGISTRY_ENTRY;16..16;order=key(fixture_id);unique=key(fixture_id)>,total_instances:INT[56,56],
total_probes:INT[1040,1040]}`。
`FAULT_REGISTRY_ENTRY` exact fields：`{fixture_id:FAULT_FIXTURE_ID,mutation:FAULT_FIXTURE_ID,
mutation_preimage_domain:ASCII[1,96],injection_point:FAULT_INJECTION_POINT,
applicability:A<{workload:WORKLOAD,instance_count:INT[1,3],probe_count_per_instance:INT[10,20]};1..2;
order=key(workload);unique=key(workload)>,probe_kind:enum[query-assertion,metadata-assertion,launcher-assertion,network-assertion],
candidate_access_expected:BOOL,precondition:CODE,expected_by_phase:A<{phase:enum[preflight,runtime,cleanup],stable_code:STABLE_CODE};
1..3;order=key(phase);unique=key(phase)>,postcondition:CODE,reopen_required:BOOL,rollback_required:BOOL}`。
`mutation` is a `MUTATION_SPEC`, not an opaque fixture label. For each registry row, `mutation.mutation_id` equals
`fixture_id`; `target_field`, `original_value`, and `replacement_value` are required literal fields in the closed row and
`replacement_value` must differ from `original_value`. `canonical mutation bytes` means the exact canonical UTF-8 bytes of
that `MUTATION_SPEC` object, serialized with `sa-json-c14n-v1`; no implementation-defined encoding, offset, or prose value is
allowed. `mutation_sha256=SHA256(LP(mutation_preimage_domain)||LP(fixture_id)||LP(workload)||LP(decimal(instance_ordinal))||LP(canonical mutation bytes))`.
The expanded fixture receipt repeats the complete `MUTATION_SPEC` and its digest, so an independent verifier can recompute the
preimage without accessing a fixture or source tree.
Fixture instance ID is `fi-` plus
`SHA256(LP("sa-m8-fault-instance-v1")||LP(fixture_id)||LP(workload)||LP(decimal(instance_ordinal)))`; ordinals are `0..instance_count-1`.

The following table freezes all registry values. `1K:3×20` means three instances with twenty probes each;
`100K:1×10` means one instance with ten probes. `pre/runtime[/cleanup]` lists phase-specific stable codes in order.

| fixture_id | injection point | applicability | probe | candidate access | expected codes | reopen | rollback |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `unauthorized-owner` | `input-owner-metadata` | 1K:3×20 | query | true | `OWNER_DENIED/OWNER_DENIED` | false | false |
| `cross-source` | `input-source-metadata` | 1K:3×20 | query | true | `SOURCE_DENIED/SOURCE_DENIED` | false | false |
| `stale-generation` | `input-generation-metadata` | 1K:3×20 | query | true | `STALE_GENERATION/STALE_GENERATION` | false | false |
| `stale-snapshot` | `input-snapshot-metadata` | 1K:3×20 | query | true | `STALE_SNAPSHOT/STALE_SNAPSHOT` | false | false |
| `wrong-dimension` | `input-vector-dimension` | 1K:3×20 | metadata | false | `DIMENSION_MISMATCH/DIMENSION_MISMATCH` | false | false |
| `wrong-vector-profile` | `input-vector-profile` | 1K:3×20 | metadata | false | `VECTOR_PROFILE_MISMATCH/VECTOR_PROFILE_MISMATCH` | false | false |
| `tombstone` | `candidate-tombstone` | 1K:3×20; 100K:1×10 | query | true | `TOMBSTONE_HIDDEN/TOMBSTONE_HIDDEN` | true | false |
| `hard-delete` | `candidate-hard-delete` | 1K:3×20; 100K:1×10 | query | true | `DELETE_HIDDEN/DELETE_HIDDEN/OBJECT_NOT_FOUND` | true | false |
| `partial-build` | `candidate-partial-build` | 1K:3×20; 100K:1×10 | metadata | true | `PARTIAL_BUILD_REJECTED/PARTIAL_BUILD_REJECTED/OBJECT_NOT_FOUND` | true | true |
| `corrupt-manifest` | `manifest-read` | 1K:3×20; 100K:1×10 | metadata | true | `MANIFEST_CORRUPT/MANIFEST_CORRUPT/ROLLBACK_VERIFIED` | true | true |
| `corrupt-index` | `index-read` | 1K:3×20; 100K:1×10 | metadata | true | `INDEX_CORRUPT/INDEX_CORRUPT/ROLLBACK_VERIFIED` | true | true |
| `interrupted-build` | `build-worker` | 1K:3×20; 100K:1×10 | launcher | true | `BUILD_INTERRUPTED/BUILD_INTERRUPTED/ROLLBACK_VERIFIED` | true | true |
| `interrupted-publish` | `publish-worker` | 1K:3×20; 100K:1×10 | launcher | true | `PUBLISH_INTERRUPTED/PUBLISH_INTERRUPTED/ROLLBACK_VERIFIED` | true | true |
| `interrupted-cutover` | `cutover-worker` | 1K:3×20; 100K:1×10 | launcher | true | `CUTOVER_INTERRUPTED/CUTOVER_INTERRUPTED/ROLLBACK_VERIFIED` | true | true |
| `missing-dependency` | `dependency-acquisition` | 1K:3×20 | launcher | false | `DEPENDENCY_MISSING/DEPENDENCY_MISSING` | false | false |
| `outbound-network-or-service-attempt` | `network-egress` | 1K:3×20 | network | false | `OUTBOUND_BLOCKED/OUTBOUND_BLOCKED` | false | false |

Table shorthands map exactly: 1K=`1k-correctness`, 100K=`100k-capacity`; query/metadata/launcher/network append `-assertion`.
Every row's `mutation` equals `fixture_id`; `mutation_preimage_domain` is `sa-m8-fault-<fixture-id>-v1`; `precondition` is
`FAULT_PRECONDITION_VISIBLE`; `postcondition` is `FAULT_POSTCONDITION_VERIFIED`. Codes before the final slash are respectively preflight/runtime;
when a third code exists it is cleanup. Candidate access, reopen, and rollback booleans are exact table values. These expansions are part of the
protocol and leave no prose-selected field.

The registry arithmetic is exact: 1K has `16×3=48` instances and `48×20=960` probes; 100K-capacity has the middle eight rows
`tombstone..interrupted-cutover`, `8×1=8` instances and `8×10=80` probes; the other workloads have zero. Total is 56 instances and
1,040 probes. Fault instances do not multiply by backend or logical repetition. Every FAULT_ITEM and fault receipt must match one and only one
expanded registry instance on fixture ID, instance ID/ordinal, workload, probe count, injection point, and expected codes. The receipt
must additionally equal that expanded row field-for-field on `mutation_sha256`, `precondition_visible`, `candidate_accessed`,
`reopen_required`, `rollback_required`, and the expanded `postcondition`; `expected_codes` must equal the registry's complete
phase-keyed set exactly, and `actual_codes` must contain exactly one entry for every expected phase with the identical stable code.
The input-freeze validator checks only the registry-declared `reopen_required` and `rollback_required` booleans; it does not inspect runtime outcomes. During fault execution, if `reopen_required=true` or `rollback_required=true`, the corresponding `reopen_pass` or `rollback_pass` must be `true`; any
boolean, phase-set, code, ordinal, or digest mismatch is `INVALID_PROTOCOL_DEVIATION` and fails fault verification.

- `sa.m8.deadline-plan.v1.payload`：
  `{workloads:A<{workload:WORKLOAD,query_items:INT[8,12],build_items:INT[10,14],lifecycle_items:INT[350,1694],fault_items:INT[0,48],
  planned_items:INT[368,1768],query_deadline_s:INT[21600,57600],build_deadline_s:INT[1680,18000],
  lifecycle_deadline_s:INT[508200,840000],fault_deadline_s:INT[0,19200],item_total_deadline_s:INT[537240,934800]};
  4..4;order=key(workload);unique=key(workload)>,
  setup_deadline_s:INT[510,510],execution_report_deadline_s:INT[180,180],verification_deadline_s:INT[600,600],package_deadline_s:INT[180,180],
  cleanup_deadline_s:INT[600,600],receipt_readback_deadline_s:INT[120,120],p1_deadline_s:INT[600,600],p2_deadline_s:INT[600,600],p3_deadline_s:INT[600,600],p4_deadline_s:INT[900,900],p5_deadline_s:INT[900,900],p8_deadline_s:INT[600,600],p9_decision_deadline_s:INT[600,600],p7a_administrative_cap_s:INT[0,0],
  execution_deadline_s:INT[2952330,2952330],post_execution_deadline_s:INT[1500,1500],preparation_through_cleanup_deadline_s:INT[2956230,2956230]}`。
  `query_deadline_s`、`build_deadline_s`、`lifecycle_deadline_s`、`fault_deadline_s` 和 `item_total_deadline_s` 是各 workload 的逐项合计，不是重复的 global total；validator 必须按 workload 逐项重算并与下表、P6 record、execution report 和 §9.1 逐字段相等。冻结的四行必须为：`1k-correctness=(21600,1680,508200,5760,537240)`、`10k-single-user=(43200,8400,512400,0,564000)`、`100k-capacity=(57600,18000,840000,19200,934800)`、`100k-filtered=(57600,18000,840000,0,915600)`；tuple 顺序依次为 `(query_deadline_s,build_deadline_s,lifecycle_deadline_s,fault_deadline_s,item_total_deadline_s)`；四行的 item_total 合计为 `2951640`，再加 setup `510` 与 execution report `180` 才得到 P6 `2952330`。
  `p7a_administrative_cap_s` 冻结为 `0`，表示不另加行政 cap。

`sa.m8.status-map.v1.payload` exact fields：
`{entries:A<STATUS_MAP_ENTRY;48..48;order=key(source_domain,phase,raw_status);unique=key(source_domain,phase,raw_status)>,
required_stable_codes:A<STABLE_CODE;48..48;order=value;unique=value>}`。
`STATUS_MAP_ENTRY` exact fields：`{source_domain:enum[ntstatus,win32,backend,watchdog,protocol],phase:enum[preflight,runtime,cleanup],
raw_status:CODE,stable_code:STABLE_CODE}`。`entries` 是以下 48 行的精确有序集合，不是名称集合；序列化时按
`key(source_domain,phase,raw_status)` 排序：

| source_domain | phase | raw_status | stable_code |
| --- | --- | --- | --- |
| `backend` | `preflight` | `DEPENDENCY_MISSING` | `DEPENDENCY_MISSING` |
| `backend` | `preflight` | `DIMENSION_MISMATCH` | `DIMENSION_MISMATCH` |
| `backend` | `preflight` | `VECTOR_PROFILE_MISMATCH` | `VECTOR_PROFILE_MISMATCH` |
| `backend` | `runtime` | `BUILD_INTERRUPTED` | `BUILD_INTERRUPTED` |
| `backend` | `runtime` | `CUTOVER_INTERRUPTED` | `CUTOVER_INTERRUPTED` |
| `backend` | `runtime` | `DELETE_HIDDEN` | `DELETE_HIDDEN` |
| `backend` | `runtime` | `INDEX_CORRUPT` | `INDEX_CORRUPT` |
| `backend` | `runtime` | `MANIFEST_CORRUPT` | `MANIFEST_CORRUPT` |
| `backend` | `runtime` | `OWNER_DENIED` | `OWNER_DENIED` |
| `backend` | `runtime` | `PARTIAL_BUILD_REJECTED` | `PARTIAL_BUILD_REJECTED` |
| `backend` | `runtime` | `PUBLISH_INTERRUPTED` | `PUBLISH_INTERRUPTED` |
| `backend` | `runtime` | `ROLLBACK_VERIFIED` | `ROLLBACK_VERIFIED` |
| `backend` | `runtime` | `SOURCE_DENIED` | `SOURCE_DENIED` |
| `backend` | `runtime` | `STALE_GENERATION` | `STALE_GENERATION` |
| `backend` | `runtime` | `STALE_SNAPSHOT` | `STALE_SNAPSHOT` |
| `backend` | `runtime` | `TOMBSTONE_HIDDEN` | `TOMBSTONE_HIDDEN` |
| `ntstatus` | `cleanup` | `FLUSH_FAILED` | `FLUSH_FAILED` |
| `ntstatus` | `preflight` | `ACCESS_DENIED` | `ACCESS_DENIED` |
| `ntstatus` | `preflight` | `OBJECT_NAME_COLLISION` | `OBJECT_NAME_COLLISION` |
| `ntstatus` | `preflight` | `OBJECT_NOT_FOUND` | `OBJECT_NOT_FOUND` |
| `ntstatus` | `preflight` | `REPARSE_REJECTED` | `REPARSE_REJECTED` |
| `ntstatus` | `preflight` | `SHARING_VIOLATION` | `SHARING_VIOLATION` |
| `protocol` | `cleanup` | `PACKAGE_TIMEOUT` | `PACKAGE_TIMEOUT` |
| `protocol` | `cleanup` | `READBACK_MISMATCH` | `READBACK_MISMATCH` |
| `protocol` | `preflight` | `CONTAINMENT_UNSUPPORTED` | `CONTAINMENT_UNSUPPORTED` |
| `protocol` | `runtime` | `INVALID_PROTOCOL_DEVIATION` | `INVALID_PROTOCOL_DEVIATION` |
| `protocol` | `runtime` | `NOT_RUN_GATE_STOP` | `NOT_RUN_GATE_STOP` |
| `watchdog` | `cleanup` | `CLEANUP_TIMEOUT` | `CLEANUP_TIMEOUT` |
| `watchdog` | `preflight` | `ACQUISITION_TIMEOUT` | `ACQUISITION_TIMEOUT` |
| `watchdog` | `preflight` | `DEPENDENCY_VERIFY_TIMEOUT` | `DEPENDENCY_VERIFY_TIMEOUT` |
| `watchdog` | `preflight` | `GOLD_GENERATION_TIMEOUT` | `GOLD_GENERATION_TIMEOUT` |
| `watchdog` | `preflight` | `INPUT_GENERATION_TIMEOUT` | `INPUT_GENERATION_TIMEOUT` |
| `watchdog` | `preflight` | `LAUNCHER_HEALTH_TIMEOUT` | `LAUNCHER_HEALTH_TIMEOUT` |
| `watchdog` | `preflight` | `PREFLIGHT_TIMEOUT` | `PREFLIGHT_TIMEOUT` |
| `watchdog` | `runtime` | `CHILD_LEAK` | `CHILD_LEAK` |
| `watchdog` | `runtime` | `CHILD_START_TIMEOUT` | `CHILD_START_TIMEOUT` |
| `watchdog` | `runtime` | `DISK_FULL` | `DISK_FULL` |
| `watchdog` | `runtime` | `FAULT_TIMEOUT` | `FAULT_TIMEOUT` |
| `watchdog` | `runtime` | `LIFECYCLE_TIMEOUT` | `LIFECYCLE_TIMEOUT` |
| `watchdog` | `runtime` | `OUTBOUND_BLOCKED` | `OUTBOUND_BLOCKED` |
| `watchdog` | `runtime` | `PROVISION_TIMEOUT` | `PROVISION_TIMEOUT` |
| `watchdog` | `runtime` | `QUERY_REPETITION_TIMEOUT` | `QUERY_REPETITION_TIMEOUT` |
| `watchdog` | `runtime` | `QUERY_TIMEOUT` | `QUERY_TIMEOUT` |
| `watchdog` | `runtime` | `REOPEN_TIMEOUT` | `REOPEN_TIMEOUT` |
| `watchdog` | `runtime` | `REPORT_TIMEOUT` | `REPORT_TIMEOUT` |
| `watchdog` | `runtime` | `TOTAL_DEADLINE` | `TOTAL_DEADLINE` |
| `watchdog` | `runtime` | `VERIFICATION_TIMEOUT` | `VERIFICATION_TIMEOUT` |
| `watchdog` | `runtime` | `WATCHDOG_GAP` | `WATCHDOG_GAP` |

The exact 48 stable-code values are:
`ACCESS_DENIED,ACQUISITION_TIMEOUT,BUILD_INTERRUPTED,CHILD_LEAK,CHILD_START_TIMEOUT,CLEANUP_TIMEOUT,CONTAINMENT_UNSUPPORTED,
CUTOVER_INTERRUPTED,DEPENDENCY_MISSING,DEPENDENCY_VERIFY_TIMEOUT,DELETE_HIDDEN,DIMENSION_MISMATCH,DISK_FULL,FAULT_TIMEOUT,
FLUSH_FAILED,GOLD_GENERATION_TIMEOUT,INDEX_CORRUPT,INPUT_GENERATION_TIMEOUT,INVALID_PROTOCOL_DEVIATION,LAUNCHER_HEALTH_TIMEOUT,
LIFECYCLE_TIMEOUT,MANIFEST_CORRUPT,NOT_RUN_GATE_STOP,OBJECT_NAME_COLLISION,OBJECT_NOT_FOUND,OUTBOUND_BLOCKED,OWNER_DENIED,
PACKAGE_TIMEOUT,PARTIAL_BUILD_REJECTED,PREFLIGHT_TIMEOUT,PROVISION_TIMEOUT,PUBLISH_INTERRUPTED,QUERY_REPETITION_TIMEOUT,QUERY_TIMEOUT,
READBACK_MISMATCH,REPARSE_REJECTED,REOPEN_TIMEOUT,REPORT_TIMEOUT,ROLLBACK_VERIFIED,SHARING_VIOLATION,SOURCE_DENIED,STALE_GENERATION,
STALE_SNAPSHOT,TOTAL_DEADLINE,TOMBSTONE_HIDDEN,VECTOR_PROFILE_MISMATCH,VERIFICATION_TIMEOUT,WATCHDOG_GAP`。`required_stable_codes` 是上述名称按 `value` 排序后的精确集合；表中每个 stable code 恰出现一次。
所有 protocol-generated stop（包括首个失败层之后的 `NOT_RUN_GATE_STOP`）必须命中对应 literal row；不得新增 alias、复用其他
phase 或从 backend prose 推断映射。Unknown raw status、duplicate tuple、absent required code 或未列 alias 均为
`INVALID_PROTOCOL_DEVIATION`；raw backend errors 永不进入 report/package。

## 9. Lifecycle、deadline、预算与 watchdog

唯一成功主链是：
`UNBOUND_DRAFT -> P0_ACCEPTED -> IDENTITY_AUTHORIZED -> BINDING_FROZEN -> TEXT_AUDITED -> PREPARATION_AUTHORIZED ->
INPUTS_PREPARED -> INPUTS_FROZEN -> EXECUTION_AUTHORIZED -> L0_PASSED -> L1_PASSED -> L2_PASSED -> L3_PASSED -> L4_PASSED ->
EXECUTION_RECORDED -> RAW_VERIFIED -> PUBLICATION_AUTHORIZED -> PACKAGE_WRITTEN -> CLEANUP_IN_PROGRESS -> CLEANUP_VERIFIED ->
P8_DECIDED -> P9_RECORDED`。拒绝、失败和 abort 是显式分支：P5 `REJECTED` 或 P7 `REJECTED` 在已有 root/descendant 时进入
`ABORT_CLEANUP_IN_PROGRESS`，否则分别落入 `REJECTED_INPUT_AUDIT` 或 `REJECTED_RAW_EVIDENCE`；P7A
`PUBLICATION_REFUSED` 或 `NOT_AUTHORIZED`，以及 package publication/readback/validation failure，进入
`NONPUBLICATION_CLEANUP_IN_PROGRESS -> VALID_EVIDENCE_NOT_PUBLISHED`；该 cleanup 或 receipt 失败进入
`CLEANUP_FAILURE_RECORD -> CLEANUP_INCOMPLETE`。任何 L0–L4 hard failure 亦进入 `ABORT_CLEANUP_IN_PROGRESS`。

终态为 `TERMINAL_STATE` 的以下完整集合：`P0_NOT_ACCEPTED,NOT_AUTHORIZED,REJECTED_TEXT_AUDIT,REJECTED_INPUT_AUDIT,REJECTED_RAW_EVIDENCE,
ABORTED_PREFLIGHT,ABORTED_RUNTIME,INVALID_PROTOCOL_DEVIATION,ABORTED_CLEANUP_VERIFIED,VALID_EVIDENCE_NOT_PUBLISHED,CLEANUP_INCOMPLETE,
P8_NOT_ADMITTED,P9_RECORDED`；这些是 protocol states，不是 `STABLE_CODE`；`P9_RECORDED` 的 terminal decision 必须是 `SELECT_LANCEDB_EXACT_FLAT` 或
`SELECT_SQLITE_NO_CHANGE`，并分别绑定对应 `selected_backend`；除 `ABORT_CLEANUP_IN_PROGRESS` 与 `CLEANUP_IN_PROGRESS` 的
cleanup-success/failure 分支外，列出的终态无出边、不可覆写、retry、splice 或换 seed；abort terminal 只能在 receipt verified
后落定。
技术阈值失败但 raw evidence 完整且 publication 成功，必须经 P7/P7A/package/cleanup 进入 `VALID_NOT_ADOPTION_ELIGIBLE`，不得错误地进入 abort；P7、verification report、package、normal receipt 与 P8 的 disposition
必须逐字相等；P9 只有在 disposition=`VALID_ADOPTION_ELIGIBLE` 且全部 adoption gates PASS 时才可 `SELECT_LANCEDB_EXACT_FLAT`，否则唯一允许的
decision/backend 是 `SELECT_SQLITE_NO_CHANGE`/`sqlite-linear-exact`。
`VALID_EVIDENCE_NOT_PUBLISHED` 仅表示已验证 raw evidence 在 publication refusal/failure 后完成 nonpublication cleanup；它没有 P8/P9 出边。
所有曾创建 root 或 descendant 的 preflight/runtime/invalid abort 必须先完成 abort cleanup receipt；cleanup 未证实只能终止于 `CLEANUP_INCOMPLETE`。

| current | actor/record | precondition | exact write/operation | success | failure |
| --- | --- | --- | --- | --- | --- |
| UNBOUND_DRAFT | independent reviewer/P0 | exact blob | 仅 P0 record | P0 accepted→P0_ACCEPTED；P0 returned→P0_NOT_ACCEPTED | INVALID_PROTOCOL_DEVIATION |
| P0_ACCEPTED | owner/P1 | P0 digest exact | 仅 identity artifact/record | IDENTITY_AUTHORIZED | P1=NOT_AUTHORIZED→NOT_AUTHORIZED；malformed→INVALID_PROTOCOL_DEVIATION |
| IDENTITY_AUTHORIZED | owner/P2 | identity/history disjoint | 仅 binding artifact/record | BINDING_FROZEN | P2=NOT_AUTHORIZED→NOT_AUTHORIZED；malformed→INVALID_PROTOCOL_DEVIATION |
| BINDING_FROZEN | independent reviewer/P3 | binding exact、非作者 | 仅 text audit/record | TEXT_AUDITED | P3=REJECTED→REJECTED_TEXT_AUDIT；record/schema malformed→INVALID_PROTOCOL_DEVIATION |
| TEXT_AUDITED | owner/P4 | targets/budgets exact | 仅 P4 authorization | PREPARATION_AUTHORIZED | P4=NOT_AUTHORIZED→NOT_AUTHORIZED；malformed 且无 root/descendant→INVALID_PROTOCOL_DEVIATION；malformed 且已有 root/descendant→ABORT_CLEANUP_IN_PROGRESS（pending terminal INVALID_PROTOCOL_DEVIATION） |
| PREPARATION_AUTHORIZED | provisioner/input-generator (P4 authorization) | handle/acquisition PASS | allowlist 内创建 inputs、每个 authorized target 一个 writer result、唯一 preparation result | INPUTS_PREPARED | `ABORT_CLEANUP_IN_PROGRESS`（已有 root/descendant）否则 `ABORTED_PREFLIGHT` |
| INPUTS_PREPARED | independent reviewer/P5 | canonical、断网、candidate 未运行 | 仅 P5 record | INPUTS_FROZEN | REJECTED 且无 root/descendant→`REJECTED_INPUT_AUDIT`；REJECTED 且已有 root/descendant→`ABORT_CLEANUP_IN_PROGRESS`；malformed 且无 root/descendant→`INVALID_PROTOCOL_DEVIATION`；malformed 且已有 root/descendant→`ABORT_CLEANUP_IN_PROGRESS`（pending terminal `INVALID_PROTOCOL_DEVIATION`） |
| INPUTS_FROZEN | owner/P6 | layers/deadlines/child exact | 仅 P6 record | EXECUTION_AUTHORIZED | P6=NOT_AUTHORIZED→NOT_AUTHORIZED；malformed 且无 root/descendant→`INVALID_PROTOCOL_DEVIATION`；malformed 且已有 root/descendant→`ABORT_CLEANUP_IN_PROGRESS`（pending terminal `INVALID_PROTOCOL_DEVIATION`） |
| EXECUTION_AUTHORIZED | coordinator/L0 | launcher/resource/handle PASS | root 内 L0 evidence | L0_PASSED | 无 root/descendant→`ABORTED_PREFLIGHT`；已有 root/descendant→`ABORT_CLEANUP_IN_PROGRESS` |
| L0_PASSED | coordinator/L1 | 1K plan exact | 1K samples | L1_PASSED | ABORT_CLEANUP_IN_PROGRESS |
| L1_PASSED | coordinator/L2 | L1 integrity/safety gates PASS；threshold failures only recorded | 10K samples | L2_PASSED | ABORT_CLEANUP_IN_PROGRESS |
| L2_PASSED | coordinator/L3 | L2 integrity/safety gates PASS；threshold failures only recorded | 100K capacity samples | L3_PASSED | ABORT_CLEANUP_IN_PROGRESS |
| L3_PASSED | coordinator/L4 | L3 integrity/safety gates PASS；threshold failures only recorded | 100K filtered samples | L4_PASSED | ABORT_CLEANUP_IN_PROGRESS |
| L4_PASSED | report-writer/P6 | every planned item is exactly observed or not-run-gate-stop | execution report CREATE_NEW→single write→flush→close→reopen | EXECUTION_RECORDED | `REPORT_TIMEOUT`、report write/flush/close/reopen/readback failure 或 execution-report schema/inventory malformed：无 root/descendant→`ABORTED_PREFLIGHT`，已有 root/descendant→`ABORT_CLEANUP_IN_PROGRESS`（pending terminal `ABORTED_RUNTIME`）；仅当 report bytes 已 durable readback 且 disposition=`EXECUTION_FINISHED_PENDING_VERIFICATION` 时才允许 `INVALID_PROTOCOL_DEVIATION` 作为 report 内容判定 |
| EXECUTION_RECORDED | independent verifier/P7 | raw evidence read-only、actor distinct from coordinator/report-writer | verification report与P7 record | RAW_VERIFIED | REJECTED 且无 root/descendant→`REJECTED_RAW_EVIDENCE`；REJECTED 且已有 root/descendant→`ABORT_CLEANUP_IN_PROGRESS`；malformed 且无 root/descendant→`INVALID_PROTOCOL_DEVIATION`；malformed 且已有 root/descendant→`ABORT_CLEANUP_IN_PROGRESS`（pending terminal `INVALID_PROTOCOL_DEVIATION`） |
| RAW_VERIFIED | owner/P7A | P7 valid、package/receipt TARGET 分别绑定 P2 `purpose=package/normal-receipt` parent binding、source inventory REF 与两个 writer source digest 精确，且两个 digest 互异 | 仅 P7A authorization record | P7A=AUTHORIZED→PUBLICATION_AUTHORIZED；P7A=NOT_AUTHORIZED/PUBLICATION_REFUSED→NONPUBLICATION_CLEANUP_IN_PROGRESS | P7A decision malformed 且无 root/descendant→`INVALID_PROTOCOL_DEVIATION`；malformed 且已有 root/descendant→`ABORT_CLEANUP_IN_PROGRESS`（pending terminal `INVALID_PROTOCOL_DEVIATION`） |
| PUBLICATION_AUTHORIZED | package-writer/P7A authorization | package target absent、package closed/self-contained、package writer 的可执行 source digest 等于 `package_writer_source_sha256` | package CREATE_NEW→single write→flush→close→reopen/readback | PACKAGE_WRITTEN | `PACKAGE_TIMEOUT`、package create/write/readback/validation failure→NONPUBLICATION_CLEANUP_IN_PROGRESS |
| PACKAGE_WRITTEN | cleanup-writer/P7A authorization | package digest/readback exact、receipt target absent、cleanup writer 的可执行 source digest 等于 `cleanup_writer_source_sha256` | close descendants、handle-relative cleanup | CLEANUP_IN_PROGRESS | CLEANUP_FAILURE_RECORD→CLEANUP_INCOMPLETE |
| CLEANUP_IN_PROGRESS | cleanup-writer/P7A authorization | ordered cleanup attempts complete、zero residual proven | normal receipt CREATE_NEW→single write→flush→close→reopen/readback | CLEANUP_VERIFIED | CLEANUP_FAILURE_RECORD→CLEANUP_INCOMPLETE |
| NONPUBLICATION_CLEANUP_IN_PROGRESS | cleanup-writer/P7A cleanup-only authorization | raw evidence verified、every created publication target deleted and reopen-not-found | nonpublication receipt CREATE_NEW→single write→flush→close→reopen/readback | VALID_EVIDENCE_NOT_PUBLISHED | CLEANUP_FAILURE_RECORD→CLEANUP_INCOMPLETE |
| ABORT_CLEANUP_IN_PROGRESS | coordinator/cleanup-writer：P6 前用 P4 standing authorization，P6 后用 P4+P6 | any root/descendant exists after preflight/runtime/invalid or P5/P7 rejection | close descendants、delete root、abort receipt CREATE_NEW→single write→flush→close→reopen/readback | abort receipt 的 `pending_terminal` | CLEANUP_FAILURE_RECORD→CLEANUP_INCOMPLETE |
| CLEANUP_VERIFIED | owner/P8 | reopen package/receipt、zero residual、P7A AUTHORIZED、normal writer results exact | 仅 P8 record | P8=`ADMITTED`→P8_DECIDED；P8=`NOT_ADMITTED`→P8_NOT_ADMITTED | INVALID_PROTOCOL_DEVIATION |
| P8_DECIDED | owner/P9 | P8 已为 `ADMITTED`、package/receipt REF and digest exact、P9 deadline 未超时 | 仅 P9 record | `P9_RECORDED`（decision/backend 见 §9） | deadline 超时→`P8_NOT_ADMITTED`；malformed→`INVALID_PROTOCOL_DEVIATION` |

P4/P5/P6 只允许其表中下一状态；不存在 `request-p7` 跳过 L0–L4。`malformed` 只映射到其所在行的唯一 failure 终态；任何
transition 的 preconditions 不被机械满足时，其唯一结果就是该行 failure 列写明的那个终态，不存在第二解释。
`P7A` 是由 `owner` 签发、`independence.required=false` 的 external authorization record；它既不写 package，也不写 receipt。P7A `AUTHORIZED` 才能授权 package publication；P7A `NOT_AUTHORIZED` 或 `PUBLICATION_REFUSED` 永远不授权 package write，并仅允许已通过 P6 的 cleanup-only/nonpublication path。
P7A `NOT_AUTHORIZED` 与 `PUBLICATION_REFUSED` 都必须使 nonpublication receipt 的 `publication_failure` 恰为 `P7A_REFUSED`，
两条 decision 的 cleanup 分支、receipt schema、target 集合、authority、write 顺序和 disposition 规则完全相同，二者不产生任何差异。
P5/P7 的 root/descendant 存在性判定以 handle-relative parent enumeration 在 rejection 时刻的实际结果为准；不得用 path 或时间推断。
P5/P7 external record 的 `allowed_next_action` 必须逐字反映该判定：无 root/descendant 时为 `stop`，已有 root/descendant 时为 `run-abort-cleanup`；不得以单一静态值掩盖两条分支。
abort cleanup 成功后，落定的终态是 abort receipt `pending_terminal` 字段的逐字值，且该值必须属于 §9 冻结的终态集合。
`AUTHORIZED` 才授权 `package-writer` 写 package，随后授权 `cleanup-writer` 写 normal receipt；`PUBLICATION_REFUSED` 或
`NOT_AUTHORIZED` 只授权 cleanup-writer 执行 nonpublication/abort cleanup 与对应 receipt write，绝不授权 package publication。
cleanup-only/abort cleanup 的 standing authority 来自已通过的 P6/层协调记录，不依赖被拒绝的 P7A；所有 CREATE_NEW/write/flush/close/reopen
均须产生唯一 writer result。
`P7A` payload 的 `source_inventory_ref` 必须逐字等于 P5 的 source-inventory REF；`package_writer_source_sha256` 与
`cleanup_writer_source_sha256` 必须分别逐字等于 source inventory `writer_sources` 中 `package-writer` 与 `cleanup-writer`
条目的冻结摘要且二者互异，且每个条目的 `relative_name` 必须逐字命中 `files` 中同名文件及其 `sha256`。`repository_binding_ref`
必须逐字等于 P2 的 repository-binding REF。
`P7A` record 的 `actor.role` 是 `owner`，而 actual writer 必须以 writer-result 记录 actor role、P7A/P6 authorization REF、target binding、operation outcome
和 source digest。P7A package/normal receipt 只在 P7 verified 且 `P7A=AUTHORIZED` 后出现；P8/P9 唯一 authority 是
`{package_ref,receipt_ref,durable_package_sha256,cleanup_receipt_sha256}`，四者必须逐字且 digest-equal，P9 必须复用 P8 二元组。
P8 只可写 `ADMITTED` 或 `NOT_ADMITTED`；`REJECTED` 不得用于 P8。`P8_DECIDED` 只在 P8=`ADMITTED` 后可达；P8=`NOT_ADMITTED` 直接落定终态 `P8_NOT_ADMITTED`。P9 具有固定 `p9_decision_deadline_s:INT[600,600]`，超时唯一转移为 `P8_NOT_ADMITTED`；因此 `P8_DECIDED` 不可无限期停留。
abort/nonpublication receipt 均不含可供 P8/P9 使用的 package digest，且 `CLEANUP_INCOMPLETE` 永久无出边。

### 9.1 Numeric deadline table

所有 deadline 从 start event 到 completion event，包含 descendants、flush、close、readback 和 terminate/kill；不得以并行
压缩证据时间。以下均为秒，超时后不得 retry：

| operation | deadline / cap | stable code / terminal |
| --- | ---: | --- |
| acquisition overall/connect/read-idle/single wheel | 900 / 10 / 60 / 120 | `ACQUISITION_TIMEOUT` / `ABORTED_PREFLIGHT` |
| launcher health / dependency verify | 30 / 180 | `LAUNCHER_HEALTH_TIMEOUT` / `ABORTED_PREFLIGHT`; `DEPENDENCY_VERIFY_TIMEOUT` / `ABORTED_PREFLIGHT` |
| corpus generation / query-gold generation | 600 / 900 | `INPUT_GENERATION_TIMEOUT` / `ABORTED_PREFLIGHT`; `GOLD_GENERATION_TIMEOUT` / `ABORTED_PREFLIGHT` |
| L0 preflight / report / P7 verification | 300 / 180 / 600 | `PREFLIGHT_TIMEOUT` / `ABORTED_PREFLIGHT`；`REPORT_TIMEOUT` / 无 root/descendant→`ABORTED_PREFLIGHT`、已有 root/descendant→`ABORT_CLEANUP_IN_PROGRESS`（pending terminal `ABORTED_RUNTIME`）；`VERIFICATION_TIMEOUT` / 无 root/descendant→`REJECTED_RAW_EVIDENCE`、已有 root/descendant→`ABORT_CLEANUP_IN_PROGRESS` |
| query repetition 1K/10K/100K | 1,800 / 3,600 / 7,200 | `QUERY_REPETITION_TIMEOUT` / `ABORTED_RUNTIME` |
| build 1K/10K/100K | 120 / 600 / 1,800 | `PROVISION_TIMEOUT` / `ABORTED_RUNTIME` |
| lifecycle 1K/10K/100K | 300 / 600 / 2,400 | `LIFECYCLE_TIMEOUT` / `ABORTED_RUNTIME` |
| fault 1K/100K (including provision) | 120 / 2,400 | `FAULT_TIMEOUT` / `ABORTED_RUNTIME` |
| one query / reopen | 5 / 60 | `QUERY_TIMEOUT` / `REOPEN_TIMEOUT` |
| child startup/graceful/forced | 10 / 5 / 10 | `CHILD_START_TIMEOUT` / `CHILD_LEAK` |
| package write/readback / cleanup/receipt readback | 120 / 60 / 600 / 120 | `PACKAGE_TIMEOUT` / `READBACK_MISMATCH` / `CLEANUP_TIMEOUT` |
| query samples（按 workload item count × per-item upper bound） | `1k:12×1800 + 10k:12×3600 + 100k:16×7200` = 180,000 | `QUERY_REPETITION_TIMEOUT` / `ABORTED_RUNTIME` |
| build samples（warmup + measured；按 workload item count × per-item upper bound） | `1k:14×120 + 10k:14×600 + 100k:20×1800` = 46,080 | `PROVISION_TIMEOUT` / `ABORTED_RUNTIME` |
| lifecycle samples（exact planned item count × operation upper bound） | `1k:1,694×300 + 10k:854×600 + 100k:700×2,400` = 2,700,600 | `LIFECYCLE_TIMEOUT` / `ABORTED_RUNTIME` |
| fault samples（exact registry instance count × probe/provision upper bound） | `1k:48×120 + 100k:8×2,400` = 24,960 | `FAULT_TIMEOUT` / `ABORTED_RUNTIME` |
| launcher + dependency + L0 setup | `30 + 180 + 300` = 510 | `LAUNCHER_HEALTH_TIMEOUT` / `PREFLIGHT_TIMEOUT` |
| execution report | 180 | `REPORT_TIMEOUT` / 无 root/descendant→`ABORTED_PREFLIGHT`、已有 root/descendant→`ABORT_CLEANUP_IN_PROGRESS`（pending terminal `ABORTED_RUNTIME`） |
| P6 execution upper bound | `180,000 + 46,080 + 2,700,600 + 24,960 + 510 + 180` = **2,952,330** | `TOTAL_DEADLINE` / `ABORTED_RUNTIME` |
| post-execution: verification + package/readback + cleanup + receipt readback | `600 + 180 + 600 + 120` = **1,500** | `READBACK_MISMATCH` / `CLEANUP_TIMEOUT` |
| preparation through cleanup upper bound | `900 + 600 + 900 + 2,952,330 + 1,500` = **2,956,230** | `TOTAL_DEADLINE` / `ABORTED_RUNTIME` |

上述是串行 authorization upper bound；所有乘法项均来自冻结 sample inventory、fault registry 和单项上限，不能用 wall-clock 并行掩盖遗漏。
P6 的 `execution_deadline_s` 固定为 `2,952,330`，`post_execution_deadline_s` 固定为 `1,500`，
`preparation_through_cleanup_deadline_s` 固定为 `2,956,230`。不另加未定义的 P7A administrative cap；任何改变 cardinality、operation、fixture 或单项 deadline
都必须同步重算这三个值。

资源 hard caps：sample root 8 GiB（7 GiB 停止新写）、experiment aggregate 16 GiB、parent free 20 GiB、available memory
8 GiB、candidate RSS delta 3 GiB、1 coordinator+1 active child、100,000 files、16 processes、256 handles、512 MiB logs、
256 MiB raw reports、256 MiB package、16 MiB receipt、2 GiB isolated dependency footprint。watchdog 每 1 s 采 RSS、disk、
file/process/handle、network/listener 和 remaining deadline；一次超 cap 立即 stop，连续三次 soft threshold 停止新 sample，
漏采超过 3 s 为 `WATCHDOG_GAP`/`ABORTED_RUNTIME`，不得自动 retry。

## 10. Hard gates、exact/flat proof 与 adoption

SQLite/M7 是 control-plane authority；`sqlite-linear-exact` 是 correctness oracle/fallback，`lancedb-embedded-exact` 是唯一
active candidate。Qdrant、Milvus、ANN、IVF、HNSW、PQ、服务化、云端、并发和真实 100K 质量不在范围；
`bm25-existing-default` 仅为只读 sentinel，不是 BACKEND。

每个 backend/workload/repetition 从同一 frozen corpus/query/gold 在 new-root-per-sample 独立 provision；provision/build/close/readback
与 query timing 分开报告。两端 affinity/thread、query order、warmup、filter、cache boundary 完全相同。LanceDB 每次 build/open/query
必须同时从 catalog、index inventory、query explain plan 证明 `vector_index_count=0,ann_index_count=0,scalar_secondary_index_count=0,
search_mode=exhaustive,distance=cosine,dimension=512,index_kind=flat/no-vector-index`；任一不能机械证明即 stop。

correctness/security hard gates 全部 100%：identity/count/metadata/filter/gold/fault/lifecycle/reopen parity、exact top-k、Recall@1/3/5、
MRR、no-hit precision、unauthorized/cross-source/stale/tombstone/delete/unpublished hit、unexpected error、network/listener/service/
production write 和最终 residual 全为零。10K threshold 为 unfiltered p95≤50ms、p99≤100ms、filtered p95/p99≤75/150ms、build p95≤30s；
100K threshold 为 unfiltered p95≤100ms、p99≤200ms、filtered p95/p99≤150/300ms、build p95≤300s。adoption 另需 100K unfiltered
p95≤0.70×SQLite、filtered p95≤100ms、build p95≤180s、RSS≤2GiB 且无新增默认依赖/服务/网络/权威负担，否则为
`VALID_NOT_ADOPTION_ELIGIBLE`。阈值和 safety deadline 不互相替代。

### 10.1 Closed technical predicate registry

下表是唯一、闭合且规范性的 26-gate registry。`equation` 列的 ASCII 文本必须逐字写入
`TECH_GATE_RESULT.equation`；typed operands 必须按 `name` canonical 排序，字段名、类型、值和数量必须与该行完全相等。
所有行的 `expected` 固定为 JSON boolean `true`，`actual` 是 equation 对 operands 的 boolean 求值，且
`passed=actual`。表中“false code”是 predicate 为 false 时的 `RESULT_CODE`：hard/resource 行使用所列
`STABLE_CODE`；performance/adoption 行使用 `NONE`，因为完整 raw evidence 下的阈值未达标不是执行错误。

证据 selector 是闭合语法：`I1(x)` 只可选择 execution report `input_refs` 中 scalar REF 字段 x；`IA(x)` 只可完整展开 `input_refs` 中 REF-array 字段 x；`O(s)` 是 `observation_refs` 中 envelope `schema_id=s` 的完整集合；`F`、`X`、`L` 分别是完整 `fault_results`、`exact_flat_proof_refs`、`layer_refs`；`C(x)` 是 `control_evidence_refs.x` 的单一 REF。逗号表示有序 union，结果按 REF comparator 重排并去重；空展开、部分展开、额外 REF 或未消费 REF 均非法。selector 只决定 `evidence_refs`，不得替代 equation operand。

| gate_id | class | predicate_id | exact typed operands | exact equation | false code | evidence selector |
| --- | --- | --- | --- | --- | --- | --- |
| `identity-count` | hard | `pred-identity-count-v1` | `actual_count:INT;planned_count:INT=3392` | `actual_count==planned_count` | `INVALID_PROTOCOL_DEVIATION` | `I1(sample_inventory),O(sa.m8.query-observations.v1),O(sa.m8.build-observation.v1),O(sa.m8.lifecycle-observation.v1),F` |
| `metadata-filter-gold` | hard | `pred-metadata-filter-gold-v1` | `filtered_membership_exact:BOOL;metadata_gold_equal:BOOL` | `filtered_membership_exact AND metadata_gold_equal` | `INVALID_PROTOCOL_DEVIATION` | `IA(corpus_manifests),IA(query_gold_manifests),O(sa.m8.query-observations.v1)` |
| `fault-lifecycle` | hard | `pred-fault-lifecycle-v1` | `fault_all_pass:BOOL;lifecycle_all_pass:BOOL` | `fault_all_pass AND lifecycle_all_pass` | `INVALID_PROTOCOL_DEVIATION` | `I1(fault_registry),F,O(sa.m8.lifecycle-observation.v1)` |
| `reopen-parity` | hard | `pred-reopen-parity-v1` | `reopen_all_pass:BOOL;reopen_required_count:INT` | `reopen_required_count>0 AND reopen_all_pass` | `INVALID_PROTOCOL_DEVIATION` | `F,O(sa.m8.lifecycle-observation.v1)` |
| `exact-top-k` | hard | `pred-exact-top-k-v1` | `exact_candidate_set_agreement:DEC` | `exact_candidate_set_agreement==1.000000000` | `INVALID_PROTOCOL_DEVIATION` | `IA(query_gold_manifests),O(sa.m8.query-observations.v1),X` |
| `recall-at-1` | hard | `pred-recall-at-1-v1` | `recall_at_1:DEC` | `recall_at_1==1.000000000` | `INVALID_PROTOCOL_DEVIATION` | `IA(query_gold_manifests),O(sa.m8.query-observations.v1)` |
| `recall-at-3` | hard | `pred-recall-at-3-v1` | `recall_at_3:DEC` | `recall_at_3==1.000000000` | `INVALID_PROTOCOL_DEVIATION` | `IA(query_gold_manifests),O(sa.m8.query-observations.v1)` |
| `recall-at-5` | hard | `pred-recall-at-5-v1` | `recall_at_5:DEC` | `recall_at_5==1.000000000` | `INVALID_PROTOCOL_DEVIATION` | `IA(query_gold_manifests),O(sa.m8.query-observations.v1)` |
| `mrr` | hard | `pred-mrr-v1` | `mrr:DEC` | `mrr==1.000000000` | `INVALID_PROTOCOL_DEVIATION` | `IA(query_gold_manifests),O(sa.m8.query-observations.v1)` |
| `no-hit-precision` | hard | `pred-no-hit-precision-v1` | `no_hit_precision:DEC` | `no_hit_precision==1.000000000` | `INVALID_PROTOCOL_DEVIATION` | `IA(query_gold_manifests),O(sa.m8.query-observations.v1)` |
| `unfiltered-p95` | performance | `pred-unfiltered-p95-v1` | `w100kc_applicable:BOOL=true;w100kc_pass:BOOL;w100kf_applicable:BOOL=true;w100kf_pass:BOOL;w10k_applicable:BOOL=true;w10k_pass:BOOL;w1k_applicable:BOOL=false;w1k_pass:BOOL=true` | `(NOT w1k_applicable OR w1k_pass) AND (NOT w10k_applicable OR w10k_pass) AND (NOT w100kc_applicable OR w100kc_pass) AND (NOT w100kf_applicable OR w100kf_pass)` | `NONE` | `O(sa.m8.query-observations.v1)` |
| `unfiltered-p99` | performance | `pred-unfiltered-p99-v1` | `w100kc_applicable:BOOL=true;w100kc_pass:BOOL;w100kf_applicable:BOOL=true;w100kf_pass:BOOL;w10k_applicable:BOOL=true;w10k_pass:BOOL;w1k_applicable:BOOL=false;w1k_pass:BOOL=true` | `(NOT w1k_applicable OR w1k_pass) AND (NOT w10k_applicable OR w10k_pass) AND (NOT w100kc_applicable OR w100kc_pass) AND (NOT w100kf_applicable OR w100kf_pass)` | `NONE` | `O(sa.m8.query-observations.v1)` |
| `filtered-p95` | performance | `pred-filtered-p95-v1` | `w100kc_applicable:BOOL=false;w100kc_pass:BOOL=true;w100kf_applicable:BOOL=true;w100kf_pass:BOOL;w10k_applicable:BOOL=true;w10k_pass:BOOL;w1k_applicable:BOOL=false;w1k_pass:BOOL=true` | `(NOT w1k_applicable OR w1k_pass) AND (NOT w10k_applicable OR w10k_pass) AND (NOT w100kc_applicable OR w100kc_pass) AND (NOT w100kf_applicable OR w100kf_pass)` | `NONE` | `O(sa.m8.query-observations.v1)` |
| `filtered-p99` | performance | `pred-filtered-p99-v1` | `w100kc_applicable:BOOL=false;w100kc_pass:BOOL=true;w100kf_applicable:BOOL=true;w100kf_pass:BOOL;w10k_applicable:BOOL=true;w10k_pass:BOOL;w1k_applicable:BOOL=false;w1k_pass:BOOL=true` | `(NOT w1k_applicable OR w1k_pass) AND (NOT w10k_applicable OR w10k_pass) AND (NOT w100kc_applicable OR w100kc_pass) AND (NOT w100kf_applicable OR w100kf_pass)` | `NONE` | `O(sa.m8.query-observations.v1)` |
| `build-p95` | performance | `pred-build-p95-v1` | `w100kc_applicable:BOOL=true;w100kc_pass:BOOL;w100kf_applicable:BOOL=true;w100kf_pass:BOOL;w10k_applicable:BOOL=true;w10k_pass:BOOL;w1k_applicable:BOOL=false;w1k_pass:BOOL=true` | `(NOT w1k_applicable OR w1k_pass) AND (NOT w10k_applicable OR w10k_pass) AND (NOT w100kc_applicable OR w100kc_pass) AND (NOT w100kf_applicable OR w100kf_pass)` | `NONE` | `O(sa.m8.build-observation.v1)` |
| `rebuild-p95` | performance | `pred-rebuild-p95-v1` | `w100kc_applicable:BOOL=true;w100kc_pass:BOOL;w100kf_applicable:BOOL=true;w100kf_pass:BOOL;w10k_applicable:BOOL=true;w10k_pass:BOOL;w1k_applicable:BOOL=false;w1k_pass:BOOL=true` | `(NOT w1k_applicable OR w1k_pass) AND (NOT w10k_applicable OR w10k_pass) AND (NOT w100kc_applicable OR w100kc_pass) AND (NOT w100kf_applicable OR w100kf_pass)` | `NONE` | `O(sa.m8.lifecycle-observation.v1)` |
| `repetition-ratio` | performance | `pred-repetition-ratio-v1` | `all_applicable_rows_present:BOOL;max_ratio:DEC;ratio_threshold:DEC=1.200000000` | `all_applicable_rows_present AND max_ratio<=ratio_threshold` | `NONE` | `O(sa.m8.query-observations.v1)` |
| `rss-cap` | resource | `pred-rss-cap-v1` | `candidate_peak_rss_delta_bytes:INT;rss_cap_bytes:INT=3221225472` | `candidate_peak_rss_delta_bytes<=rss_cap_bytes` | `INVALID_PROTOCOL_DEVIATION` | `C(resource_watchdog)` |
| `disk-cap` | resource | `pred-disk-cap-v1` | `aggregate_cap_bytes:INT=17179869184;aggregate_root_peak_bytes:INT;max_sample_root_bytes:INT;sample_cap_bytes:INT=8589934592` | `aggregate_root_peak_bytes<=aggregate_cap_bytes AND max_sample_root_bytes<=sample_cap_bytes` | `DISK_FULL` | `C(resource_watchdog)` |
| `network-zero` | hard | `pred-network-zero-v1` | `egress_bytes:INT;network_connections:INT` | `egress_bytes==0 AND network_connections==0` | `OUTBOUND_BLOCKED` | `C(environment),C(interposition_ledger)` |
| `listener-zero` | hard | `pred-listener-zero-v1` | `listeners:INT` | `listeners==0` | `OUTBOUND_BLOCKED` | `C(environment)` |
| `service-process-zero` | hard | `pred-service-process-zero-v1` | `candidate_service_processes:INT` | `candidate_service_processes==0` | `CHILD_LEAK` | `C(environment)` |
| `production-write-zero` | hard | `pred-production-write-zero-v1` | `production_write_count:INT` | `production_write_count==0` | `INVALID_PROTOCOL_DEVIATION` | `C(interposition_ledger)` |
| `residual-zero` | hard | `pred-residual-zero-v1` | `child_processes:INT;open_handles:INT;residual_bytes:INT;residual_entries:INT` | `child_processes==0 AND open_handles==0 AND residual_bytes==0 AND residual_entries==0` | `CHILD_LEAK` | `C(resource_watchdog)` |
| `sqlite-ratio` | adoption | `pred-sqlite-ratio-v1` | `lancedb_unfiltered_p95_ns:INT;ratio:DEC;ratio_threshold:DEC=0.700000000;sqlite_unfiltered_p95_ns:INT` | `sqlite_unfiltered_p95_ns>0 AND ratio<=ratio_threshold AND lancedb_unfiltered_p95_ns*10<=sqlite_unfiltered_p95_ns*7` | `NONE` | `O(sa.m8.query-observations.v1)` |
| `adoption` | adoption | `pred-adoption-v1` | `authority_burden_zero:BOOL;build_100k_pass:BOOL;default_dependency_zero:BOOL;filtered_100k_pass:BOOL;network_zero:BOOL;rss_2gib_pass:BOOL;service_zero:BOOL;sqlite_ratio_pass:BOOL` | `authority_burden_zero AND build_100k_pass AND default_dependency_zero AND filtered_100k_pass AND network_zero AND rss_2gib_pass AND service_zero AND sqlite_ratio_pass` | `NONE` | `I1(dependency_lock),O(sa.m8.build-observation.v1),O(sa.m8.query-observations.v1),C(environment),C(resource_watchdog),C(interposition_ledger)` |

Performance operand 的机械来源由下表唯一冻结；`applicable=false` 必须同时使用 `pass=true`，且不得制造 metric。所有 ns
均为 integer。`rebuild-p95` 只取 operation=`rebuild` 的 measured lifecycle observations；initial build 和 query 均禁止进入。

| workload | unfiltered p95 | unfiltered p99 | filtered p95 | filtered p99 | build p95 | rebuild p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `1k-correctness` | N/A | N/A | N/A | N/A | N/A | N/A |
| `10k-single-user` | 50000000 | 100000000 | 75000000 | 150000000 | 30000000000 | 30000000000 |
| `100k-capacity` | 100000000 | 200000000 | N/A | N/A | 300000000000 | 300000000000 |
| `100k-filtered` | 100000000 | 200000000 | 150000000 | 300000000 | 300000000000 | 300000000000 |

`repetition-ratio` 对每个实际存在的 backend/workload/query-class ratio row 适用，要求完整 population 且最大值
`<=1.200000000`。`sqlite-ratio` 只消费 `100k-capacity` unfiltered measured p95，ratio 以任意精度整数除法 half-even
序列化为九位 DEC，并以交叉乘法复核。`adoption` 的 `filtered_100k_pass` 是 LanceDB `100k-filtered` p95
`<=100000000`；`build_100k_pass` 是 LanceDB 两个 100K workload 的 build p95 均 `<=180000000000`；
`rss_2gib_pass` 使用 `2147483648`，其余 adoption BOOL 均从对应 closed evidence 重算，不得从其他 gate 的
`passed` 字段复制。

Execution report 和 verification report 的两个 `A<TECH_GATE_RESULT;26..26>` 必须逐项 byte-for-byte 相等，包括
predicate ID、typed operands、equation、expected、actual、passed、RESULT_CODE 和完整 expanded REF set。所有 hard/resource
行必须 PASS 才能形成非-abort execution report；performance/adoption false 行的 `failed_stable_code=NONE`，其 gate ID
必须进入首次可求值 PASS layer 的 `threshold_failures`。五个 PASS layer 的 `threshold_failures` union 必须恰等于所有
`passed=false` 的 performance/adoption gate IDs，且集合两两不重叠；FAIL layer 的该数组恒为 `[]` 并携带
`stable_code`、`pending_terminal` 和 abort-cleanup authority。阈值失败不得被改写成 raw-evidence failure；schema、authorization、
digest、inventory、hard 或 resource 偏离不得被降格成 threshold failure。

`residual-zero` 在 P7 只检查 execution report `sample_cleanup` 与最后一条 pre-cleanup resource-watchdog evidence 的四个值；
它不引用尚不存在的 durable package 或 cleanup receipt。P8/P9 另行且必须检查 normal receipt `after_zero=true` 和 after
全零；后者是最终 cleanup authority，不得反向改写 P7 gate。

## 11. P0 审查边界

P0 reviewer 只读检查 blob/外部记录分离、canonicalization、全部 schema、状态转移、Windows no-follow、query/gold cardinality、
16 个 fault 的 56/1,040 算术、预算/deadline、exact/flat fairness/index proof 和 package/receipt authority。审查期间不得修改
被审 bytes。P0 输出只能是：

- `PASS / P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY`；或
- `RETURNED_FOR_REVISION / P0_NOT_ACCEPTED`。

P0 PASS 只接受技术文字，不产生 P1–P9/P7A、identity、binding、root、dependency、benchmark、registry、M8 admission、backend
selection 或 implementation authorization。阶段状态、八项 Decision、approval 和 registry 由路线图及正式机器登记独立管理。
