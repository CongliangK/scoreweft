# PLAN_v3 · 零观点完整操作面 + 命运交响曲验收

> 状态：**v1.1（定稿 + 增量轮追加：R1-R4 执行完毕 + R5 落档 + v3.1-v3.4 增量轮记录 §10.10-§10.13）** · 2026-08-24
> 本文档是 v3 升级的单一计划锚点：所有 worker / reviewer 子智能体先读本文再动工。
> 上游输入：用户 v3 方案最终版 + 五路调查 + 三轮规划对抗审查（R1 契约/行业 12 MAJOR；R2 可行性/测试 7 MAJOR；R3 红线/一致性 5 MAJOR）。全部已修复，处置记录见 §10。
> 决策编号延续：本计划新增 **BG-D11..BG-D15**（§5；D11-D14 三轮规划审查定稿，D15 为 R4 仲裁新增），与 BG-D1..D10 并列，全文落位 AGENTS.md §一（v3 落档）。

---

## 0. 前置条件核验（2026-08-23 实测，全绿）

| 项 | 状态 | 证据 |
|---|---|---|
| fast 档测试 | ✅ 68 passed / 5 deselected，23.35s（AGENTS 记 ~26s 为约数口径） | 实测；**62 为迁移前旧口径**（62 +5 catalog +1 default_out = 68，docs/MIGRATION.md:48 佐证） |
| doctor | ✅ `"ok": true`，退出码 0 | 唯一 false = diffrhythm（optional，BG-D10 预期内） |
| ComfyUI | ✅ 127.0.0.1:8188 可达（0.33.0） | /system_stats 200 |
| GPU | ⚠️ RTX 4080 16GB，已用 ~78% | BG-D8 显存闸下 slow 档 demucs 会排队/降级（设计行为，不阻塞主线——命运工程只用 sfz/sf2，无 GPU） |
| out/minimal 锚点 | ✅ mix.flac 齐备 | test_cli sha 锚点有效 |
| python3 | ✅ miniconda base，numpy 2.5.1；**base env 无 jsonschema（禁止安装，见 §3.1）** | /usr/bin/python3 无 numpy（AGENTS 坑表成立） |

**结论：满足动工前置。** 全量测试口径：fast 68 / slow 3 / service 2 = 73。
**R1 动工前置动作**：向 `tests/baselines_w2a.json` 补一条 master 快乐路径基线（小输入 loudnorm 两遍，冻结 sha）——现 7 条无 master，master 校验退役的误伤保护不能只靠懒锚点。

---

## 1. 目标与五条原则

**目标**：AI 以资深音乐人的身份，通过核心元语直接操作工程数据；每个引擎的全部能力以统一契约（描述符）完整呈现在模型面前、且**可经编辑面直达**（含参数级，见 §3.6 params 透传槽）；宿主零观点、零特化、零围栏。**最终验收 = 贝多芬第五交响曲《命运》第一乐章（完整 502 小节、12 声部、约 5.3 分钟）以 v3 操作面端到端构建、渲染、QC 通过并交付试听**（§4）。

**五条原则**（沿用用户方案，不变）：
1. 能力全给，观点不给——机制进工具，音乐判断留智能体；
2. 数据是事实源，修改走命令层；
3. CLI 是快捷键，不是围栏——底层全量可达；
4. 结构收口，能力开放——五动词管结构，事件流与参数直通全集；
5. 听感归智能体——宿主只出文件与数字。

**验收范围裁定（已提交用户确认，见文末询问记录）**：
- **必达**：第一乐章完整。事实源 = Mutopia `Symphony5_1.mid`（Public Domain，管弦乐总谱；**审查 R1 期已实测下载解析**：74649 字节 / format 1 / 13 轨（1 meta + 12 乐器）/ 384 PPQN / **8295 音符 / 1013 四分音符拍 ≈ 506.5 小节 @2/4**（与权威 502 小节 + fermata 尾音吻合，repeat 已展开）/ **全曲单一恒 tempo = 192 quarter-BPM** / 音符力度恒 90、零 CC 零弯音（机械化底稿实证）；许可证据 = piece-info "Copyright: Public Domain"，ID Mutopia-2017/11/05-941；R4 入仓时以 `来源 URL + ID + sha256 + 取回日期` 四要素封存）。
- **可选加分**：第二乐章（Mutopia Symphony5_2 同许可可得）。
- **明确不承诺**：第三、四乐章——**不存在许可干净的机器可读源**（kernScores/CCARH = CC BY-NC-SA 4.0 违红线禁 NC；Musopen 该作品页无 MIDI；Project Gutenberg #156 标 Copyrighted；IMSLP 合成板块 = CC BY-NC 3.0）。全曲四乐章如用户强需求，须另行裁定人工录入路线，不属于本计划。

---

## 2. 调查结论摘要（详细证据见 §11 附录）

### 2.1 仓库现状关键事实（行号级挂载点已经 R2/R3 两轮审查逐行复核）

| 事实 | 位置 | 对 v3 的意义 |
|---|---|---|
| 7 引擎 payload 校验 100% 硬编码分散（~37 字段 / ~90 行） | synth.py:81-84、sf2.py:179-187、sfz.py:65-69、sample.py:52-67、master.py:114-120、demucs.py:60-67、ai.py:76-79 | 描述符系统的全部替换面 |
| 注册点唯一：`register_engine` 仅记名 | engines/base.py:30-35；统一校验入口 run_engine :98-119 | 描述符挂载点 |
| SMF 写入器仅 note/program/tempo（单恒速）；write_smf 排序稳定（同 tick 保插入序） | engines/midi_util.py（PPQ=480；:72 稳定排序） | 事件流编码器扩展点；**旧路径字节必须不动** |
| automation 仅 gain_db/pan/lowpass_hz | core/project.py:28（AUTOMATION_PARAMS） | VPO 表情层全不可驱动 = v2 事件流的动因 |
| project.py 全文 494 行，load_project 校验主体 :42-330 手写、**无任何写回路径**；返回 dict 含派生键（bank_explicit/program_explicit/clip_explicit） | core/project.py | 五动词需新建 save_project（序列化须过滤派生键白名单） |
| SameFileError 代码内未处理（靠 /tmp 副本外部规避） | project.py:481、test_eden_repro.py:31 | WP5 一并修复；**/tmp 副本纪律沿用至 R3 判据③（红线④）** |
| 轨→payload 组装硬编码 if/elif（含速记解析/派生量/显式优先三类程序逻辑） | project.py:404-435（track_engine_spec） | R2 由描述符 track_projection + 封闭钩子集 + params 覆盖合并数据化（R1 保持 if/elif 不动） |
| **v1 TRACK_KEYS 封闭集拒绝未知轨字段——引擎参数级直通缺通道** | project.py:30-31、_unknown :95 | §3.6 params 透传槽的动因（R3-P3） |
| 位级锚点：test_cli（out/minimal mix.flac sha）、test_engines w2a 7 例（**无 master 条目**→§0 前置动作补）、test_eden_repro | tests/ | v1 渲染路径逐位不变的硬约束 |
| test_catalog 断言引擎 payload docstring 原文；timbres.md 为 git 内活数据（--write 可重落盘） | test_catalog.py:104-105、catalog.py:78-108 | 描述符化后需同步改写并 catalog --write 重落盘 |
| 已有命运先导草稿 | out/audition/fate_motif/project.json（10 轨 2/4 108BPM c 小调） | 演奏法双轨叠置手法已验证 |
| schema 漂移 ×2 | project_v1.json master.qc 缺 duration_min_s（实现已支持）；sidechain/bus 描述过时 | WP5 顺带补正 |
| /tmp 与产物目录可能跨设备（os.replace 前提）；sfizz CLI 无 --version（版本取自 rpm 登记事实） | demucs.py:51 注释；sfizz_render --version 实测不存在 | 原子写 tmp 放目标同目录；sfizz binary_pin 降级为 sha/size 核验 |
| sfizz_render --midi 吃标准 SMF；fluid_player 按标准行为透传 CC/弯音 | sfizz --help 实测 + sf2.py:66 路径核实 | 控制事件编码进 SMF 的方案成立 |
| **legacy 直接依赖的底层函数：write_smf / write_notes_smf / fluidsynth_render（sfz 渲染入口同理）——签名与行为冻结点名** | legacy/midi2wav.py:19-21、gm_lofi.py:67-70、sfz.py | v3 改造不许动这些函数的旧路径（红线⑤，R3a-#10） |

### 2.2 行业规范对照与采纳修正（联网调查 + R1 审查复核驱动）

**符合度总评**：三大机制均有强行业先例（CLAP 事件模型 ≈ 事件流的 C 语言版；OpenAPI components/$ref 双形态 ≈ 双布局；LV2"数据与代码分离"哲学 = 描述符注册表；Live LOM 动词集 ≈ 动词面）。**采纳修正清单**：

| # | 修正 | 来源教训 |
|---|---|---|
| C1 | 描述符参数用**稳定字符串 id**（非序号），带 `unit` 量纲字段（出处=**LV2 units 扩展**；VST3 units 实为分组机制）；枚举必须伴 stepped 约束 | LV2 symbol / LV2 units / CLAP IS_ENUM↔IS_STEPPED |
| C2 | 描述符带 CLAP 风格 version 串 + binary_pin{version, sha256}；doctor 交叉核验；**sha256 为 advisory 黄灯**（doctor item 结构扩展 severity/warn 级，warn 不影响 exit code）；sfizz 无版本自述→version 取自 rpm 登记事实、核验退化为 sha/size | LV2 minor/micro + CLAP version + R2 审查 |
| C3 | 事件流**同 tick 规范全序**（三级决胜键，单一 `event_sort_key()` 函数，编码器与 show 共用导入，禁两处实现）：`(t, 类型序, pitch 升序, 插入序)`；类型序 = keyswitch → program_change(含其 bank 前置，见 C3a) → cc → pitch_bend → note_off → note_on | VST3 无序反面教训 + LMMS#4437 + CLAP events.h 排序硬契约 |
| C3a | **bank-PC 复合规则**：带 bank 的 program_change 编码为「CC0/CC32 紧贴 0xC0 之前」的复合消息，bank CC 是 PC 的组成部分、**不参与通用 cc 排序**（Bank Select 必须先于 PC 才生效） | Roland/Sweetwater/Kurzweil 手册惯例 |
| C3b | cc 编码舍入 = **round-half-up**（明示）；编码后值域 clamp | R1-F3 审查 |
| C4 | 事件 id / note_id → **v2 权衡后缓议**（§3.2 末尾记录理由），地址用规范排序索引；**操作纪律：索引跨编辑会漂移，连续编辑必须每次 edit 后重新 show 取索引**（写入 BG-D11） | MIDI2.0/Live11/CLAP 先例 + 有意识取舍 |
| C5 | $ref 采**标准 JSON Schema 语义**：仅 track 槽位、相对工程目录、禁绝对路径、外部文件不嵌套 ref、$ref 无兄弟字段 | OpenAPI 3.0 自创变体代价 + LMMS 断链教训 |
| C6 | undo：每动词一 undo 点 + 人类可读描述串；快照持久化；undo 前检测外部轨文件漂移（hash 对比，不一致须 --force） | REAPER Undo Block + Ardour 快照文件 |
| C7 | **编辑动词不设第五个**：duplicate 由 `insert --copy-of` 折叠承载（编辑动词=insert/set/move/delete 四个；五动词口径见 §3.4） | Live LOM 有 duplicate；折叠语义已覆盖 |
| C8 | 文本力度→velocity 采用 MusicXML 官方公式 velocity = percent×90（默认 forte=90）留档（命运 MIDI 实测力度恒 90，恰为该公式默认值，闭环验证） | MusicXML sound dynamics 规范 |
| C9 | 轨身份 = track.name；rename 动词负责引用重写（automation/sidechain/stem 文件名/外部轨文件名四处），实现为**两段式**（全部先写 tmp → 全部 rename） | Unity guid/Godot UID 教训记录 |
| C10 | 描述符 JSON 随仓库 git 版本化；**描述符 schema 文件为文档性契约，运行时校验用 validate_payload 手写驱动（仓库惯例，base env 无 jsonschema，零新增 pip 依赖——R3a-#5）；harvest_log 仅存命令行/参数名表/类型单位短摘要（≤1 行/参数）/来源 URL 指针，禁粘手册正文（R3a-#4）** | LV2 语义 + Ardour/NKS 反例 + R3 审查 |
| C11 | 未知事件类型 v2 闭集拒绝（工程文件是制品本身，静默跳过=静默语义丢失；CLAP size-skip 式透传留 v3.1） | CLAP 事件头设计 + R1 审查裁定 |
| C12 | **收割法第一事实源 = 引擎源码的 payload 读取行为**；底层工具文档仅作参数语义/单位参考与 doctor 交叉核验，不直接产 payload parameters | R1 契约审查 |
| C13 | 跨字段/条件约束一律走描述符显式 `invariants` 清单（代码断言），与单字段可无上下文求值的 {type,range,enum} 划界 | R1 契约审查 |

### 2.3 命运编制 → 资产映射（结论：资产层零缺口）

第一乐章编制：木管 2.2.2.2（长笛/双簧管/单簧管/大管各 2）、圆号 2（C）、小号 2（C）、定音鼓（C/G）、弦乐五部；**无长号/大号/短笛/低音大管**（末乐章才加入）。

| 声部 | 引擎 | 主力音色（sfz 引用串） | 备选 |
|---|---|---|---|
| 长笛/双簧管/单簧管/大管 a2 | sfz | `VPO/Woodwinds/{flute,oboe,clarinet,bassoon}-SEC-*.sfz` | VSCO2 同族（CC0）、sf2 FluidR3 GM |
| 圆号/小号 | sfz | `VPO/Brass/{french-horn,trumpet}-SEC-*.sfz` | VSCO2 FHorn/Trumpet |
| 定音鼓 C/G | sfz | `VPO/Percussion/timpani-hit.sfz`（半音映射 C2..F#3；**MIDI 实测定音鼓音 43..48 恰在键位内**）；滚奏 `timpani-roll.sfz` | VSCO2 Timpani/TimpaniRolls |
| 弦乐五部 | sfz | `VPO/Strings/{1st,2nd}-violin|viola|cello|bass-SEC-{staccato,sustain,...}.sfz`（短动机用 staccato——VPO sustain attack 0.4-0.6s） | VSCO2 Ens 系、karoryfer |

**R1 审查实测补充（决定性）**：
- **VPO KS 文件实为 `sw_last` 语义**（如 1st-violin-SEC-KS-C2.sfz：12 组 sw_last + sw_default），note_on vel127 短保持 + note_off 无害，计划编码方案可行；**KS 键区逐乐器不同且必须避让音域**（小提琴/小号/长笛 KS 在 C2-F2 区，圆号/大管/大提琴 KS 在 C5/C6 区）→ mapping.json 逐乐器携带 KS 键位，gen_fate 断言 KS pitch ∉ 该轨音符域（R1-F8）。
- **低音提琴写谱高音陷阱**：Mutopia t12（低音提琴）与 t11（大提琴）同拍**同度** 417 次——MIDI 是写谱音高，低音提习俗例**发声低八度**；VPO bass 按发声高音编键。→ mapping.json 增 per-track `transpose` 字段（contrabass = -12），gen_fate 加断言"重合处低音 ≤ 大提琴"（R1-F10，不修则弦乐四八度叠置塌层）。
- **轨名非语义**（'one:'…'twelve:'），乐器识别依赖内嵌 GM PC + 音域 + 总谱常识；**PC 部分失真**（圆号/小号两轨均 = GM English Horn 字节 69，其余轨 PC 解码正确）→ importer 逐轨输出 PC/音域证据日志（零观点不解释但留证据），mapping 注记写明识别方法（R1-F12）。
- 定音鼓/木管/弦乐键位实测全部落位（详见 §11）。

署名义务：**VPO 署名是义务而非惯例**（AGENTS 红线①："发布使用 SalamanderGrand / VPO 音色的成品时负 CC-BY 署名义务"），按 REPORT §7.6 模板履行（Paul Battersby + virtualplaying.com）；注记引用库内 license.htm 复合许可原文是义务的**精确化**而非替代（R3a-#6）。当前 §2.3 主力映射全部落在 Standard 组（非 Philharmonia 源的 PERF 组），无额外渊源义务。

---

## 3. 架构设计 v3（修订版）

### 3.0 分层（沿用用户方案）

```
感知层    智能体域：多模态/外部工具 —— 宿主不碰
操作层    bgm 五动词 show/insert/set/move/delete ＋ render/qc/diff/undo
检视层    show 视图族（结构/音符窗/事件流/描述符注册表/diff）
数据层    project.json v2 双布局（内联 或 $ref per-track）
表达层    通用事件流 ＋ params 透传槽 ＋ 引擎描述符注册表
引擎层    7 引擎不变；payload 校验由描述符生成
资产层    不变（18 条 manifest）
验证层    校验器/QC/位级复现/测试 —— 零改动复用（锚点不变量见 §6）
```

**术语口径（全文统一，R3-P1 修复）**：**五动词**（操作面元语）= show / insert / set / move / delete；**编辑动词**（bgm edit 下的四个）= insert / set / move / delete；**复合命令** = split / merge / undo。

### 3.1 机制 A：引擎描述符注册表（声明式）

**Schema**：`bgm_gen/schema/engine_descriptor_v1.json`（JSON Schema 定义描述符本身；**文档性契约**——运行时校验用 validate_payload 手写单字段驱动，仓库惯例，零新增 pip 依赖，base env 无 jsonschema 禁止安装——C10/R3a-#5）。

描述符字段：
```
{ engine, version,                    # CLAP 风格语义化版本串
  binary_pin: {version, sha256|null}, # doctor 核验（sha=advisory 黄灯；sfizz 无 --version，version 取 rpm 登记事实+sha/size 核验）
  parameters: [{id*, type: int|float|enum|bool|str|path|any|object|array|tuple,
                schema?, min?, max?, default?, unit?, enum?: [...], stepped?,
                flags?: [required|optional], realtime?}],
  input_ports: [...],
  events_supported: [{type, note}],   # §3.2 事件类型消费声明（引擎级事实）
  formats: [...],
  track_projection: {...},            # 仅 synth/sf2/sfz/sample：轨字段→payload 映射表＋封闭钩子集＋params 覆盖合并（§3.6）
  invariants: [...],                  # 跨字段/条件约束清单（C13）
  coverage: {tier: A|B|C, evidence, probes, gaps} }
```
**三档定义（R3-P21）**：A=程序化收割（第一事实源=引擎源码 payload 读取行为）；B=AI 起草+探针验证（sfizz：CLI --help + SFZ 规范 + 源码）；**C=手写降级**（A/B 均不可行时人工起草，coverage.gaps 强制标注 + 全量行为探针；当前无 C 档实例，诚实记录）。

**存放与来源**：描述符本体 = `bgm_gen/engines/descriptors/<engine>.json`（git 版本化、声明式为源、不依赖运行时自述）。收割器 `bgm_gen/engines/harvest.py`（手动运行，产出+证据日志落 `descriptors/harvest_log/`，**日志内容纪律见 C10**；模块级仅标准库，pkgutil 自动发现安全）。辅助参考源：fluidsynth settings API（仅 doctor 交叉核验）、ffmpeg filter 手册（参数语义/单位）、ComfyUI /object_info（ai 引擎 params 点路径覆盖语义核验）、demucs/matchering 的 argparse/签名（comfyui env 子进程只读探测，零安装）。**关键认知：sfizz 能力面=SFZ 文件本身（对 AI 无闸门），描述符只覆盖渲染选项与事件通道，coverage 如实标注**。

**生成式校验**：`base.py` 新增 `validate_payload(engine, payload)`（单字段约束描述符驱动）+ **`content_hash_key(engine, payload, sr, channels)`**（增量渲染 hash 键组装，内部读 engine/binary_pin/descriptor 三版本；**R1-W1 随 validate_payload 一并交付，W2 只调用**）；跨字段约束走 invariants 断言。`run_engine` 唯一入口调用；7 引擎内硬编码校验退役。**v1 组装结果不变锁**：track_projection 数据化在 R2 落地，以"重组装深比较"测试锁定（样本 = examples/minimal.json + baselines_w2a 全部 spec + **out/eden_v2/project.json（只读）**）；R1 阶段 track_engine_spec 的 if/elif 原样不动。

**track_projection 钩子集（封闭清单，R2 实现）**：数据映射表 + 仅四类白名单钩子：① sf2 instrument 速记解析；② sample `length_s` 派生量（clip×spb）；③ meta 注入（bpm/sr）；④ **params 覆盖合并（§3.6，显式优先——与 sf2 bank/program 显式优先惯例同族）**。新增钩子须主线批准。

**事件能力门**：`events_supported` 驱动 §3.2 事件校验。**sf2 = cc + pitch_bend only**（program_change 透传会破坏 fluid_synth_program_select 显式选音色、keyswitch 的 note_on 会在无 KS 区音色上出实音）；sfz = cc + pitch_bend + keyswitch + program_change + note_on/off；synth/sample = notes-only（事件流任何类型均拒）。

**探针语义（判据可机械执行）**：行为探针（非音质探针）——对每个 declared parameter 至少一组赋值渲染：断言 exit 0 + 出参契约字段齐（path/sr/channels/duration_s/rms_db）+ 产物非零字节 + determinism 分级正确。取值：数值型探 {default, 边界近点}；随 program 变的 params 按 invariants 声明的合法组合各探一条；ai 引擎探针=参数注入点被 /object_info 接受（非每参数全渲）；master matchering+ref 条件组合挂 slow。

**防漂移四件套**：①binary_pin 版本+sha（sha=advisory）；②行为探针（test_descriptors.py，demucs/ai 挂 slow/service）；③doctor 增查（item 结构扩展 severity/warn，warn 不拉红 exit code）；④引擎/二进制升级 = 先 diff 描述符再重收割。

**呈现**：`bgm show engines [--json]`（WP1 即交付）。R1-W1 交付清单另含：`bgm catalog --write` 重落盘（timbres.md payload 段与描述符同步）。

### 3.2 机制 B：通用事件流（schema v2 核心）

**存储**：track 新增 `events: [...]`（与 notes 同基准：**轨局部 beat**）。类型表：

| type | 字段 | SMF 编码 |
|---|---|---|
| `cc` | ctrl(0-127), value(0-127，浮点允许；编码 round-half-up 后 show 显示编码值) | 0xB0 |
| `pitch_bend` | semitones(浮点)；**量程=轨级字段 `bend_range`（半音数，默认 2）**——sfz 轨含弯音事件时必须显式声明（SFZ 文件级 pitch_wheel_range 逐文件不同）；sf2 轨默认 2 | 0xE0 14-bit 线性映射 `clamp(round-half-up(8192*(1+s/range)), 0, 16383)` |
| `keyswitch` | pitch(0-127) | note_on vel127 + note_off；**note_off tick = min(下一 KS 前 1 tick, KS+0.25beat)，下钳 KS+1 tick（beat 0 合法）；相邻同 tick 双 KS：编码为 on/off/on/off 各 +1 tick 确定性错开（字节锚点锁定——R3-P8）** |
| `program_change` | program, bank? | **bank = CC0/32 紧贴 0xC0 之前**的复合消息，不参与通用 cc 排序（C3a） |
| `note_on` / `note_off` | pitch, vel(**note_on vel ∈ 1..127，vel=0 校验层拒绝**)；note_off 编码 velocity=0（与既有 Trk.note 出口一致） | 0x90/0x80——**与 notes[] XOR** |

**notes[] 与事件流的关系（XOR 规则 + 投影规范）**：notes[] 语义不变（v1 兼容）；note 事件载体二选一，**校验层强制**。v2 schema 中 notes 改 optional（v1 仍 required+minItems 1）。**note 事件 → notes 四元组投影规范**：① 同 pitch 交叠复音校验层拒绝（配对无歧义）；② 悬空 note_on 拒绝；③ events-only 轨缺省 clip 按 **note_off 最大 beat** 推导；④ synth/sample 轨禁止 note 事件载体（必须 notes[]）；sf2/sfz 轨允许，投影在组装层合成。"notes = note_on/off 的视图"在 show 层兑现。

**payload 事件通道与编码合并**：控制事件进引擎 payload 的新字段 **`payload.events`**（track_projection 从轨 events 投影）。sfz/sf2 引擎分支：payload 含 events 时改走 `events_to_smf`——notes 四元组先投影为 note 事件、与控制事件经 `event_sort_key()` 合并编码进**同一 SMF**（notes[]+cc 混装轨由此支持）；payload 无 events 时**保持 write_notes_smf 旧路径字节不动**（v1 兼容）。`descriptors/{sfz,sf2}.json` 随之更新（parameters/events_supported）并记 harvest_log（R2 交付项）；**payload.events 引入伴随 sfz/sf2 描述符 version bump（1.1.0）；envelope spec_version 不变（events 为 payload 内可选字段）——BG-D6 口径注记（R3a-#9）**。**窗口语义注意（R2 审查 A·6）**：events-only 轨缺省 clip 按 note_off 最大 beat 推导——落在最后 note_off 之后的控制事件会被窗口截断，表情层须知悉。

**同 tick 规范全序（C3）**：单一 `event_sort_key()`（midi_util 定义，编码器与 show 共用导入）：`(t, 类型序, pitch 升序, 插入序)`；类型序 = keyswitch → program_change（含 bank 前置）→ cc → pitch_bend → note_off → note_on。字节级锚点测试锁定（含"带 bank 的 PC"正例、相邻同 tick 双 KS 错开锚点）。

**未知类型**：v2 闭集，校验拒绝（C11）。

**编码器**：`midi_util` 新增 `events_to_smf(path, events, bpm, ppq=PPQ, ch=0, prog=None)`（支持 ppq 入参——命运链路用 384 整数倍 PPQ 避免微移）。**`write_notes_smf` 旧路径字节零改动**；test_events 补对 write_notes_smf 产物的 .mid 直接 sha 锚点（现有保护全是渲染间接锚）。

**引擎消费矩阵**：

| 引擎 | cc | pitch_bend | keyswitch | program_change | note 事件载体 |
|---|---|---|---|---|---|
| sfz(sfizz) | ✅ 透传 | ✅（量程按轨声明） | ✅ sw_last | ✅ | ✅（投影为 notes） |
| sf2(fluidsynth) | ✅（fluid_player 标准透传） | ✅（默认 ±2） | ❌ 拒 | ❌ 拒（护 program_select 显式选音色） | ✅（投影为 notes） |
| synth / sample | ❌ 拒 | ❌ 拒 | ❌ 拒 | ❌ 拒 | ❌ 拒（必须 notes[]） |

**车道=投影**：`show cc` / `insert cc-points` 实现为 events 上的视图/动词，不新增数据层。

**事件 id 权衡记录（C4）**：单写者 CLI 前提下规范排序索引+谓词选择已可精确寻址；**决定 v2 不加 id 字段**（v3.1 候选）；索引漂移纪律入 BG-D11。

### 3.3 机制 C：schema v2 双布局 + 增量渲染

**spec_version**：`"1"`（v1 规则严格适用）或 `"2"`（新增：track.events / track.bend_range / **track.params（§3.6）** / track.$ref / master.qc.duration_min_s 补正）。**v1 工程零迁移、渲染位级不变**。

**$ref 规则（C5）**：仅 track 槽位 `{"$ref": "tracks/<file>.json"}`；相对工程文件目录；禁绝对路径/嵌套 ref/兄弟字段；外部文件 = 完整 track 对象（name 即身份）。装载在 json.load 后、校验前；装载层记录来源映射，**校验报错路径附来源文件标注**；**装载层前置门：spec_version="1" 的轨带 events/$ref/params/bend_range 一律拒绝（先查版本再展开——R3-P7），v1+$ref 负例入 R1-W2 的 test_dual_layout**。

**save_project()**：双布局感知序列化 + **原子写**（tmp 放**目标同目录** + os.replace）；**序列化键白名单过滤派生键**（bank_explicit/program_explicit/clip_explicit/$ref 来源映射）；规范化 = 键序按 schema 属性序、固定 indent、ensure_ascii=False（幂等口径=语义等价+字节稳定，连 save 两次 sha 相等为测试锁定）。

**split/merge**：core 层 `split_layout()/merge_layout()`（CLI 暴露在 WP3）。split 产物文件名由 track.name 派生（slug 化）；文件名与 name 允许不一致（装载以文件内 name 为身份，show 标注来源文件）。

**增量渲染（默认关闭）**：`bgm render --incremental` 显式开启（cli.py render 分支 3 行 parser + 1 行透传，**R1-W2 所有**）；**`BGM_NO_INCREMENTAL=1` 为硬闸**（赢过 flag，输出一行日志；**读取点在 render_project 内部**，in-process 调用者同受保护）；**conftest 统一注入 env=1**，增量专项用例覆写一律走 `helpers.run(env_extra=...)` 子进程或 autouse fixture save/restore，并加元测试断言注入生效。机制：边车 `<track>.<engine>.render.json` = `{content_hash, summary:{sr,channels,duration_s,rms_db}}`（**渲染成功后先 stem 后边车**固定顺序，崩溃最多多渲一次——**崩溃窗口用例：stem 已写、边车未写 → 重跑不假命中，入 test_dual_layout（R3-P4）**）；**hash = `content_hash_key()`（=组装后 payload 规范化 JSON + engine/binary_pin/descriptor 三版本 + sr/channels）**；命中且 wav 存在→跳过重渲（日志明示），返回值从边车 summary 回填；**mix/master 恒重跑**。增量用例用固定 tmpdir 时**自清残留边车**。确定性引擎下增量结果与全量位级一致（测试锁定）。

**SameFileError 修复**：render_project 快照复制改 tmp+rename。**快照口径**：v1 工程快照保持 copyfile 字节保真不动；**$ref 工程快照 = 内联展开单文件**（正本不动、快照自包含、BG-D9 惯例保持）；判据⑦"逐位一致"= wav/flac 产物 + v1 快照字节。

**schema 文件补正**：project_v1.json 补 `master.qc.duration_min_s`、更新过时描述；新增 project_v2.json。

### 3.4 机制 D：操作层五动词 + undo

**命令语法**：
```
bgm edit <verb> --target <路径> [--window beat:a-b|sec:a-b] [--payload '<json>']
        [--copy-of <源> | --transpose <半音> | --quantize <拍格> | --scale <比>]
编辑动词（4）: insert | set | move | delete
复合命令: split | merge | undo
bgm edit undo [--list] [--force]
```
（五动词 = show + 上述编辑动词四；show 的 CLI 形态见 §3.5。）

- **target 语法**：`tracks/<name>`、`tracks/<name>/notes/<i>`、`tracks/<name>/events/<i>`、`tracks/<name>/clip`、`tracks/<name>/params[/<key>]`（§3.6）、`automation/<i>`、`sections/<i>`、`meta/<field>`、`master/...`；索引 = show 规范排序视图序号（索引漂移纪律入 BG-D11）。
- **语义细则（R3-P20）**：`insert` 带索引 target = 在该索引**之前**插入（splice）；`insert` 无索引 = append/按 payload 内容定位；`set --payload` 对对象 target = **深度合并**（未知键拒绝，整替换须经 delete+insert）；负例入 test_edit。
- **管线**：读→校验→变换→**再校验**→原子写→结构化 diff（stdout 摘要 + --json）。**--window/--payload 解析放 handler 内手写报错**（守住"stderr 含字段路径"测试口径）。
- **跨形式折叠**：`--copy-of` 跨 notes↔events 载体先转换；有损语义（vel=0/交叠复音）校验层拒绝并报字段路径；test_edit 含正/负例。
- **undo（C6）**：每动词一快照点+描述串；快照布局保全（主文件+外部轨文件）；栈 = 工程旁 `.bgm_undo/`（**栈格式契约：快照文件 `<seq>.<timestamp>/` 目录 + `manifest.json`（[{seq, desc, files, sha256}]）——show diff 读 manifest，跨 worker 接口以此为准（R3-P2）**）；上限 50 条淘汰测试锁定；.gitignore 增 `**/.bgm_undo/`；**执行序**：先全量写快照（成功才入栈）→ 再逐文件 tmp+rename（两段式）；失败从刚写的快照自动恢复（写失败用例：只读目录模拟）。**undo 前置检查**：外部轨文件 hash 与栈顶 manifest 记录不一致 → 报错列漂移文件，须 `--force`（负例入 test_edit）。**测试专用 crash 注入钩子 `BGM_CRASH_AFTER=N`**（env 门控：第 N 次文件写后 os._exit(137)，仅测试用例使用）。
- **时间寻址**：beat 权威；sec 窗口按 meta.bpm 换算落 beat（正例入 test_edit）。
- **双入口**：CLI + core/edit.py 同校验路径。

### 3.5 机制 E：检视层 show 族

```
bgm show structure [--json]        # 段落/轨/clip/时长总览
bgm show notes [--track T] [--window ...] [--json]
bgm show cc [--track T] [--ctrl 1|11|64]   # events 车道投影视图（显示编码后值，用例锁定）
bgm show events [--track T] [--window ...] # 含 notes→note_on/off 投影
bgm show engines [--json]          # WP1 已交付，此处归口
bgm show diff [--undo N]           # 对比快照栈/当前文件（读 §3.4 manifest）
```
全部 `--json/--text` 双输出。**视图回归（R3-P15）：`bgm_gen/tests/test_show.py`（fast）**——含 show 族输出结构断言 + **盲测用例（pytest 化）**：题库 ≥3 类题型（窗口轨集合/轨音色/窗口音符数）× 每类 ≥5 题、seed 固定可复现、**ground truth 独立实现**（直接 json.load 工程原文件计算，不经 load_project）、断言失败即 fail；盲测效力口径=锁"show 投影 vs 工程原文件"一致性。

### 3.6 机制 F：params 透传槽（payload 参数级直通——R3-P3 修复，承接用户"五动词+payload 直通"）

**问题**：v1 TRACK_KEYS 封闭集（project.py:30-31 + _unknown :95）使工程轨只能触达固定映射字段；引擎 payload 其余参数（sf2 的 gain/channel、sample 细粒度参数等）在工程层面不可达——与原则 3/4 的"底层全量可达/参数直通全集"冲突。

**设计**：v2 track 新增 **`params: {...}`**（可选对象）：
- **校验**：键必须 ∈ 该轨引擎描述符 parameters ids（notes/events 通道除外）；值按描述符单字段校验；跨字段约束走 invariants（复用 validate_payload 同一路径）。
- **组装**：track_projection 产出默认 payload 后 **params 覆盖合并**（显式优先，钩子④）。
- **编辑面**：`bgm edit set --target tracks/<name>/params --payload '{"gain":0.5}'`（深度合并）；`delete --target tracks/<name>/params/<key>`；`show structure/notes` 呈现轨的 params 摘要。
- **零观点**：宿主不解释参数语义，校验完全由描述符驱动；非法键/越界值在工程校验层拒绝（报字段路径）。
- **R2 落地**（随 track_projection 数据化）；v1 工程无 params 字段零影响（深比较锁覆盖）；命运 mapping 可用 params 承载引擎级参数（如 sf2 轨 gain 补偿）。
- 测试：正例（sf2 轨 params.gain 生效——R2 冒烟 RMS 变化）、负例（未知键/越界值/synth 轨写 sf2 专键拒绝）。

---

## 4. 命运交响曲验收工程（最终验收）

### 4.1 范围与事实源

第一乐章完整（Allegro con brio，2/4，c 小调，502 小节；**MIDI 实测 1013 四分拍 ≈ 506.5 小节，repeat 已展开**）。事实源：`examples/fate/Symphony5_1.mid`（Mutopia PD，73KB，随仓库提交 + 许可证据文件：URL + ID + **sha256 + 取回日期**）；校对源：IMSLP Breitkopf 1862 扫描（人工抽查呈示部/展开部/再现部关键段落）。

**关键实测参数（R1 审查代理实测，R4 锚点）**：8295 音符 / 13 轨（轨名非语义；圆号/小号两轨 PC 失真为 English Horn(69)，其余正确）/ **恒 192 quarter-BPM** / 力度恒 90、零 CC、零弯音 / 定音鼓音域 43..48 / 低音提琴与大提琴同度写谱（→ -12 移调）。

### 4.2 构建管线（零观点工具 + 音乐判断数据分离）

```
① smf_import（通用工具，零观点）
   bgm_gen/core/smf_import.py —— 纯标准库 SMF format 1 读器（~200 行）：
   PPQ/tempo（主导 tempo = 覆盖 tick 时长最长者，并列取先——合成双 tempo 用例锁定）/轨名/PC/音域证据日志/
   note on-off → 每轨 notes 四元组（beat=四分音符）；running status 解析（合成用例）/dur=0 钳制/未配对 off 告警
② mapping（音乐判断，纯数据）
   examples/fate/mapping.json —— 12 轨 → 引擎+音色 + 演奏法策略（R4 终态：双轨叠置——KS 单轨经实测证伪回退，见 §4.2④ R4 追加裁定与 §10.8；KS 键位证据留档 ks_layout_evidence）
   + per-track transpose（contrabass=-12 及移调乐器表）+ pan 布局 + 增益表 + 弦乐 dur 补偿
   （引擎级参数经 track.params 透传，§3.6）
③ gen_fate（组装器）
   examples/gen_fate.py（参照 gen_eden_v2 规模 300-500 行）—— ①×② → project.json v2 双布局 + 表情层；
   四断言（A1 为双轨回退后改写口径）：零 KS 事件守卫（mapping 带 KS 条目时逐轨校验避让）、
   重合处低音提琴 ≤ 大提琴（移调后）、note 落 VPO 键位内、
   全轨同时无声最大间隙 ≤ 声明 silent_window_max_s 减尾音余量（R2-T12）
④ 表情层（AI 音乐人施加，走 v3 动词/事件流）
   至少：CC1 动态渐变、vel 塑形、rubato=分数拍错位；弯音按音乐判断慎用。
   （keyswitch 演奏法切换原列其中——**R4 实测 KS 事件×全量音符触发 sfizz 失控后取消**，
   演奏法改双轨叠置承载，见 §10.8；本行为历史口径注记。）
   **R2 实测纠偏（决定性，mapping 必须据此选音色）**：VPO SEC-sustain 全库零 CC opcode——CC1 动态仅在 PERF 族生效（set_cc1/gain_cc1，实测 0→127 渐强 -64→-30dB 单调）；
   tremolo 走 CC11（SEC-tremolo）或 CC1（PERF-tremolo）；Brass 合奏有 normal-mod-wheel 变体。
   → 动态层用 PERF 变体或 tremolo 通路，不得对 plain sustain 挂 CC1。VPO 未声明 pitch_wheel_range，
   实测默认 2 半音（examples/fate/bend_range_evidence.json）；KS 实测 sw_last 有效
   （c2=sustain/e2=staccato 差 >12dB）——但 R4 全量实测推翻外推：KS×874 音符上下文交互失控
（§10.8），最终仍回退双轨叠置。
   **R4 资源事故追加裁定（2026-08-23）**：**PERF sustain 族（`*-SEC-PERF.sfz`）渲染期禁用**——
   sfizz 1.2.3 对其 loop_continuous 采样无限渲染（实测 30s 写出 4.28GB；曾致整机冻死，见 §10.7；
   引擎层已加三重护栏兜底拦截）。命运动态层改用：SEC-tremolo + CC11（长音动态）或
   PERF-staccato（短音，R2 冒烟已证安全）或 vel+gain 塑形。
⑤ 渲染与 QC：bgm render → out/fate_mvt1/{mix.flac,stems/,project.json(内联快照),qc.json}
   预算：**R4 实测订正（§10.8）——sfizz offline 超实时 ~200×，23 轨全链 38-43s/轮**（原依 eden 线性外推的 ~20min/轮估计差 30 倍量级，峰值 RSS ~1.3GB）；迭代总量 ≤40min 口径不变
```

**流程前置**：**机械化直渲底稿 QC 预检**——gen_fate 产出无表情版先渲一轮，跑 bpm/key/silent 实测，前置暴露检测器行为，再进表情迭代。

**演奏法策略**：优先 VPO KS 变体单轨 + keyswitch 事件（VPO KS 实测 sw_last 语义，编码方案兼容）；R2 探针异常 → 回退双轨叠置（fate_motif 已验证手法）。**回退判据**：双轨版 gen_fate 产物通过 test_fate_data 四断言 + QC 全绿；记录落点 = 本文档 §10 执行期小节（R5 并入 REVIEW_LOG.md）+ mapping.json 注记同步改写。

### 4.3 QC 目标（master.qc）

| 项 | 目标 | 备注 |
|---|---|---|
| target_lufs | -14 ±1 | B 站标准；**crest>13dB 预案**：loudnorm 第一遍免费给出预测 crest，超限时声明式母前处理（bus 级轻限幅）或 target_lufs 工程级下修并注记理由。**R4 落地：`master.pre_limit` 母前限幅机制已入 v2 schema（§10.8）；实测 ffmpeg linear 判定 binding 约束=LRA ≤ 目标 11 而非 crest（不限幅 LRA 12.4 → +3dB 削顶 LRA 10.5 转 Linear）** |
| true_peak_db | ≤ **-1.2** | 留 loudnorm dynamic 回退 TP 超参余量（REPORT 已付学费）；test_fate 断言 `normalization_type=="linear"`（master.py 已解析该字段），dynamic 回退第一时间显形。**R4 定稿实测 Linear ✓（TP -3.3）** |
| silent_window_max_s | ≤ 2.5 | 戏剧性休止放宽（机械底稿谱面间隙 0.16-0.6s 量级，2.5s=4 小节全编制无声，保守安全；§4.2③ 第四断言预警）。**R4 定稿实测 0.75s ✓** |
| key | C minor 入 top-2 | 管弦 mix 检测行为无先例 → 直渲预检前置暴露；**失败预案**：记录实测 top-3 与 r 值，判据降级须主线显式批准并在 REPORT v3 节注记理由，**不允许 worker 静默改 key_top2**。**R4 主线裁定（§10.8）：降级 info（qc 置 null 声明式正门）——实测 G minor(0.76)>C major(0.72)>C minor(0.67)，G-G-G-Eb 属音主导+bE 大调第二主题致 KK 结构性偏置；调性正确性由乐谱事实源保证** |
| bpm | 声明 192 ±2% | **QC 门按 top-3 含 0.5/1/2 倍频口径判定（qc.py 现行为），top-1 直命中为期望非承诺**（192 在量程 50-200 内；八分 IOI 0.156s 距折叠窗下限仅 6.25ms）。**R4 主线裁定（§10.8）：降级 info——实测 99.4/198.8/92.3 恒 +3.5% 偏快（检测器对管弦长音素材 IOI 系统偏差），节拍正确性由 duration 门（317.812s 机器精确）独立锁定** |
| duration_min_s | **300** | 实测 1013 拍 @192 = 316.5s（5.28 min）；阈值取 300 防中途截断（R3-P9）。**R4 定稿实测 317.812s ✓** |
| sr/channels | 44100/2 对齐 meta | hf_ratio 不设阈值（缺省 info 级观察项） |

交付：`out/fate_mvt1/` 全套 + 试听指引 + **署名义务注记**（VPO——Paul Battersby + virtualplaying.com，按 REPORT §7.6 模板履行，引用库内 license.htm 复合许可原文）。

---

## 5. 五轮瀑布执行计划（worker/reviewer 对抗协议）

**每轮协议**：worker 并发实现（提示词含本文档路径+任务书）→ reviewer 并发对抗验收（判据命令化）→ 主线修复放行 → 轮末重跑 fast 档（+受影响 slow/service）。轮间严格瀑布。**修复循环上限：单轮 ≤2 次，超限升级用户仲裁或更换 worker（R3-P13）。并发 worker 各用独立 git worktree，轮末由主线合流（同文件分区合流时人工核对边界——R3-P19）。**

| 轮 | 工作包 | worker 并发分工（文件所有权） | reviewer 验收判据（命令化） |
|---|---|---|---|
| **R1 地基** | WP1 描述符 + WP5 双布局 | **W1 描述符**：schema/engine_descriptor_v1.json、engines/descriptors/*（7 份）、engines/harvest.py、base.py（validate_payload + content_hash_key + invariants）、7 引擎校验退役、doctor.py 增查（severity/warn 扩展）、cli.py（**仅 show engines 子命令区**）、test_descriptors.py、test_catalog.py 断言改写 + catalog --write 重落盘、**baselines_w2a 补 master 基线（前置动作）**。track_engine_spec if/elif 不动 ‖ **W2 双布局**：core/project.py（$ref 装载+版本前置门+来源标注/save_project 键白名单/split/merge/SameFileError/增量边车+env 硬闸读取于 render_project 内）、schema/project_v1.json 补正 + project_v2.json、.gitignore（.bgm_undo/ + 边车）、conftest.py（BGM_NO_INCREMENTAL=1 注入 + 未打 marker 用例收集期 fail）、**cli.py 仅 render 分支（--incremental 4 行）**、test_dual_layout.py | ① `python3 -m pytest bgm_gen/tests -q` 全绿；② `bgm show engines --json`（jq 断言 7 引擎字段齐）；③ 探针测试（§3.1 语义）全绿（demucs/ai 挂 slow/service）；④ `-m slow` 位级锚点不变（含新补 master 基线）；⑤ split 位级一致（minimal 主样本挂 fast；eden_v2 全量挂 slow）；⑥ 增量专项（--incremental + env=0 子进程）：改一轨仅该轨重渲 + 仅改 bpm 未命中负例；⑦ 缺省 render 逐位一致（wav/flac+v1 快照字节）；⑧ **v1+$ref / v1+events / v1+params 装载拒绝负例**；⑨ marker 纪律元测试（临时无 marker 用例收集期 fail） |
| **R2 通道** | WP2 事件流 + params + track_projection 数据化 | **W 事件流**（单 worker）：schema/project_v2.json events/bend_range/**params**、core/project.py 事件校验（XOR/配对/悬空/交叠/vel≥1/bend_range 声明/sf2 KS·PC 拒）+ params 校验、midi_util event_sort_key() + events_to_smf()（ppq 入参）、sf2/sfz 消费分支（payload.events + notes 混装合并编码；无 events 走旧路径）、**params 覆盖合并（钩子④）**、descriptors/{sfz,sf2}.json 同步更新 + harvest_log、track_projection 数据化（钩子集封闭）+ 重组装深比较锁（minimal + baselines 全部 spec + out/eden_v2 只读）、cc 车道 core 函数、test_events.py | ① fast 全绿；② test_events：同 tick 全序字节锚点（bank-PC 正例/相邻同 tick 双 KS 错开）、负例族（XOR/悬空/交叠/vel=0/synth 轨事件/sf2 KS/sf2 PC/v1+events/sfz 弯音无声明/**params 未知键·越界·跨引擎错键**）、events-only clip 推导、cc half-up+clamp、弯音 14bit 往返、ppq 入参、write_notes_smf .mid 直接 sha、v1 工程 sha 不变、重组装深比较；③ 冒烟（slow）：VPO CC1 渐强 RMS 单调上升、弯音微分音（实测 VPO 文件量程回填 mapping）、keyswitch 探针（sw_last 切换有效；异常触发回退并记录）、**sf2 轨 params.gain 生效（RMS 变化）** |
| **R3 操作** | WP3 动词 + WP4 检视 | **W1 动词**：core/edit.py（新）、cli.py edit 族+undo（manifest 栈格式/漂移检测/BGM_CRASH_AFTER/两段式写）、test_edit.py ‖ **W2 检视**：core/show.py（新）+ 视图族、**test_show.py（fast，含盲测 pytest 化用例——§3.5 规格）**；**cli.py show 子命令接线由主线在 worker 阶段同步完成（轮内交付物，reviewer 验收前就绪——R3-P2）** | ① fast 全绿；② test_edit：CRUD 正负例（exit≠0+stderr 字段路径+无 Traceback，含 $ref 来源标注例）、undo 漂移检测负例（--force 才过）、BGM_CRASH_AFTER 原子写窗口注入、undo 写失败自动恢复、跨形式 copy-of 正/负例、sec 窗换算、rename 四处重写、undo 上限淘汰、insert/set 语义细则负例；③ **十种真实修改在 out/eden_v2/project.json 的临时副本上执行（原文件不动，红线④——R3a-MAJOR1）**：copy-of/transpose/quantize/scale/窗删/clip 改/automation 增删/事件插入/轨增删/meta 改全过且 `show diff --json` 可解析+text 非空；④ test_show 盲测用例全绿（脚本退出码 0） |
| **R4 验收** | WP6 命运 + WP7 测试收口 | **W1 命运**：core/smf_import.py、examples/fate/（mid+四要素注记+mapping.json）、examples/gen_fate.py（四断言）、直渲底稿 QC 预检、渲染+QC 迭代（预算 §4.2⑤）、test_smf_import.py、**test_fate_data.py（fast：gen_fate 重跑输出到 tmp 与 out/fate_mvt1 对拍逐字节一致+四断言）/ test_fate_render.py（slow：自渲全链+mix sha 锚定必选+qc ok 断言）** ‖ **W2 收口**：**七组**新测试覆盖审计（对照 §6 矩阵查漏）、三档全量回归、cli stem/master/qc 负例补测（清遗留债务 3）、tests/README.md 漂移修 | ① `out/fate_mvt1/mix.flac` 存在、qc.json `ok=true`（§4.3 阈值，含 normalization_type=="linear"）；② 命令化（双轨终态口径，R4 审查 B·N7 同步）：`bgm show structure --json` 输出 23 轨 = 12 乐器编制×双轨叠置+timpani、`bgm edit undo --list` 非空且含表情层动词记录、`bgm show events --track <弦乐轨>` CC1 事件计数 >0（KS 表情层已按 §10.8 裁定取消）、test_show 盲测以 fate 工程 fixture 复跑退出码 0；③ 三档全绿（或显式 skip 理由）；④ 试听交付（路径+时长+响度数字） |
| **R5 落档** | WP8 文档与决策 | **W 落档**：AGENTS.md 追加 BG-D11..D14 + **§二目录表更新**（core/ 增 smf_import/edit/show 行、descriptors/、.bgm_undo 注记）+ **§四坑表更新**（fast 口径 68 例~26s→294 例~71s、预算 ≤75s（§6 权威口径）、SameFileError 坑转历史注记、out/minimal 与 out/eden_v2 等 gitignored 锚点"新机首跑前置"注记）+ **§五债务表更新**（债务 3 清除划账；债务 4 措辞=防前科重演仅覆盖 gen_fate，gen_eden 双件债务维持）+ **红线①补记**（PD MIDI 入库事实+四要素封存+三四乐章 NC 排除裁定）+ **BG-D9 补注**（边车 `<track>.<engine>.render.json` 与 `.bgm_undo/` 命名族）、REVIEW_LOG.md 全记录（含 §10 执行期发现）、REPORT.md 增 v3 节（命运 QC 数据+crest 处置+署名义务）、README/engines README/catalog 接线、PLAN_v3.md 定稿 | ① 最小抽查清单执行（R3-P11）：BG-D11..D14 逐条对照 §3 对应小节 + `grep -nE 'content_hash_key|event_sort_key|BGM_NO_INCREMENTAL' bgm_gen/engines/base.py bgm_gen/engines/midi_util.py bgm_gen/core/project.py` 命中实现；红线五条逐条列检查命令（许可=assets/manifest grep；ComfyUI=comfyui env 零安装记录；sudo=计划全文 grep 空；旧产物=git status 干净；legacy=test_legacy 绿）；② 全测试终跑三档 |

**BG-D11..D14 决策文本（三轮规划审查定稿；R5 落档照录 AGENTS.md §一）**：
- **BG-D11 操作层**：**五动词=show/insert/set/move/delete**（操作面元语；编辑动词=insert/set/move/delete，复合命令=split/merge/undo）；target 寻址=规范排序索引+窗口谓词；**索引跨编辑会漂移，连续编辑必须每次 edit 后重新 show 取索引**；每动词一 undo 快照点（布局保全，上限 50，undo 前漂移检测，--force 覆盖）；CLI 与 core/edit.py 同校验路径；宿主不封装任何音乐观点。
- **BG-D12 双布局**：spec_version "2" 支持 track 槽位 $ref（相对工程目录、单缝不嵌套、无兄弟字段；装载层版本前置门：v1 拒 events/$ref/params）；v1 零迁移零位变；save_project 原子写（tmp 同目录、键白名单）为唯一正本写回器；render 快照：v1 保持 copyfile、$ref 工程内联展开；增量渲染默认关闭、`--incremental` 显式开启、`BGM_NO_INCREMENTAL=1` 硬闸（读取于 render_project 内）、hash 键=组装后 payload 规范化 JSON+engine/binary_pin/descriptor 三版本+sr/channels。
- **BG-D13 描述符**：引擎能力以声明式描述符（git 版本化 JSON，文档性 schema+手写校验，零新增依赖）为源，三档来源 A 收割（第一事实源=引擎源码 payload 读取行为）/B 起草+探针/C 手写降级（gaps 强制标注，当前无实例）；单字段约束描述符生成、跨字段约束走 invariants 清单；探针=行为探针（exit 0+出参契约+非零产物+determinism 分级）；防漂移=pin（sha=advisory 黄灯）+探针+doctor+升级 diff 四件套。
- **BG-D14 事件流**：track.events 通用事件（cc/pitch_bend/keyswitch/program_change/note_on/off），note 载体与 notes[] XOR（同 pitch 交叠与悬空拒绝）；弯音=semitones+轨级 bend_range（sfz 必显式）；同 tick 全序单一 event_sort_key()：keyswitch→PC（bank 前置复合）→cc→bend→note_off→note_on，三级决胜 (t,类型序,pitch,插入序)；未知类型闭集拒绝；车道=投影视图；引擎消费由描述符声明（sf2 拒 program_change/keyswitch）；控制事件经 payload.events 进引擎，无 events 的 payload 保持旧路径字节不变；**track.params 透传槽承接参数级直通（校验由描述符驱动，组装为覆盖合并）**；payload.events 引入伴随 sfz/sf2 描述符 version bump，envelope spec_version 不变。
- **BG-D15 母前峰值限幅 master.pre_limit**（**R4 仲裁新增**，非规划期草案——R5 落档时随 D11-D14 一并定稿入 AGENTS.md）：v2 schema 声明字段（`{ceiling_db, attack_ms=5, release_ms=150}`）；mixer 确定性 numpy lookahead 限幅器（信号延迟 look-1 使峰值样本入自身治理窗），作用点=premix 求和后；动因与校准记录见 §4.3/§10.8——**实测 ffmpeg linear 判定 binding 约束=measured_LRA ≤ 目标 LRA(11) 而非 crest**（ceiling +3dB 削顶使 LRA 12.4→10.5 转 Linear；ceiling_db 定义在 premix float 域可为正值）。

**终审（R5 后）**：并发 3 名深度红队（契约/红线合规/音乐产品现实性）最终对抗审查——判据：零 MAJOR + 全部 MINOR 有处置记录；**再审 ≤2 轮，仍未清零则带未清零清单交用户裁定（R3-P13）**。

---

## 6. 测试计划

**通用规范**：①未打 fast/slow/service 任一 marker 的用例**收集期 fail**（conftest 纪律检查，元测试锁定）；②**fast 档预算 ≤75s**（v0.93 原定 ≤60s；R1 验收实测 60-66s——构成=旧 68 例 ~26s + dual-layout 渲染组 ~24s + 描述符探针 ~10s + doctor 新探针 ~3s，已实测归因；R2 候选优化：doctor 二进制探测改 session 级缓存，可回收 ~8s）；③env 覆写走子进程 helpers.run(env_extra) 或 autouse fixture + 元测试断言 conftest 注入生效；④增量用例自清残留边车；⑤子进程解释器走 helpers.py3()。

| 文件 | marker | 覆盖 |
|---|---|---|
| test_descriptors.py | fast（synth/sf2/sfz/sample/master loudnorm 探针）+ slow（demucs、master matchering+ref）+ service（ai） | 描述符 schema 自洽；**行为探针（§3.1 语义）**；validate_payload 正负例（单字段+invariants+params）；doctor 一致性（severity/warn） |
| test_events.py | fast | 负例族（XOR 双向/悬空/交叠/vel=0/synth 轨事件/sf2 KS/sf2 PC/v1+events/sfz 弯音无声明/params 未知键·越界·跨引擎错键）；同 tick 全序字节锚点（bank-PC 正例/相邻同 tick 双 KS 错开）；cc half-up+clamp；弯音 14bit 往返；ppq 入参；write_notes_smf .mid 直接 sha；events-only clip 推导；v1 工程 sha 不变；重组装深比较（minimal+baselines 全部+out/eden_v2 只读） |
| test_edit.py | fast | CRUD 正负例（含 $ref 来源标注、跨形式 copy-of 正/负、insert/set 语义细则）；undo 栈+漂移检测负例+写失败自动恢复+上限淘汰+manifest 格式；BGM_CRASH_AFTER 原子写窗口注入；折叠语义；sec 窗换算；rename 四处重写 |
| test_dual_layout.py | fast（纯数据+minimal 规模渲染）+ slow（eden_v2 全量） | $ref 装载/拒绝（绝对路径/嵌套/兄弟字段/**v1+$ref·events·params 版本门**）；split↔merge 语义幂等；save 连续两次字节稳定；split 位级一致（minimal fast/eden_v2 slow）；$ref 快照独立重渲位级一致；增量命中/未命中（仅改 bpm 负例）/默认关闭逐位一致/**边车写入顺序崩溃窗口（stem 已写边车未写→重跑不假命中）**；SameFileError 回归 |
| test_show.py | fast | show 族输出结构断言（structure/notes/cc/events/diff 的 --json schema 与 --text 非空）；show cc 显示编码值；**盲测 pytest 化用例（§3.5 规格：≥3 题型×≥5 题、seed 固定、ground truth 独立 json.load 直算）**；R4 追加 fate 工程 fixture 复跑 |
| test_smf_import.py | fast | SMF 读器：Mutopia 实测锚定（8295/1013 拍/192bpm/384PPQN/13 轨）；running status 合成用例；双 tempo 并列取先合成用例；dur=0 钳制；未配对 off 告警 |
| test_fate_data.py | fast | gen_fate 重跑输出到 **tmp** 与 out/fate_mvt1 对拍逐字节一致（生成器确定性回归——**防遗留债务 4 前科重演：仅覆盖 gen_fate，gen_eden/gen_eden_v2 债务 4 维持原状**）；四断言（KS/移调/键位/静音间隙） |
| test_fate_render.py | slow | 从 examples/fate 自渲全链 → **mix sha 锚定（必选）** + qc.json ok + normalization_type=="linear" |

**回归不变量（轮轮必守）**：①out/minimal mix.flac sha；②w2a **8 条基线**（含新补 master）位级 sha；③eden_track 位级（slow）；④legacy 契约（fast 4 例）；⑤fast 计数只增不减（68→294）且 fast 档 ≤75s（§6 口径）。

**既有测试的唯一预期改动**：test_catalog.py:104-105（docstring→描述符断言+重落盘）；tests/README.md 两处漂移（R4-W2）。

---

## 7. 验收总则（DoD v3）

1. `bgm show engines --json` 呈现全部 7 引擎完整能力面（三档来源、coverage/binary_pin 如实标注）；
2. 通用事件流（cc/pitch_bend/keyswitch/program/note）经 midi_util→sfizz/fluidsynth 全链路出声且 QC 复现；车道=投影视图；
3. 五动词 + show 族全可用，payload/事件/params 由描述符校验——**命令化判据：`grep -nE '"(synth|sf2|sfz|sample|demucs|ai|master)"' bgm_gen/core/show.py bgm_gen/core/edit.py` 零命中（核心层）；cli.py 仅允许命中 v1 既有子命令分发区（白名单=cli.py 现存 :16-56 注册区与 :60-155 handler 区的既有行，以 R1 动工前 git 快照为准）。**豁免注记（R3 审查 B-3/m-5，2026-08-23 裁定）：`"master"` 作为**工程母带段数据键**（BG-D7，与 core/project.py `proj["master"]` 同惯例）的命中属合法——判据意图是禁"引擎分发语境"的硬编码，非工程 schema 键；命中行逐一人审，show.py 的 4 处与 edit.py 的常量定义均属数据键语境**；
4. schema v2 双布局：v1 零迁移零位变、split 后位级一致、--incremental 只重渲变更轨（默认关闭不扰锚点）；
5. 测试全绿（新增八组 + 旧 68 fast 零回归、fast ≤75s；slow/service 绿或显式 skip）；
6. **命运第一乐章交付**：out/fate_mvt1 全套（mix.flac/stems/qc.json ok=true），试听指引+署名义务注记完整——v3.1-v3.3 增量轮实态注记（终审 A·M-1）：产物目录正本=split 布局（tracks/*.json，内联快照机制仍在但该工程未用）；归一化=Dynamic（v3.1 用户双通道授权，Linear 为 v3.0 时点口径）；定稿 sha 9c4e5f43（REPORT §8.7）；
7. 文档与决策落位（BG-D11..D14、REVIEW_LOG、REPORT v3 节、AGENTS 四节更新），终审红队清零。

---

## 8. 风险登记（v3 修订版）

| 风险 | 缓解 |
|---|---|
| **管弦动态 crest>13dB → loudnorm dynamic 回退撞 TP 门** | TP 目标 -1.2 留余量；loudnorm 第一遍预测 crest 前置；超限走声明式母前处理或 target_lufs 下修+注记；test_fate 断言 normalization_type=="linear" |
| **VPO PERF sustain 族无限渲染（R4 冻机事故根因）** | 三重护栏（sfz 引擎输出体积闸/增长停滞 60s/墙钟超时 + measure 流式化 + render stem 时长门）；映射层禁用 PERF sustain 族（§4.2④ R4 裁定）；回归锁 test_sfz_loop_watchdog |
| **key top-2 对管弦 mix 无先例** | 直渲底稿 QC 预检前置暴露实测；失败=记录 top-3/r 值+主线显式批准降级+REPORT 注记，禁 worker 静默改 |
| 描述符漂移（插件升级） | binary_pin 版本（主锚）+sha（advisory）、行为探针、doctor、升级即 diff（四件套） |
| sfizz 1.2.3 对 VPO KS 文件行为不确定 | R2 探针先行（VPO KS 实测 sw_last 语义）；回退判据/记录落点已定义（§4.2） |
| VPO sustain attack 0.4-0.6s（短音糊） | 演奏法策略强制 staccato/KS；dur 补偿惯例进 mapping |
| 增量渲染破坏位级一致性 | 默认关闭+env 硬闸；hash 键含组装后 payload 与三版本；位级比对测试；锚点测试强制绕过+元测试 |
| 双布局迁移事故 | v1 内联兼容零迁移；split 后位级比对；undo 快照布局保全+漂移检测 |
| **编辑验收污染唯一正本**（out/eden_v2/project.json 为 eden_v2 唯一实存工程） | R3 判据③十种修改一律在临时副本执行（红线④）；test_fate_data 重跑输出 tmp；深比较样本只读（R3a-MAJOR1） |
| 同文件并发冲突 | §5 所有权表（cli.py 分区：render 分支 W2/show engines 区 W1/edit 族 R3-W1/show 接线主线轮内完成）；并发 worker 独立 worktree，轮末主线合流 |
| Mutopia MIDI 机械化 | 表情层由 AI 施加；实测参数锚定（§4.1） |
| 低音提琴写谱高八度听感塌层 | mapping transpose（Cb=-12）+ gen_fate 断言 |
| QC silent_window 撞戏剧休止 | 阈值工程级 2.5s+§4.2③ 第四断言预警（机械底稿谱面间隙 0.16-0.6s，安全边际大） |
| GPU 被占 78% | 命运工程零 GPU；slow 探针排队属设计行为 |
| 大谱表工程体积 | 双布局分片；JSON ~1-3MB 无碍 |
| 上下文/时长预算 | worker 提示词自带本文档+任务书；reviewer 判据命令化；命运渲染预算 §4.2⑤（单轮 ≤3min/总量 ≤40min）；单轮修复循环 ≤2 次超限升级 |

---

## 9. 明确不做

不做听感/播放；不做音乐观点封装；不加新引擎；不依赖二进制运行时自述；不强制单/多文件；不为引擎写专属参数枚举；**不做 tempo 曲线**（恒 bpm，rubato 以分数拍错位近似——v3.1 候选）；**不做事件 id 字段**（C4 权衡）；**不做 RPN/NRPN 复合事件**（v3.1 候选）；**不承诺三四乐章**（无干净许可机器源）；不改 legacy 五件 argv/cwd 契约（红线⑤）；**write_smf/write_notes_smf/fluidsynth_render 及 sfz 渲染入口的旧路径签名与行为冻结**（R3a-#10）；**增量渲染不做缺省开启**；**不做音质探针**（描述符探针=行为探针）；**零新增 pip 依赖**（base env 禁装 jsonschema 等）。

---

## 10. 审查记录（三轮对抗式审查 + 终审，滚动追加）

### 10.1 规划审查 R1（2026-08-23，契约红队 + 行业对照官，并发）

**审查者 A（契约红队）**：fail → 修复后可进。**审查者 B（行业对照官）**：pass-with-fixes。
**MAJOR 处置（12 条）**：M1 增量默认关闭+硬闸+元测试；M2/F7 hash=组装后 payload+三版本+仅改 bpm 负例；M3 投影规范四条+notes optional；M4 载体转换+vel≥1；M5 轨级 bend_range+clamp/half-up+实测回填；M6 快照内联展开+独立重渲测试；M7 钩子集封闭+R1 保持 if/elif+数据化移 R2+深比较锁；M8 C12 源码第一事实源+结构化类型+invariants C13；M9/F11 实测订正 1013 拍/192qBPM/5.28min；F2 bank-PC 复合规则+锚点正例；F10 mapping transpose+断言；R2 前置 master 基线。全部落位。
**MINOR 处置（20 项）**：F1/F3/F4/F5/F8/F12/F14/F15（8 项）+ m1..m12（12 项）——已修入对应章节。

### 10.2 规划审查 R2（2026-08-23，工程可行性官 + 测试验收官，并发）

**两位审查者均判 pass-with-fixes**（架构挂载点逐行核实全部真实存在；命运管线时长经仓库证据外推现实可行；混音链 float32 无削波硬伤；helpers.run(env_extra) 已存在）。
**MAJOR 处置（7 条）**：Feas-M1 cli.py render 分支归 R1-W2；Feas-M2 content_hash_key 归 W1 交付 W2 调用；Feas-M3 payload.events+编码合并+描述符同步入 R2；Test-T1 TP -1.2+crest 预案+linear 断言；Test-T2 marker 分层+fast ≤60s 预算；Test-T3 行为探针语义定义；Test-T4 五处测试锁定补齐。全部落位。
**MINOR 处置（24 项，含 2 组合并）**：m-1..m-11（m-10/T6、m-11/T2 合并）+ T5/T7/T8/T9/T10/T11/T12/T13/T14/T15/T16/T17/T18——已修入对应章节。

### 10.3 规划审查 R3（2026-08-23，红线合规官 + 终审一致性官，并发）

**两位审查者均判 pass-with-fixes**（红线①②③⑤实质合规、BG-D1..D10 零冲突；行号级事实断言抽查全部精确、五轮依赖图无环、QC/风险/DoD 阈值互洽、核心数字链条自洽）。
**MAJOR 处置（5 条，全部修入本版 v0.93）**：
| 编号 | 问题 | 处置落点 |
|---|---|---|
| 红线-MAJOR1 | R3 判据③就地执行将污染 out/eden_v2 唯一正本（红线④） | 判据③改临时副本执行+test_fate_data 输出 tmp+深比较样本只读（§5/§6/§8） |
| 红线-MAJOR2 | R5 落档清单漏 AGENTS 债务表/坑表/红线①补记/BG-D9 补注 | §5 R5-W 清单四项补齐 |
| P-1 | "五动词"口径全文矛盾（会固化进 BG-D11） | §3.0 术语口径统一：五动词=show+四编辑动词；C7/BG-D11 同步 |
| P-2 | R3 轮内三方协作接口未声明（接线时序/undo 栈格式/test 归属） | 接线=主线轮内交付；manifest 栈格式契约；show cc 用例移入 test_show.py（§3.4/§3.5/§5） |
| P-3 | "payload 直通"参数级在编辑面无 schema 落点 | §3.6 params 透传槽（校验/组装/编辑面/测试全链）；BG-D14 补记 |
**MINOR 处置（26 项）**：红线 #3（债务 4 措辞）、#4（harvest_log 纪律）、#5（零依赖声明）、#6（署名义务定性对齐）、#7（盲测落点）、#8（DoD3 白名单）、#9（D6 版本化注记）、#10（legacy 冻结点名）；P-4（边车崩溃窗口用例）、P-5（七组审计）、P-6（计数订正：R1 20 项/R2 24 项）、P-7（版本前置门+负例提前 R1）、P-8（KS tick0 边界+同 tick 错开）、P-9（duration 300）、P-10（R4 判据命令化）、P-11（R5 抽查清单）、P-12（DoD3 grep 范围收敛）、P-13（修复循环上限）、P-14（marker 元测试判据⑨）、P-15（test_show.py+盲测 pytest 化）、P-16（494 行口径/8 条基线/23.35s）、P-17（指代改 §4.2③）、P-18（范围确认提交用户）、P-19（worktree 并发机制）、P-20（insert/set 语义细则）、P-21（C 档定义）——全部修入。

- [x] 规划审查 R1（契约/行业）—— 12 MAJOR + 20 MINOR 处置
- [x] 规划审查 R2（可行性/测试）—— 7 MAJOR + 24 MINOR 处置
- [x] 规划审查 R3（红线/一致性）—— 5 MAJOR + 26 MINOR 处置
- [x] **用户放行（2026-08-23：确认执行，验收范围=第一乐章完整）**
- [x] 执行期 R1（地基：描述符 + 双布局）
- [x] 执行期 R2（通道：事件流 + params + track_projection 数据化）
- [x] 执行期 R3（操作：五动词 + show 族）
- [x] 执行期 R4（验收：命运第一乐章 + 测试收口）—— 双审查官 pass-with-fixes（0 MAJOR），11 项 MINOR 全修复（fb75263/e5070ed），命运成品交付（§10.8）
- [x] 执行期 R5（落档）—— 文档与决策归档（§10.9）
- [x] 执行期 v3.5（声部离散+乐句台阶，§10.14，dfe1832）
- [x] 终审深度红队（2026-08-24 三路并发 A 契约/B 红线/C 音乐产品：全部 PASS 零 MAJOR；B 零 MINOR、C 三项文档 MINOR 修复 b5ba37c、A 两项 M 修复=DoD6 实态注记+ResourceError 负例；判据"零 MAJOR+MINOR 全处置"达成。原顺序裁定注记：先迭代后终审）
- [x] 增量轮 v3.1 表情迭代（2026-08-23/24 收官，§10.10）
- [x] 增量轮 v3.2 空间化机制（2026-08-24 合流，§10.11）
- [x] 增量轮 v3.3 空间应用（2026-08-24 收官，§10.12）
- [x] 增量轮 v3.4 资源感知并行渲染（2026-08-24 合流，§10.13；终审仍待发）

### 10.4 执行期 R1 记录（2026-08-23，已放行）

- **前置**：master 基线入 baselines_w2a（8 条）；BGM_TMP_ROOT 进程级隔离（helpers/conftest）；content_hash_key 接口桩入 base.py；双 worktree（v3-r1-w1 / v3-r1-w2，out/ 最小子集拷贝）。
- **交付**：W1 描述符系统（541c222）+ W2 双布局（c34db50）并发完成；合流 main 零冲突（cli.py 自动合并）；三档回归 fast 133 / slow 6 / service 3 全绿。
- **验收**：审查官 A（契约/位级）判据①-⑨ 全过，MAJOR D-1（merge→save 丢显式 bank/program → 位级漂移）→ 主线修复 `_serializable_track` 显式信号兼容 raw dict + bank=128 位级回归用例。审查官 B（描述符/纪律）pass-with-fixes → 主线修复：B1 结构化片段静默穿透兜底（object/array 非匹配值 raise）、D1-doctor 与 base 共享唯一结构检查（engines/descriptor_check.py 上移）、A3 ai.workflow 空值守卫、D-2 save 白名单补 sf2 键、B-1 边车仅增量模式写、C-1 $ref 目录逃逸加固、F1 三个 required 负例、harvest gaps 如实补注收紧面（bpm min=1/bank 128/channel 15/hits=[]）、B2 未知键语义入 schema 说明。
- **预算裁定**：fast ≤60s → ≤75s（构成实测归因；R2 候选优化 doctor 探测 session 缓存）。
- **R2 顺带候选**（记录在案，不阻塞）：harvest.py 改名 `_harvest.py` 消 RuntimeWarning；show engines text 视图 gap 标注；引擎 docstring payload 段指针化；synth params 键第三份拷贝收敛；增量 hash 含资产内容 sha（v3.1）。

### 10.5 执行期 R2 记录（2026-08-23，已放行）

- **交付**：单 worker（6aab91a）：event_sort_key/events_to_smf/notes_to_events + 工程层事件校验（XOR/配对/交叠/能力门/bend_range 声明）+ params 透传校验（投影锁定集）+ track_engine_spec 描述符数据化（四钩子）+ descriptors sf2/sfz v1.1.0 + test_events 34 fast/4 slow。fast 174 / slow 全量 10 / service 3 全绿。
- **验收**：审查官 A（编码契约）判据全过，MAJOR A·1（排序主键=浮点 beat → 同 tick 掐音头，字节级复现）→ 已修（主键=编码 tick + note_off 按 _on_t 公式）+ 回归测试；MINOR A·2/A·3 已修。审查官 B（校验语义）判据全过，MAJOR G1（PLAN §4.2④ "VPO sustain CC1 驱动"虚假声明）→ 已修（§4.2④ 实测纠偏 + 本记录）；MINOR A1（NaN 穿透→isfinite 拒）/A2（synth 嵌套 params 键集工程层校验）/C1（v2 notes 空数组合法）/E1（conftest 清理 >24h 残目录）已修；环境修复：/tmp 残目录 80%→37%。
- **R4 消费的实测三结论**：①CC1 仅 PERF 族生效（SEC-tremolo 走 CC11）——命运动态层选色必遵；②KS sw_last 有效（c2=sustain/e2=staccato 差 >12dB）无需回退；③VPO 弯音未声明 pitch_wheel_range，实测默认 2 半音（bend_range_evidence.json）。
- **任务书矛盾裁定**：sf2 轨允许 note 事件载体（投影为 notes），仅拒 keyswitch/program_change（以 PLAN §3.2 消费矩阵为准；任务书括注笔误，worker 正确裁定）。

### 10.6 执行期 R3 记录（2026-08-23，已放行）

- **交付**：W1 五动词+undo（d57d615：core/edit.py 1505 行 + cli edit 族 + test_edit 29 例）‖ W2 show 族+盲测（cc9c974：core/show.py 599 行 + cli show 叶 + test_show 36 例）。合流 f5b21c9（cli.py 双区手工合流）；fast 242 → 审查修复后 248 / slow 10 全绿；主线集成验证（edit→show diff→undo 字节复原）通过。
- **验收**：审查官 A（编辑/undo 安全）pass-with-fixes：**M-1** 回滚成功被误报"自动回滚失败"+误导 undo --force（会误撤好编辑）→ 已修（成功/失败分支分离 raise）+ 断言收紧；**M-2** NaN/Infinity 可写入工程（工程层 \_num/\_event_num/notes 行/\_parse_num/payload 解析五处无 isfinite）→ 已修全链拒绝 + 回归锁；**M-3** XOR 门 events 键缺席绕过（哑轨可写出）→ 已修 + 负例；**M-4** W1/W2 快照文件名契约断裂（\$ref 工程 show diff 恒 snapshot_missing）→ 已修（读侧扁平名回退）+ 集成测试。MINOR m-1（unlink 幂等）/m-2（OSError 入捕）/m-5（\_MASTER_SEG 还原明文+DoD3 豁免注记）/m-6（diff 数值等值折叠）已修；m-3/m-4（copy-of \$ref 文案/双下划线歧义）与 NOTE n-1/n-2/n-4/n-5 记录在案（低危，v3.1 候选）。审查官 B（检视/盲测）pass-with-fixes 0 MAJOR：B-1 盲测 seed 零覆盖 events-only 轨 → 已修（确定性配额补题）；B-2 doctor 计数脆弱（ComfyUI down 显形）→ 已修（排除"总判定"行，带前导空格）；B-3 DoD3 grep 豁免注记 → 已修（§7-3）。注入实验证实：四类故意缺陷（闭区间/排序键改/投影剥离/音色错位）组合测试网全检出。
- **环境注记**：ComfyUI 于 R3 审查期间下线（service 3 skipped 属设计行为；doctor ai.binary_pin 黄灯不阻断）；demucs 单测复跑通过（GPU 占用波动类 flake 已知）。

### 10.7 R4 资源事故与修复记录（2026-08-23，主线调查）

- **事故**：R4-W1 首次运行期间整机两次冻死（用户硬重启，19:31 重启日志佐证；无 OOM kill 记录=换页风暴形态）。中断现场：`out/fate_mvt1/` 已开始渲染，首个 stem（flute_sus）写出 **9.15GB**（≈14.4h 音频）。
- **根因链（A/B 对照实验实锤）**：R4-W1 按 §4.2④ 原情报选了 `flute-SEC-PERF.sfz` → VPO PERF sustain 族含 loop_continuous 采样（无视 note_off 永续循环），sfizz 1.2.3 对其**渲染不终止**（同一正确 316.7s MIDI：sustain 版正常 56MB 收尾；PERF 版 30s 写出 4.28GB）→ 旧 `measure_wav` 全量加载失控产物（8.5GB 文件 ≈25GB RAM）→ 叠加当时 ComfyUI（12.7GB 显存持有者）+ 输入法 ASR 6.4GB + 双 agent 测试套件 → 61GB 内存耗尽 → zram 风暴冻死。次生发现：PIPE 未读时 sfizz 噪音日志撑爆 64KB 管道缓冲会把子进程堵死在半途（挂起形态）。
- **修复（三重护栏 + 一道编排闸，全部带回归锁）**：① `sfz.py _run_bounded`：输出体积闸（(预期时长+15s)×2 上限，实测拦截真实杀手 payload 于 **1.8s**）+ 增长停滞 60s 挂起检测 + 墙钟超时（预期×4+120s），stdout/stderr 落临时文件绝不接 PIPE；② `base.py measure_wav` 流式分块（常驻内存数十 MB 级，数值口径不变）；③ `project.py render_project` stem 时长门（工程时长+60s 上限）。回归锁：`test_sfz_loop_watchdog_terminates_unbounded_render`（合成 loop_continuous SFZ 秒级拦截+半成品清除）。
- **复验**：fast 249 / slow 10 全绿（w2a 位级基线含 sfz 双例零回归）；真实 flute-SEC-PERF payload 1.8s 拦截、半成品清除、flute-SEC-sustain 不受影响（49.5s 正常出声）。
- **映射裁定**：§4.2④ 已更新——PERF sustain 族渲染期禁用，动态层改 SEC-tremolo+CC11 / PERF-staccato / vel+gain 塑形。
- **运维注记**：/tmp 为 tmpfs（31G，写入即耗内存）——大文件实验一律落 /home 磁盘路径；受控测试统一经 `/tmp/render_guard.py`（进程树 RSS 帽 + MemAvailable 地板 + 越线 SIGKILL）。

### 10.8 执行期 R4 记录（2026-08-23，已放行）

- **交付与合流**：W1 命运工程（c3c67fe：smf_import 231 行 + gen_fate 449 行 + mapping 465 行 + 测试三件 21 例 + sfz 尾音余量校准 15→30s——VPO SEC-sustain 正常尾音实测达 21s，15s 误拦，失控拦截不受影响）‖ W2 测试收口（74ee026：COVERAGE_AUDIT 96 设计点对账 + catalog 重落盘同步锁 F-1 + cli 负例 6 条清遗留债务 3 + README/conftest 漂移修）。零冲突合流（2651b5f/5fe4cdd）。
- **渲染预算订正（§4.2⑤ 原估差 30 倍量级）**：sfizz offline 超实时 ~200×，23 轨全链实测 **38-43s/轮**（原估 ~20min/轮），峰值 RSS ~1.3GB；渲染全程 guard 包裹零险情。
- **失控清单扩展（R2 结论外推禁令再证实）**：VPO SEC-sustain 族失控并非 PERF 独有——oboe/horn/trumpet/viola 四件在本工程音符量下触发 sfizz 1.2.3 失控（单音正常、beat 432 后上下文触发；flute 等 6 件正常）→ 换 VSCO2 CE（CC0）四件。护栏两次秒拦（119MB/159MB 上限触发）。**KS 事件×全量音符同型失控**（clarinet 93 KS×874 音符二分锁定）→ 按回退判据用双轨叠置，KS 表情层取消。
- **W1 上报七项的主线裁定**：①key/bpm FAIL → **判据降级走 schema 声明式正门**（工程 qc 置 null=info 级，证据全文 mapping qc_adjudication + LISTEN.md + 本记录；key=G-G-G-Eb 属音主导+bE 大调第二主题致 KK 结构性偏置、bpm=恒 +3.5% IOI 系统偏差，正确性由乐谱事实源+duration 门独立锁定）；②normalization Dynamic → **按 §4.3 预案第一选项落地 `master.pre_limit` 母前限幅**（新机制：mixer._apply_premaster_limit 确定性 numpy lookahead 限幅器 + v2 schema 声明字段 + 校验/白名单/save 测试 6 例）——**实测校准发现 ffmpeg linear 判定 binding 约束是 LRA ≤ 目标 11 而非 crest**（不限幅 LRA 12.4 / +6dB 11.6 / +4dB 11.1 均 Dynamic、+3dB 10.5 转 Linear；§4.3 "crest 12.8dB" 表述不完整，已注记）；③mixer.py:90 缺陷指控**实证推翻**（run_engine 返回带顶层 detail，normalization_type 解析正常，误报）；④sfz.py 余量 30s **复核批准**；⑤sfizz 一次性非确定实例（VSCO2 TrumpetSus 1/14 次偏差、13 次复现一致）记录在案，stem 自校验列 v3.1 候选；⑥W2 上报：slow 缺输入用例维持 assert-fail-fast（同 test_cli 锚点惯例）、qc 缺输入前置检查落地（f7ba0cc）、doctor 会话缓存落地（helpers.doctor_report_once，fast 73.6→70.0s）。
- **仲裁后定稿**：qc **ok=true**（LUFS -14.0 精确 / TP -3.3 / silent 0.75s / dur 317.812 / **normalization_type=Linear**；key/bpm info 级记录实测值）；test_fate_render 断言更新为仲裁后口径（Linear + info 级 + ok=true）。
- **双审查官验收（均 pass-with-fixes，0 MAJOR）与修复**：审查官 A（命运/音乐产品）6 MINOR——rubato 描述对齐/undo 栈真实计数 50 快照 48 表情动词（两轮表情层）/PLAN §4.2 双轨终态口径/LISTEN 来源标注/母前限幅听感披露（19.14% 样本受抑、最深 -7.05dB@313.6s，试听指引引导检查 ff 尾声）/base 预检产物自 W1 worktree 补拷（fb75263）。审查官 B（契约/测试收口）5 MINOR——**M-2 限幅器对齐 off-by-one 实锤**（延迟 look 而非 look-1，峰值样本不在自身治理窗，最坏块相位单样本过冲 ~7%@12dB 靠硬钳掩盖→已修 look-1 + 最坏相位回归锁 + **重渲**，新 mix.flac sha256 `93cc4967481fa4a6…`，Linear/qc ok 复验不变）；M-1 F-3 命运盲测 fixture 落地（_blind_raw $ref 手卷展开保持独立直算 + 9 题全中）；M-3 范围门负例 4 条；M-4 pre_limit falsy 穿透（{} 拒绝、null=显式关）；M-5 README 计数 294。NOTE-1 cli_negative docstring 过时形态更新。
- **回归与预算口径**：fast **294** passed（空闲桌面 70.6s / 忙桌面 77s——Firefox+ZCode 并行实测 +7~8s 方差，预算 75s 以空闲口径衡量）/ slow 14 passed / service 3 显式 skip。

### 10.9 R5 落档记录（2026-08-23）

本轮只动文档（零代码/测试/schema/mapping/examples 改动；out/ 产物未触碰），改动文件清单：

| 文件 | 落档内容 |
|---|---|
| `AGENTS.md` | §一追加 **BG-D11..D14**（照录本文 §5 定稿草案）+ **BG-D15**（R4 仲裁新增拟文）+ 红线①补记（Mutopia PD 底稿四要素封存 + 三四乐章 NC 排除裁定）+ BG-D9 v3 补注（边车/undo 栈命名族）；§二目录表更新（core 三件 smf_import/edit/show、descriptors/、fate 工程、fate_mvt1 系产物、.bgm_undo/.bgm_val 注记）；§三追加"v3 升级（2026-08-23）"段；§四坑表（fast 294 例/预算 ≤75s 空闲口径、SameFileError 转历史注记、锚点新机首跑前置、v3 五坑：VPO 失控清单/sfizz 非确定实例/fast 预算口径/loudnorm linear 判定/tmpfs 大文件纪律）；§五债务划账（债务 3 清账、债务 4 措辞精确化、新增债务 6 doctor CLI 缓存不对称）；§六指针表加 PLAN_v3 行；日期改 2026-08-23（v3 落档） |
| `docs/REVIEW_LOG.md` | 追加"v3 执行期审查"章：R1/R2/R3/R4 逐轮（交付/审查发现/修复）+ R4 资源事故段——全部事实自 §10.4-§10.8 提炼，数字照抄 |
| `docs/REPORT.md` | 追加 **§八 v3 命运第一乐章交付报告**（QC 全数字表/key-bpm info 降级证据/crest-LRA 处置全程/编制双轨叠置/表情层三通道/渲染耗时/署名义务模板/已知限制）；§⑤ CLI 速查追加 v3 操作面（show 族/edit 五动词/undo/--incremental/target 路径族）；标题行改双成品口径 |
| `README.md` | 新增"v3 操作面"段（五动词/事件流/描述符/双布局/命运指针各一行）；子命令 8→10、fast 口径 294 例/~71s、目录地图 examples/out 行、深入指针 PLAN_v3 行、成品试听行补 fate_mvt1 |
| `bgm_gen/engines/README.md` | 新增"描述符注册表（v3，BG-D13）"段（事实源/运行时/收割与防漂移/呈现 + 指针本文 §3.1）；辅助模块补 midi_util 事件流职责与 descriptor_check/harvest；新增引擎步骤补第 6 步（配描述符） |
| `catalog/timbres.md` | **未改**——盘内活数据有逐行同步锁（test_disk_catalog_fresh_render_sync，R4-W2 F-1），手工追加指针行会打破 fast 套件；改 catalog.py 属代码改动超本轮边界。v3 参数级直通指针已由 engines/README 与 AGENTS §一 BG-D14 承担 |
| `docs/PLAN_v3.md` | 本文件：状态行 v0.93 → v1.0（定稿）；§5 补 BG-D15 定稿注记；R5 复选框勾销；本 §10.9 |

落档后状态：BG-D1..D15 全部入宪法；执行期记录三处互链（PLAN_v3 §10 / REVIEW_LOG v3 章 / REPORT §八）；终审深度红队（§5 终审）为下一步。

### 10.10 v3.1 表情迭代记录（2026-08-23/24，已收官）

- **动因与诊断**：用户试听反馈"缺乏强弱变化和灵动表达，拍子和进行僵硬"→ 主线参考分析 `out/ref_analysis/ASSESSMENT.md`（卡拉扬 1982 BPO 对照，§一 三差距实测：①速度恒 192 无呼吸（8291/8295 音符落 96-tick 网格）；②宏观动态差 5dB（12.4 vs 参考 17.3dB）、乐句弧线被压平；③华彩窗差 11.8dB——"命运换气"未做出；§二 机制支持度 ~75%（缺口=长音内连续渐强，采样器层）、§三 瓶颈在编排大部分可迭代追平）。v3.1 任务书直接引用该文件。
- **交付（2bafe13）六项修复对照三差距**：①速度 192→**144** + **27 段 beat 域分段线性 warp**（全轨共享单调函数，对 notes/events/automation 统一变换；呈示部终止 ritard+fermata / 展开部终点全奏延展 3.67s / **华彩 adagio 0.61×速** / GP 拉宽 1.35s / 终止式渐慢+双和弦 fermata），取代旧 E4 单点 rubato（其 beat 240.5-243 华彩定位经结构实测证伪——本谱为**无反复单程**，真华彩=oboe 独奏 beat 536-544，旧"repeat 已展开"注记一并修正，§4.0）；②**85 关键帧乐句级力度**（三深谷+双高潮+尾声峰 0.92→回收 0.62→终推 0.88，段内实测回收 5.4dB）+ gain 自动化 ×9→**×20dB** + CC1 三通道联动；③**华彩 dolce 沉底**（13 音 vel 覆盖 57-64 + gain 谷，沉底 15.5dB ≥10dB 超额）；④**固定 seed humanize**（stac 微时序 ±0.04 拍，动机群共享偏移防同 pitch 交叠 + 11 乐器散射表 + 拍位/动机头重音）。全部改动落 `examples/fate/mapping.json`（表情数据+音乐注记）与 `examples/gen_fate.py`（warp/塑形逻辑）。
- **失控清单第 5 件**：VPO bassoon-SEC-sustain **@144+warp 非网格上下文 sfizz 失控**（护栏 7.7s 拦截：已写 197MB > 上限 164MB；@192 恒速网格 v3.0 正常）→ 换 VSCO2 同族（CC0）——失控=音色×全量音符**上下文交互**缺陷，随数据变化可复发、非固定音色黑名单（mapping runaway_inventory v3.1 注记）。
- **Dynamic 归一化=用户双通道授权**：LRA 19.2 与 Linear 门（≤11）数学互斥（保 Linear 需压 ff 段 ~8dB、宏观动态回落 v3.0 水平；参考 17.3dB 本身不过此门）→ 用户裁定"响度要求是次要的，可以不做严格限制，最重要的是艺术表达的程度"→ **Dynamic 为 v3.1 正门**（pre_limit ceiling=3.0 维持）。授权链=worker 交互提问授权 + 主线事后当面二次确认；**主线一次误判**该归因为无据而降级"待追认"，经 **0160492** 撤销（诚实留痕，教训入 AGENTS 坑表）。
- **验收（07bf145）**：**MAJOR-1 参考口径修正**——卡拉扬 1982 实为**带呈示部反复**演奏（onset 包络自相关 0.888、深谷簇三处只有带反复能解释）→ 真实参考速度 ≈**174 四分 BPM**（1261 拍/434.9s），旧 139.8 系分母错误；v3.0 差距从"快 36.8%"修正为"快 ~10%"，v3.1 的 144 相对参考实为"慢 ~17%"；**用户裁定保持 144=富特文格勒式宽幅演绎**（同口径传统：富特文格勒 ≈145 / 卡拉扬1982 ≈174 / 克莱伯 ≈178；独立演绎选择，非"贴卡拉扬"）。MINOR-1 限幅披露按实测改写（超阈样本 **0.84%**、271 超阈簇 p95 时长 1.09s、最长持续超阈段 **9.21s@再现 TUTTI**、最深衰减 **-10.31dB**@225.8s fermata——ff 段实质压缩属 Dynamic 正门已知代价；LRA 论据 20.6/17.0 复核成立）；MINOR-2 timpani 补 vel 帽（accent_velocity 传 vel_cap，123-127 越帽 122）；MINOR-3 数字族订正（华彩 10 音（扩展口径 13）/关键帧 86 条/warp 累计延展 31.36 拍=13.06s/全曲 435.36s）。重渲 qc 全绿（LUFS -14.0/TP -1.2/silent 1.55s/dur 437.648s，Dynamic 口径）；fate 测试 10 例绿，新 mix.flac sha `73e1472f…`。
- **复测结论（ASSESSMENT §四/§五，同工具同口径）**：时长 437.6s（音乐终点 435.0s，vs 参考 434.9s +0.6%）；平均 138.4 四分 BPM；宏观动态 12.4→**16.4dB**（贴参考 95%）；微动态 17.5→**21.4dB**；十分位 p50 跨度 9.7dB 非单调（三深谷+双高潮，修"墙到墙"）；华彩窗 S-LUFS -29.5（纯发声段 -33.1）。表情层全部量化指标经收官独立复测成立（偏差 ≤0.3dB）。

### 10.11 v3.2 空间化机制记录（2026-08-24，已合流）

- **交付（d31a464）机制四件**（不碰命运工程，seating 应用留给 v3.3）：
  - `core/space.py`（新）：`make_hall_ir` 确定性厅堂 IR（**splitmix64 整数哈希噪声**——不走 numpy.random（Generator 流跨版本不承诺），纯 uint64 环绕逐位确定且跨平台/跨 numpy 版本稳定；早期反射簇 5-30ms **左右构造性不对称**+晚期去相关指数混响；全局能量归一 Σh²=1；Schroeder 倒积分 **RT60 自测 ±15%** 内建）；`apply_track_space` **深度模型**（预延迟 depth×24ms≈8.2m 声程差 / 电平 -depth×4.5dB / 一阶 HF 滚降 8000→3500Hz 线性随 depth（空气吸收）/ M-S 宽度 side 增益=width/0.3（0.3=中性）——各算子中性点逐位旁路）；`ola_convolve` FFT/OLA 分块卷积（复用 lowpass 扫描的 OLA 手法）。
  - `mixer.py`：**A' 空间化级**插在轨道链 A 与 duck B 之间（无 space 轨完全旁路，位级不变）；`master.space_ir` 声明时 **wet 总线**=全轨送量求和→共享 IR OLA 卷积→与 dry 求和进 C 段（premix 含 IR 尾长，混响自然收尾）；**send_db 缺省 -12+depth×9（越远越湿）**。
  - `project.py`：`track.space{depth 必填 0-1, width 缺省 0.3, send_db 可选}` 封闭键集校验 + **v1 版本前置门拒绝**；`master.space_ir{rt60_s 0.4-4.0, seed 整数}` 校验；save 白名单补 space/space_ir（键缺席结构不落 null）。
  - `schema/project_v2.json` 属性定义 + `tests/test_space.py` 19 例（IR 确定性/RT60 自测/去相关/早期不对称/OLA 对拍直接卷积/深度模型三档单调性/中性点逐位恒等/全链集成/校验负例族）。回归 fast 297 passed（+19）。
- **审收修复（0650e92）四项**：M-1 归一声道口径文档订正（立体声 wet 恒 -3dB）；M-2 小厅病态区 API 守卫（size<12 拒绝，产线不可达仅护直调）；M-3 wet 尾×QC silent 门边界声明入 mixer docstring；M-4 补 ir>block OLA 对拍用例（此前 61 样本用例恰好错过产线路径）。test_space 20 例 + fast 全量绿。
- **合流（50b385b）与纯增量承诺双证**：**无 space 字段工程位级不变**——①minimal 同目录产物 12/12 逐位相等；②fate slow mix sha 锚点复验通过（318s 无 space 工程经改后 mixer 位级不变）；另 wet 全链两次渲染 premaster/wet/flac sha 逐位相等。决策入宪法 **BG-D16**。

### 10.12 v3.3 空间应用记录（2026-08-24，已收官）

- **动因**：用户诊断三症状（无环境声 / 左右完美镜像 / 乐器扁平）→ v3.2 机制的音乐应用层落地。**worker 活锁中断由主线收尾**（卡点=任务书"空闲测量"前置在持续开发机上不可满足——等空闲与开发占用互为因果，用户叫停；成果 95% 已成；教训入 AGENTS 坑表）。
- **交付（bb66cb3）**：`mapping.seating` **富特文格勒式德式座位表**（12 轨 pan 非对称 + depth 纵深 0.28-0.80（弦乐前台→木管中排→铜管/定音鼓后排）+ width 声部宽 0.30-0.50 按人数定宽（一提 18 人最宽，oboe 独奏最窄）；stac/sus 双轨共座位经 gen_fate 透传）+ `master.space_ir` **1.9s 厅堂 seed=5**（纪念第五交响曲；Philharmonie 中频档位下侧，BGM 织体清晰度取 0.1s 下侧）+ 收尾 buffer 5.5→4.2 拍（**wet 尾×silent 门边界实测处理**：轮 1 曾 2.85s FAIL——wet 衰减尾越过 -60dBFS 后 IR 定长残留 ~1.9s 静音；裁至 2.3s，被裁 dry 段 <-60dBFS 听感零损失、湿衰减尾完整保留）。渲染 3 轮 guard 包裹（轮 1 silent 门发现→轮 2 收尾裁剪 QC 绿→轮 3 座位校准定稿）。
- **座位表校准记录**：轮 1 用卡拉扬式（低音右后 +0.55）实测 L/R 仅 0.02dB（右置低音恰好抵消一提左侧优势，指标①不达标）；轮 3 换富特文格勒式低音左后 + 声部宽度非对称达标 1.14dB（教训入 mapping seating.energy_tilt_note；与速度裁定 144=富特文格勒传统同一体系）。
- **空间三指标（ASSESSMENT §六，量化验收）**：①全曲 L/R 能量差 **1.14dB**≥1.0 ✅（左倾=左侧弦乐质量优势 18+12+8 人 vs 16+12 人）；②总混音立体声相关系数 **0.03**<0.90 ✅（基线 0.30——"完美镜像"症状的可闻实质=声部层扁平/无环境声而非左右波形相同，本指标从 0.30 起步非 1.0）；③末和弦后衰减尾 RT60 **1.95s**（premaster 尾段 dB 线性拟合 R²=0.994；门 1.9s±40%=1.14-2.66 全带覆盖）✅——wet 尾真实存在且斜率=厅堂 RT60。
- **音乐指标回归（不劣化 >0.5dB 口径，同工具复测）**：宏观动态 16.6→**17.4dB**（§四记录 16.4 与复测 16.6 系口径差）、微动态 22.0dB、十分位跨度 11.0dB（形态完整、对比更深）；华彩沉底 15.5→14.6dB（混响回填 +0.7dB 超预算 0.2-0.4dB——独奏在厅中必激发厅堂，≥10dB 要求仍超额 4.6dB，音乐判断保留）；尾段回收 5.4→**6.9dB**；个别谷段位移 -1.1dB 方向为更静（depth 后排电平衰减）非混响填谷，loudnorm 归一后形态对比反而加深。
- **QC 定稿（v3.3）**：ok=true，LUFS -14.0 / TP -1.2 / silent 2.3s / duration **439.036s**（437.106 dry + 1.93 IR 尾）/ normalization=**Dynamic**（用户 v3.1 裁定沿用）；限幅实测超阈 0.466%（v3.1 0.84%——depth 电平衰减使峰密度降）、最深 -10.00dB。新 mix.flac sha256 `9c4e5f43ba5e…`。
- **验收三 MINOR 口径注记（ASSESSMENT §6.7，修复=口径注记入档）**：①限幅受抑比例双口径（限幅器增益曲线内部 21.0%（含 lookahead 对齐前帧）vs 独立复测帧/元素口径 19.2%，两数同量级、结论不变，引用注明口径）；②RT60 拟合窗（单窗 1.95s / 多窗敏感带 1.79-1.93s，中心窗 R²=0.99425，门全带覆盖）；③-60dB 首达时点 1.54s（§6.1 的 1.65s 为含帧化粗口径）。
- **测试**：fate 11 例绿（data 7 + render 4，含新增座位断言）；**fast 预算找补**=增量用例组换 2 轨微工程（315 例 75.3s 负载口径，预算 18.10→11.67s 回收 6.4s）；gen_fate 重跑逐字节一致 + 全链重渲 sha 位级一致（test_fate_render 4 例慢档全绿）。

### 10.13 v3.4 资源感知并行渲染记录（2026-08-24，已合流）

- **动因**：§10.7 冻机事故的资源纪律（宁可欠利用，不可冻机）——61GB 内存耗尽 zram 风暴冻死的前科使"资源感知"成为并行化的第一优先级。
- **交付（6b66f40）**：`core/resources.py` 资源层——`probe()` 静态探测（进程内缓存：cpu 线程/内存总量/GPU）、`mem_available_gb()` **实时读 /proc/meminfo MemAvailable，每次现读绝不缓存**（缓存会让门控对本机其他进程内存涨落失明）、`plan_workers()` 并发规划纯函数、`DispatchGate` 派发实时门控、`run_pool()` ThreadPoolExecutor 驱动器（结果按任务序收集，与完成顺序无关）；**三开关** `BGM_NO_PARALLEL=1`（硬关走旧顺序路径，读取点在 run_pool——镜像 BGM_NO_INCREMENTAL 模式）/`BGM_MAX_PARALLEL=N`（与硬帽取 min 只能更小，非法值报 ResourceError）/`BGM_MEM_FLOOR_GB=X`（内存地板覆盖）。**并发公式**：workers = min(⌈(avail−floor)/per_task⌉, ⌊cpu×0.5⌋, 硬帽 8, n_tasks)，保底 1；**floor=max(6GB, 总内存×20%)**。**stem 循环与轨链循环池化**（GPU 引擎按 BG-D8/D10 **排除池外**，池成员=synth/sf2/sfz/sample+track_chain；增量 hash 主线程派发前算/命中不占槽；B duck/C 求和母带/lowpass numpy 保持顺序）；per_task 表=render_guard 实测峰值 RSS×**1.5 保守系数**落表（0.5GB 档/track_chain 0.3GB）。**确定性=并行≡顺序**（BGM_NO_PARALLEL=1）minimal 同目录全产物 12/12 含 qc.json 逐位相等 + test_cli sha 锚点隐式锁定；加速实测 sfz16 夹具 7.7→2.6s（**2.97×**）/sfz6 1.81×，峰值 RSS 0.18GB；test_parallel 16 例 + fast 全量 314 通过 0 失败（84.8s 忙载）。
- **验收修复（58aad63）两修**：M-1 `DispatchGate.acquire` 检查与递增并入同锁段（原 check-then-increment 有 **TOCTOU** 窗口，多线程同时 acquire 可瞬时超发；现役单派发线程不受影响，收口防未来复用踩坑）；M-2 cli render 捕获 ResourceError（BGM_MAX_PARALLEL 非法值/门控超时不再裸 traceback，实测 exit 1 干净报错）。
- **合流（c1cb676）**：确定性验收**三组独立对拍 12/12+15/15 逐位相等**；GPU 排除池外 + 增量交互保持；实测 16 轨 sfz **2.97×** / sf2 **1.44×**。决策入宪法 **BG-D17**。
- **Amdahl 如实记录**：命运工程实测（持续开发机忙载）仅 **1.10×**——瓶颈=空间化顺序段（wet 总线 OLA 卷积与轨链依赖未并行）+ 外部负载；夹具微工程收益大（2.97×）而大工程顺序段占比高。**空间化段并行列 v3.5 候选**（AGENTS 债务 7）。

---


### 10.14 v3.5 记录（2026-08-24，声部离散+乐句台阶，已放行）

- **动因**：用户听感双诊断（对照参考+AI 音频模型 music-flamingo+5s 块硬测量三通道证实）——①声部离散缺失（"一个个独立的琴"，VPO 独奏采样一人一轨）；②乐句力度台阶缺失（参考 p75=5.3dB/占比 33%/开场交替，我们 2.4dB/18%/平滑）。
- **交付**（dfe1832）：players 层叠 23→55 轨（弦乐 3-4 人/木管 a2 双人；Δt ±8-15ms + 微失谐 ±5-9¢【pitch_bend+bend_range 实现，32/32 声明】+ Δgain 含 −10log10(K) 归一 + 组内 pan 散布；VSCO2 换琴做音色散布）+ 乐句块表（70 细档 vel/CC1 + 25 粗档 gain 阶跃，保护区零块）。
- **指标**：台阶 p75 2.7→4.1dB、开场交替 2→7（=参考）、占比 25.6%（门 28% 差 2.4pt——premaster 实际 37.2% 超参考 32.9%，Dynamic 母带逐帧追踪吃掉，验收官独立重放归因链证实，用户正门固有代价四处披露）；离散代理峰簇 4→6、拍频能量 +31%；模型复听转向"声部群/groups"。
- **主线追认**：pre_limit 撤除（BG-D15 机制保留在库，命运工程不再声明——三段归因+ceiling 扫描+撤除回收实测，TP 由 Dynamic 兜底 -1.2 不变）。
- **失控清单 +3 件（第 6-8）**：第 7/8 件=同乐器跨演奏者一通一失控（"数据敏感非黑名单"最强实证）。
- **验收**：pass-with-fixes 0 MAJOR（全部可测声称独立复现含 165 stems 全链重渲 sha 全等）；2 MINOR+1 NOTE（mapping 注记同步）已修。

---

## 11. 附录：调查证据索引

**仓库侧**（2026-08-23 实测，R2/R3 审查逐行复核）：代码地图（7 引擎挂载点行号表）、schema v1 全结构、assets.json 18 条、VPO 454 sfz 乐器全清单（timpani 5 变体等）、fate_motif 草稿、测试 73 例逐文件盘点、sfizz_render --help 实测、mixer/master 链 float32 核实、base env jsonschema 缺席实测——已内化于 §2.1/§2.3/§6；环境核验见 §0。

**行业侧**（联网，来源 URL 已由调查代理逐条附验）：
- 描述符：LV2 core spec + units 扩展（drobilla.net / lv2plug.in）、CLAP 头文件（github.com/free-audio/clap）、VST3 ParameterInfo（steinbergmedia.github.io）、ComfyUI nodedef（docs.comfy.org/specs/nodedef_json）+ 本机 /object_info 实证、fluidsynth settings API（fluidsynth.org/api）。
- 事件：SMF 格式（CCRMA/Somascape 交叉验证）、MIDI 2.0 UMP（midi.org）、VST3 IEventList 无序教训（KVR）、LMMS #4437、CLAP events.h 排序硬契约、MusicXML sound dynamics 官方公式（w3.org MusicXML 4.0）、bank-PC 先后惯例（Roland/Sweetwater/Kurzweil 手册）。
- 双布局：OpenAPI $ref（swagger.io/learn.openapis.org）、Godot tscn ext_resource/Unity guid、LMMS 绝对路径断链（lmms.io/forum #30764）、Ardour session 手册、REAPER State Chunk Definitions。
- 操作面：ReaScript SDK（reaper.fm）、Ableton LOM（docs.cycling74.com + midiremotescripts 社区版）、FL Studio MIDI Scripting 手册、music21 用户指南、pretty_midi ISMIR 2014 论文、abjad TENOR 2015、Strudel/Sonic Pi。

**素材侧**（联网+两轮实测下载解析，R1 审查代理复核）：
- Mutopia Symphony5_1：mutopiaproject.org/ftp/BeethovenLv/O67/Symphony5_1/（piece-info id=941，"Copyright: Public Domain"）；文件实测 74649 字节 / format 1 / 13 轨 / 384 PPQN / 8295 音符 / 1013 四分拍 ≈506.5 小节 / 恒 192 qBPM / 力度恒 90、零 CC/弯音 / 定音鼓音域 43..48 / 低音提琴写谱高八度（同度写谱 417 次）。第二乐章 Symphony5_2 同许可可得。
- VPO 实测：KS 文件 sw_last 语义（1st-violin-SEC-KS-C2：12 组 sw_last + sw_default）；KS 键区逐乐器避让音域（弦乐/小号/长笛 C2-F2 区，圆号/大管/大提琴 C5/C6 区）；bass 组 lokey 下探 c1（发声高音编键）；license.htm 复合许可全文。
- IMSLP：imslp.org/wiki/Symphony_No.5,_Op.67（Breitkopf 1862 PD 扫描=校对源）。
- 排除（许可不干净）：kernScores/CCARH（CC BY-NC-SA 4.0）、kunstderfuge（NC）、Project Gutenberg #156（Copyrighted）、IMSLP 合成录音（CC BY-NC 3.0）；music21 corpus 无贝多芬交响曲（实查仅室内乐）。
- 规模权威：IMSLP 乐章表（502 bars）、Wikipedia（2/4、二分音符=108、编制、5-8 min）。
