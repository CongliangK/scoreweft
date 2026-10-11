# bgm_gen 测试套件（v3 R4 收口，PLAN_v3 §6 测试计划 / AGENTS §四）

五层测试 + 三档 marker（`fast` / `slow` / `service`）。**默认只跑 fast 档**
（slow/service 自动记 `deselected`，不静默混跑）；`-m` 显式选档。
**marker 纪律**：未打三档任一 marker 的用例**收集期直接 fail**（conftest
`pytest_collection_modifyitems`，元测试 `test_marker_discipline_collection_fails_on_unmarked` 锁定）。

## 运行方式

```bash
# cwd 必须是工作区根（bgm_gen 的父目录：<仓库根>）
cd scoreweft  # 进入克隆目录

python3 -m pytest bgm_gen/tests -q                          # fast 档（默认，347 例，实测 ~67s；12 skip=6 分家缺件+6 位级版本门）
python3 -m pytest bgm_gen/tests -q -m slow                  # GPU 引擎冒烟
python3 -m pytest bgm_gen/tests -q -m service               # ComfyUI 依赖项
python3 -m pytest bgm_gen/tests -q -m "fast or slow or service"   # 真全量三档
```

> **`-m ""` 陷阱**：空串经 conftest 判空后落入"默认只收 fast"分支
> （= fast-only），**不是**全量三档；真全量必须写 `-m "fast or slow or service"`。

本地验证环境 `python3` = miniconda base（含 numpy/pytest）；新环境应自行安装依赖并确认解释器，不要盲用缺少 numpy 的系统解释器。pytest 未装时：
`python3 -m pip install pytest -i https://pypi.tuna.tsinghua.edu.cn/simple`。

> \* slow 实测含 ~120s BG-D8 显存闸等待（ComfyUI 常驻占 91% 显存时，demucs
> auto 档等待/降级 CPU 属设计行为）；显存空闲时本档 ~30s。

## 三档语义与 skip 记账

| 档 | 内容 | 服务不可达时 |
|---|---|---|
| fast | 资产 manifest 校验 + 确定性引擎基线回归（baselines_w2a 8 条，v3 R1 补 master）+ CLI 端到端与负例 + QC 测量器回归 + 旧脚本回归 + **v3 七组**（描述符探针/事件流/编辑动词/双布局/show 盲测/catalog 同步锁/cli 负例） | 不依赖任何服务，恒可跑 |
| slow | demucs 10s 四分轨（stem RMS 对 baselines_w2b 下限）+ master loudnorm（ebur128 复测 -14±1）+ v3（demucs/master matchering 探针、VPO CC1/弯音/KS 探针、sf2 params.gain、eden_v2 全量 split 位级） | 不依赖 ComfyUI；无 GPU 时 BG-D8 自动降级 cpu |
| service | ai 引擎 8s 小工作流（wf_ace15 + duration=8）+ gen.py 冒烟 + v3 ai 探针（注入点被 /object_info 接受） | **显式 `pytest.skip` 计入摘要（`N skipped`），绝不静默当绿**；默认跑法下记 `N deselected` |

## 位级基线与冻结外部版本（版本门控 skip，用户裁定 2026-10-11）

位级哈希锚点（`out/minimal/mix.flac`、`baselines_w2a` 的 `sha256`、harvest
事实表的 binary_pin）的字节由外部工具参与产出（ffmpeg 终编/flac 编码/解码、
libfluidsynth sf2 渲染），**只对描述符 binary_pin 冻结的版本有效**
（ffmpeg 8.1.2 / FluidSynth 2.5.4，单一事实源 = `engines/descriptors/*.json`，
harvest verify 保证与事实表一致）。

`helpers.skip_if_binary_version_drift(...` 版本门：实测二进制版本（`ffmpeg
-version` / `fluidsynth --version` 子进程解析，与 doctor/harvest 同口径，会话级
缓存）≠ 冻结 pin 时，相关**位级哈希断言段显式 skip**——reason 钉死格式
「检测到 X 版本 A≠冻结 B，位级基线仅对冻结版本有效（安装 pin 版本或重采基线后
恢复严格断言）」，计入 `N skipped` 摘要，**绝不静默当绿**；版本匹配时静默放行，
位级断言照常严格执行。探测失败（二进制缺失）不 skip——测试自然失败，如实暴露
环境问题。**门控范围=仅位级哈希断言段**（红队复审 m-1 收窄，2026-10-11）：出参
契约/sr/channels/时长/RMS、QC 判定、渲染成功性、SameFileError/硬闸/快照自包含
结构断言、harvest 静态深一致与 sfizz sha/size pin **无条件执行**；mix 全链锚点/
sf2 基线 = fluidsynth+ffmpeg 门、master 基线 = ffmpeg 门；synth/sample/sfz 基线
不依赖这两个版本化二进制，恒严格执行——漂移破坏其字节属**新漂移证据**，必须
如实失败）。

**版本不符时的显式 skip 属预期行为**（存量位级基线对外部工具版本敏感是已知
事实，如 FFmpeg 8.1.2→8.1.3、FluidSynth 2.5.4→2.6.0 升级曾致 7 例位级断言
失败）。恢复严格断言的两条正路：①安装回 pin 版本（描述符登记的冻结版本）；
②认可新版本并**重采全部位级基线**（重渲锚点 + `harvest` 事实表更新 +
`baselines_w2a` 重录，配套提交说明）。**不许**为凑绿改基线哈希值或删断言。

## 前置服务清单（不依赖外网）

1. **fast/slow**：近零前置——唯一例外：test_cli 的 sha 锚点依赖
   `out/minimal/mix.flac`（仓库根 out/，被 .gitignore），**新机/清空 out 后首跑需先
   `bgm render examples/minimal.json -o out/minimal` 生成锚点**。
   权重已离线缓存（`HF_HUB_OFFLINE=1` 路径已验证）；
   ffmpeg/fluidsynth/sfizz 由 `bgm_gen/runtime.json` 指向本地路径。
2. **service**：ComfyUI 常驻 `http://127.0.0.1:8188`（`按 ComfyUI 官方说明启动本地服务`，
   conda env comfyui）。未启动 → service 档全量 skip（摘要计数）。
3. 解释器分档（BG-D3）：demucs/matchering = `<独立环境>/bin/python`；
   其余 = miniconda base。均登记在 `runtime.json`，测试经 `helpers.py` 读取，
   **不信任 `sys.executable`**（直呼环境会被宿主 AppImage 劫持，R3 实测坑）。
4. 代理（HTTPS_PROXY（由使用者自行配置） / hf-mirror）只在下载期需要，测试期不需要。

## 分层用例与断言口径

v1 既有（R4 首交付）：

| 文件 | 用例数 | 断言口径 |
|---|---|---|
| test_assets.py | 30 | manifest 15 条：license 非空且白名单命中（CC0/MIT/Apache/BSD/GPL/LGPL/ISC/GeneralUser）；driver 非空且与 runtime.json 登记项存在性一致；relpath 解析 assets_root 后存在 + size 偏差 ≤1%（目录按普通文件求和、排除符号链接——防 rpm .build-id 假象）；`_meta.count`==条目数 |
| test_engines.py | 10(fast) + 2(slow) + 1(service) | fast：baselines_w2a **8 条**逐条重渲，sr 相等、duration ≤0.1s、rms ≥ assert_rms_floor_db（≥3dB 余量）、出参契约 7 字段 + default_out 解耦 + **sfz loop watchdog**（VPO PERF sustain 无限渲染护栏回归锁，§10.7 事故）；slow：demucs 4 stems 存在非零 + 活跃 stem RMS 下限（vocals 基线 null→只验存在）、master ebur128 复测 -14±1；service：ai 8s（免 RMS，只验 sr=48000/时长/非静音） |
| test_cli.py | 9 | render examples/minimal.json 端到端：产物齐 + qc.json ok=true + **mix.flac sha 与 out/minimal/mix.flac 逐位一致**（确定性锚点）；负例 4 条（spec_version/notes 3 元/clip 越界/未知字段）exit≠0 + stderr 含字段路径 + 无 Traceback；engines/render-engine/doctor 冻结复验 + doctor 呈现层（默认表格/--json 一致） |
| test_qc.py | 5 | bpm_check：78BPM 节拍器（16 拍 + ±15% 幅度抖动 + 轻底噪破坏 IOI 并列）→ top-3 含 78±3 或 0.5/2 倍频；key_check：D3/F3/A4 持续 4s → top-1 r≥0.70 且 top-2 含 D minor；无声窗（尾部 2s 静音测 1.9–2.1s）；ebur128（loudnorm I=-20 校准复测 ≤0.5）；hf_ratio（220Hz 正弦 <0.01） |
| test_qc_gating.py | 7 | QC 门控正负例（R4 审查 MAJOR-1 补）：bpm 门 pass/fail、调性门（声明 key 须 top-2 命中——严格语义）pass/fail、duration_min_s 门、hf_ratio 门双侧、sr 不齐 fail |
| test_eden_repro.py | 1(slow) | eden_track 全链位级复现：/tmp 副本重渲 → mix.flac 与交付 sha 逐位一致（c0b245f8…）+ bass.duck stem 抽验（终审 MAJOR-1 补：mixer 的 OLA lowpass 扫描/pan 表达式/exp 曲线数值路径锚定） |
| test_legacy.py | 4(fast) + 1(service) | gm_lofi（42.7s±1 / -37.3dB±1）、demo_lofi（39.4s±1）、midi2wav（6s 级 wav）、key/bpm_check 对旧产物冒烟；gen.py（service）exit 0 + 产物存在（AI 免 RMS）。全部在临时 cwd 跑，不碰包内旧产物 |
| test_catalog.py | 6 | 四源扫描计数（synth 6/sf2 双源/GM 128 表/sfz 四库对磁盘独立复数/sample 三源）+ payload 段由描述符驱动（参数名全出现）+ **盘内==fresh 渲染同步锁**（R4-W2 F-1：描述符改动须 `catalog --write` 重落盘，日期行归一） |

v3 新增七组（PLAN_v3 §6 矩阵，覆盖审计见 [COVERAGE_AUDIT.md](COVERAGE_AUDIT.md)）：

| 文件 | 用例数 | 断言口径 |
|---|---|---|
| test_descriptors.py | 57(fast) + 2(slow) + 1(service) | 描述符 schema 自洽（id 唯一/enum 必伴 stepped/消费矩阵/invariants 双向锁/coverage 三档）；validate_payload 正负例 + validate_param_value（params 槽单键）+ content_hash_key；行为探针（exit0+出参契约+非零产物+确定性）；doctor severity/warn 黄灯不拉红 |
| test_events.py | 36(fast) + 4(slow) | 负例族（XOR 双向/悬空/交叠/vel=0/能力门/sf2 KS·PC 拒/v1+events/弯音无声明/params 错键族）；同 tick 全序字节锚点（bank-PC/双 KS 错开/note_off vel=0）；cc half-up+clamp；弯音 14bit 往返；ppq 入参；write_notes_smf .mid 直接 sha（红线⑤）；events-only clip 推导；重组装深比较；slow=VPO CC1/弯音/KS 探针 + sf2 params.gain |
| test_edit.py | 32(fast) | 五动词 CRUD 正负例（$ref 来源标注/insert·set 语义细则/跨形式 copy-of）；undo 栈 manifest+漂移检测+--force+写失败自动恢复+上限淘汰；BGM_CRASH_AFTER 原子写窗口；折叠顺序 transpose→scale→quantize；rename 四处重写；eden_v2 十修改临时副本；NaN/XOR 回归锁 |
| test_dual_layout.py | 17(fast) + 1(slow) | $ref 装载/拒绝族（绝对路径/嵌套/兄弟字段/v1 版本门四键）；split↔merge 幂等+save 字节稳定+显式 bank 位级；split/$ref 快照位级一致（minimal fast/eden_v2 slow）；增量命中/改一轨仅重渲/仅改 bpm 全未命中/边车崩溃窗口/默认关闭逐位；SameFileError；conftest 纪律元测试×2 |
| test_show.py | 39(fast) | show 族结构断言（structure/notes/cc/events/diff 的 --json schema + text 非空）；show cc 编码值 half-up（text 只显编码值）；events 规范序=event_sort_key 共用；**盲测 pytest 化**（3 题型×6 题、seed 20260823 固定、ground truth 独立 json.load 直算） |
| test_cli_negative.py | 6(fast) | stem/master/qc 负分支（AGENTS §五.3 遗留债务 3 清除）：exit≠0 + stderr 可定位 + 无 Traceback |
| test_smf_import.py / test_fate_data.py / test_fate_render.py | fast + fast + slow | **R4-W1 交付，主线合流后入位**：Mutopia 锚定/running status/双 tempo；gen_fate 确定性对拍+四断言；自渲全链 sha 锚定+qc ok |

产物全部落 `/tmp/r4smoke_<pid>/`（**BGM_TMP_ROOT 进程级隔离**，conftest 注入；
并发 worker/审查者互不共享；>24h 陈旧残目录启动时自动清理）。baselines 两 JSON
是断言的单一事实源，**只读**；基线漂移 = 引擎回归，不许改基线凑绿。

## v3.4 资源感知并行（test_parallel.py，16 例 fast）

并行对象与资源层（`bgm_gen/core/resources.py`；PLAN_v3 §10.7 冻机事故的纪律延伸——
**宁可欠利用，不可冻机**）：

- **并行对象**：① `render_project` stem 循环（CPU 四引擎 synth/sf2/sfz/sample 池化，
  GPU 引擎按 BG-D10 不进工程轨、防御性顺序兜底——gpu_guard（BG-D8）已有 GPU 互斥，
  池化会抢显存）；② `mix_project` A 段轨链（独立 ffmpeg 子进程）。B 段 duck
  （trigger→target 依赖）/C 段（求和→母带依赖）/lowpass numpy 扫描（GIL 收益小）保持顺序。
- **并发公式**：`workers = max(1, min(ceil((avail−floor)/per_task), cpu_threads×0.5, 8, n_tasks))`，
  `floor = max(6GB, 总内存×0.2)`；per_task = 实测峰值 RSS×1.5 保守表
  （resources.py `PER_TASK_GB`）。64G/32G/16G 机器自适应（内存紧张时内存帽主导）。
- **实时门控 DispatchGate**：每次派发前现读 `/proc/meminfo` MemAvailable（绝不缓存），
  需 `≥ floor + per_task×(在途+1)`，不足 0.5s 轮询、10 分钟超时报错而非死等。
- **环境开关**（镜像 BGM_NO_INCREMENTAL 的 conftest 注入模式）：`BGM_NO_PARALLEL=1`
  硬关走旧顺序路径；`BGM_MAX_PARALLEL=N` 并发上限（只能压小）；`BGM_MEM_FLOOR_GB=X`
  地板覆盖。**conftest 对 BGM_NO_PARALLEL 刻意不注入**——默认并行走新路径，由
  test_parallel 锁定"并行≡顺序（BGM_NO_PARALLEL=1）位级一致"；顺序专项用例经
  monkeypatch/env_extra 覆写。
- **确定性硬门**：minimal 工程同目录先后并行/顺序渲染，**全部产物 sha 逐位相等**；
  并行≡v3.3 顺序锚点由既有 test_cli 的 sha 锚点隐式锁定（CLI 默认走并行路径）。
  增量渲染交互（hash 主线程派发前算、命中轨不占槽、边车"先 stem 后边车"顺序）
  由 test_dual_layout 增量组在新路径上复验。
- **并发受控行为锁**：BGM_MAX_PARALLEL=2 → 在途峰值 ≤2（计数器断言）；
  BGM_MEM_FLOOR_GB 极高 → workers 退化 1（纯函数 + run_pool 行为双断言）。
- **纪律**：一切开发期渲染 `python3 /tmp/render_guard.py` 包裹（GUARD_CAP_GB=6）；
  DispatchGate 单测一律 monkeypatch mem_available_gb 模拟低内存，绝不真吃内存。

## 一键体检（doctor）

```bash
python3 -m bgm_gen doctor            # JSON（cli.py 冻结路径，机器可读不回退）
python3 bgm_gen/doctor.py            # 人读绿红表（默认；可选档有标注）
python3 bgm_gen/doctor.py --json     # 原 JSON（与 doctor_report() 逐字段一致）
```

exit 0=必检项全过；1=有 ✗（与 JSON 的 ok 字段一致）。
