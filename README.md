# music_tools —— 终端音乐/BGM 生产工具

**一句话**：工程=JSON、CLI=`bgm`、引擎插件化、确定性优先的终端音乐/BGM 生产工具链——程序化合成、采样音源、SF2/SFZ 乐器、AI 整段生成、分轨、母带、QC，全部无头驱动，乐谱即数据（可 diff、可 git、可复现）。

> **姊妹项目 Video Tools**：本仓专注「音乐/BGM」产线。若你的需求是 **视频渲染 / 帧精确剪辑 / 字幕烧录 / gfx 动效 / 抠像背景替换 / 4K 投稿封装**（vtx CLI、timeline.json 产线），请移步姊妹仓 **`<私有视频工具仓>/`**——两仓通常搭配使用：本仓产出的 BGM 挂载进 video_tools 的 timeline.json 后，由其 `blender_bridge/audit_bundle.py` 生成分轨审计包（MP3 试听件 + 审计 timeline + audit.blend）供 Blender 逐轨屏蔽/独听裁决。

## 安装

```bash
cd music_tools  # 进入克隆目录
python3 -m pip install -r requirements.txt  # numpy；pytest 仅开发/测试
bash init.sh                               # 自检，不安装或启动模型/服务
python3 -m bgm_gen --help                   # 无需个人 bgm 包装脚本
```

手动最小依赖是 Python 3 + numpy + FFmpeg；SF2 需系统 libfluidsynth，SFZ 需 sfizz_render，sox 为辅助可选项。通过系统包管理器或 [FFmpeg](https://ffmpeg.org/download.html)、[FluidSynth](https://www.fluidsynth.org/)、[sfizz](https://github.com/sfztools/sfizz) 官方源自行获取，不随仓分发。demucs/matchering 在独立 Python 环境安装，ComfyUI 按 [官方说明](https://github.com/Comfy-Org/ComfyUI) 启动本地 8188 服务；OMR 可选 [Audiveris](https://github.com/Audiveris/audiveris)，AGPL 外部 CLI 不分发。许可边界见 [NOTICE](<NOTICE.md>)。

可选批转器/预览脚本的根优先级为 `MUSIC_ASSETS_ROOT` / `MUSIC_SAMPLES_ROOT` 环境变量 → 已有本地 runtime 配置 → 仓库 `assets/` / `assets/samples/`；编目中的 `$MUSIC_ASSETS_ROOT/...`、`$MUSIC_SAMPLES_ROOT/...` 是发布占位，不是可直接传入引擎的文件名。下载需代理时自行设置 `HTTPS_PROXY`，不预设个人代理端口。

核心引擎仍从本地 `bgm_gen/runtime.json` 读取实际路径；新 clone 不含该文件。当前 doctor 校验已有配置，不会自动创建缺失配置；首次需按下列结构在本地配置真实绝对路径（文件已 gitignore，勿提交），再运行 `python3 -m bgm_gen doctor`。doctor 检查完整环境，未启用的 GPU/服务项可能报未就绪，不代表 synth 不可用。以下是结构示意，所有占位必须替换：

```json
{
  "python_system": "<含 numpy 的 Python 绝对路径>",
  "assets_root": "<资产根绝对路径>",
  "samples_root": "<one-shot 根绝对路径>",
  "tools": {"ffmpeg": "ffmpeg", "fluidsynth_cli": "fluidsynth", "fluidsynth_lib": "libfluidsynth.so.3", "sfizz_render": "<sfizz_render 绝对路径>"},
  "sf2": {"FluidR3_GM": "<FluidR3_GM.sf2 绝对路径>", "GeneralUser_GS": "<GeneralUser_GS.sf2 绝对路径>"},
  "demucs": {"python": "<独立环境 Python>", "env": {"HF_HOME": "<资产根>/models/hf"}},
  "matchering": {"python": "<独立环境 Python>"},
  "comfyui": {"base_url": "http://127.0.0.1:8188"}
}
```

最小示例先跑 `python3 -m bgm_gen render examples/minimal.json -o out/minimal`；fast/slow/service 跑法与资产前置见 [CONTRIBUTING](<CONTRIBUTING.md>)。

## 快速上手

```bash
bgm doctor                                    # 环境体检（读取并校验本地 runtime.json）
bgm engines                                   # 引擎清单 + 确定性分级
bgm catalog                                   # 音色目录（详表见 catalog/timbres.md）
bgm render examples/minimal.json -o out/try1  # 最小工程端到端：stems→混音→母带→QC

# 测试（fast 档，默认 347 例——2026-10-11 开源整改后口径，预算 ≤90s；12 个显式 skip = 6 分家缺件 + 6 位级版本门（ffmpeg/fluidsynth 漂移，仅位级哈希断言段），见 bgm_gen/tests/README.md）
cd music_tools  # 进入克隆目录
python3 -m pytest bgm_gen/tests -q
```

`bgm` = `~/.local/bin/bgm`（= `python3 -m bgm_gen`，钉 miniconda python3 + PYTHONPATH=本仓库）。十个子命令：`doctor / engines / render-engine / render / stem / master / qc / catalog / show / edit`（用法速查见 [docs/USAGE.md](docs/USAGE.md) §一；示例工程 `examples/minimal.json`）。

## v3 操作面（2026-08-23 落档，docs/PLAN_v3.md）

- **五动词**：`bgm edit insert/set/move/delete`（+复合 split/merge/undo）+ `bgm show` 检视层——CLI 是快捷键不是围栏，底层全量经 core/edit.py 同校验路径可达（BG-D11）。
- **通用事件流**：track.events（cc/pitch_bend/keyswitch/program_change/note_on/off），同 tick 规范全序，notes[] 与事件载体 XOR；`track.params` 透传槽承接引擎参数级直通（BG-D14）。
- **引擎描述符注册表**：`bgm_gen/engines/descriptors/<engine>.json` 为能力面声明式事实源（参数/事件消费/invariants/coverage），`bgm show engines` 呈现（BG-D13）。
- **schema v2 双布局**：`spec_version "2"` 支持 track $ref 外部文件 + 增量渲染 `--incremental`（默认关闭）；v1 工程零迁移零位变（BG-D12）。
- **空间化**（v3.2/v3.3，BG-D16）：`track.space{depth,width,send_db}` 深度模型 + `master.space_ir` 合成厅堂（splitmix64 确定性 IR + wet 总线 OLA 卷积）；无 space 字段工程位级不变。命运成品即用（富特文格勒式座位表 + 1.9s 厅堂）。
- **资源感知并行渲染**（v3.4，BG-D17）：stem/轨链按 min(内存维, cpu×0.5, 硬帽 8) 并发 + DispatchGate 实时内存门控；`BGM_NO_PARALLEL` / `BGM_MAX_PARALLEL` / `BGM_MEM_FLOOR_GB` 三开关；确定性=并行≡顺序逐位相等。
- **验收成品**：贝多芬命运第一乐章端到端（smf_import→gen_fate→edit 表情层→render→QC ok）——工程与试听指引已随 BG-D20 分家迁 `music_project/`（examples/fate/ + out/fate_mvt1/LISTEN.md；v3.3 定稿 439.0s / LUFS -14.0 / Dynamic）。

## 引擎（插件）总表

| 引擎 | 功能 | 确定性 | 运行环境 |
|---|---|---|---|
| **synth** | synthlib 程序化音色（kick/snare/hat/fm_ep/bass/lead 六音色，纯 numpy DSP） | deterministic | 系统 python3 |
| **sf2** | 任意 .sf2 + bank/program → wav（libfluidsynth ctypes，零额外安装） | deterministic | 系统 python3（系统库 libfluidsynth） |
| **sfz** | SFZ 乐器 → wav（sfizz_render 子进程，免 sudo 落位版） | deterministic | 系统 python3 |
| **sample** | one-shot 采样触发（numpy 时间线混合；Kenney / Sonniss 等） | deterministic | 系统 python3 |
| **master** | 母带：loudnorm 两遍法（默认 -14 LUFS / -1 dBTP，B 站标准）/ matchering 参考匹配 | deterministic | loudnorm=ffmpeg 子进程；matchering=comfyui env |
| **demucs** | htdemucs 四分轨（vocals/drums/bass/other） | tolerant | comfyui env python（GPU 串行保护 BG-D8） |
| **ai** | ComfyUI HTTP 工作流提交（ACE-Step 1.5 / Music3 整段素材生成） | nondeterministic | ComfyUI 服务 127.0.0.1:8188 |
| （diffrhythm） | 整曲人声生成——可选档未装（BG-D10 用户明确后再装） | nondeterministic | venv-dr（未建） |

确定性含义：**deterministic**=同 spec 逐位复现；**tolerant**=GPU 归约非逐位（容差带断言）；**nondeterministic**=GPU 扩散（seed 固定亦不保证）。AI 素材走**冻结复现协议**：生成物落盘冻结后由工程引用，整轨渲染逐位可复现。

## 音色目录（有哪些声音、在哪）

- 命令行：`bgm catalog`；逐源详表：[catalog/timbres.md](catalog/timbres.md)。
- **试听预览**：`catalog/preview/*.mp3`（每库一件"典型音色串烧"，引擎真实渲染+时间码索引 [catalog/preview/INDEX.md](catalog/preview/INDEX.md)；再生成 `python3 tools/make_timbre_previews.py`）。
- 各源概览：

| 源 | 内容 | 许可证 |
|---|---|---|
| synth（synthlib） | 6 音色：kick / snare / hat（打击乐）+ fm_ep / bass / lead（调性） | 自产代码 |
| sf2 | 双音源各 GM 128 音色：FluidR3_GM（系统）+ GeneralUser GS（$MUSIC_ASSETS_ROOT） | MIT / GeneralUser |
| sfz | 四库共 685 件 .sfz：VSCO2 CE 管弦 75 · Karoryfer 三库 155（bigcat cello / Meatbass / War Tuba，war_tuba 只用顶层 Programs 入口）· Salamander Grand Piano · VPO 弦乐 454 | CC0 · CC0 · CC-BY 3.0 · VPO 自由使用许可（分层） |
| sample | Kenney 全 10 包（CC0，753 ogg，经视频项目 assets_audio 采样根）+ Sonniss GDC 精选鼓组 one-shot 12 件（$MUSIC_ASSETS_ROOT/samples/drums_gdc）+ Mixkit 36 类目 1169 mp3（仅供本地自取；不得作为工具素材再分发） | CC0 / royalty-free |

音色库真身在本仓 `assets/{sf2,sfz,samples}`（gitignored；2026-09-09 自 `$MUSIC_ASSETS_ROOT/` 迁入，旧位置符号链接兼容），manifest=`bgm_gen/assets.json`（19 条，含许可证/sha256/下载源）。署名义务（Salamander/VPO 用于发布物时）见 [docs/USAGE.md](docs/USAGE.md) §二。

## 目录地图

| 目录 | 一行说明 |
|---|---|
| `bgm_gen/` | Python 包：`cli.py`（CLI）/ `doctor.py`（体检）/ `synthlib.py`（纯 numpy 合成器库）/ `catalog.py`（音色编目）/ `core/`（编排：project·mixer·qc）/ `engines/`（7 引擎 + 插件契约，见其 README）/ `schema/`（project v1/v2 + engine_descriptor_v1 三件）/ `legacy/`（旧脚本薄包装，契约冻结）/ `analysis/`（BPM/调性检测）/ `tests/`（五层测试三档 marker）+ `assets.json`（manifest）+ `runtime.json`（机器本地探测，gitignore） |
| `workflows/` | 14 个 ComfyUI 工作流（ACE-Step 1.5 系 / Music3 / 步数 A/B 组），见 [workflows/README.md](workflows/README.md) |
| `examples/` | 仅 `minimal.json` 示例工程（测试锚点）+ `convert_openscore.py` 乐谱库批转器——**各项目作曲生成器 2026-09-09 分家迁 music_project**（BG-D20） |
| `docs/` | PLAN.md（规划与决策）/ PLAN_v3.md（v3 升级史）/ PLAYBOOK_BGM.md（创作手册）/ USAGE.md（CLI 速查+署名义务）/ OMR_PROOFREADING.md（校对协议）/ MIGRATION.md（迁移史）（内部归档未随开源版发布）——**项目报告与计划已迁 music_project/docs/** |
| `tools/` | `par_dl.sh` 大文件分块断点并行下载器 + `make_timbre_previews.py` 音色试听预览生成器（catalog/preview/ 再生成） |
| `catalog/` | 音色编目（`timbres.md` 详表 / `timbres.json` 机器可读 / `timbres_GAPS.md` 缺口档案）+ 试听预览（`preview/`，MP3+INDEX.md）+ 乐谱源登记（`scores/`） |
| `assets/` | **音色库真身**（gitignored，BG-D2 修正案 2026-09-09）：`sfz/`（VPO 454 件/SalamanderGrand/VSCO2/karoryfer，7.6G）+ `sf2/`（GeneralUser GS 等）+ `samples/`（drums_gdc/_audition 等）——`$MUSIC_ASSETS_ROOT/` 同名符号链接为兼容层，历史绝对路径照常解析 |
| `out/` | `minimal/` 测试锚点 + `smoke/` 引擎冒烟证据（工具 QC 基础设施）（gitignored；**全部成品产物 135G 已迁 `music_project/out/`**，各 LISTEN.md/PROOF.md 随迁） |
| 姊妹仓 | `<私有项目仓>/` = **项目案例仓**（项目生成器/项目测试/项目文档/全部产物；索引见其 README） |

## 架构（三句话）

1. **引擎契约 = envelope + payload**（`bgm_gen/engines/base.py`）：envelope 全引擎统一（engine/spec_version/sr/channels），payload 各引擎自有；出参必含 path/sr/channels/duration_s/rms_db，spec 声明 sr 则结果必须相等（BG-D5）。
2. **工程 = 单文件 project.json**（BG-D7）：记谱统一 `notes=[MIDI pitch, beat 浮点, dur beat, vel]`；每轨单 clip 绝对窗口、sections 纯标注、重复段=整轨复制——作曲即写数据，AI 与人等权读写。
3. **确定性分级 + 位级回归锚点**：三档 determinism 声明；确定性引擎由 `tests/baselines_*.json` RMS 基线与 `out/minimal` sha 锚点锁死，改坏即测试红（项目级位级复现锚点随 BG-D20 分家迁 music_project/tests）。

## 深入指针

| 文档 | 内容 |
|---|---|
| [docs/PLAN.md](docs/PLAN.md) | 整合规划 v1.4：BG-D1..BG-D10 决策全文、五轮瀑布、QC 阈值 |
| [docs/PLAN_v3.md](docs/PLAN_v3.md) | v3 升级计划 v1.1（定稿+增量轮）：描述符/事件流/五动词/双布局 + v3.1-v3.4 增量轮，BG-D11..D17 |
| [docs/USAGE.md](docs/USAGE.md) | CLI 用法速查（十子命令+v3 操作面+并行开关）+ 署名义务模板 |
| [docs/MIGRATION.md](docs/MIGRATION.md) | 迁移史（自私有视频项目仓库 bgm_gen 的路径换算与结构重排） |
| [AGENTS.md](AGENTS.md) | 工具宪法：决策搬运、放置规则、迁移状态、坑表、遗留债务 |
| [bgm_gen/engines/README.md](bgm_gen/engines/README.md) | 引擎插件开发契约（如何新增引擎）+ 描述符注册表 |
| [workflows/README.md](workflows/README.md) | ComfyUI 工作流逐件说明与提交方式 |

成品试听与项目档案：**全部成品产物（含 LISTEN.md 试听指引）在 `<私有项目仓>/out/`**——如命运第一乐章 `music_project/out/fate_mvt1/mix.flac`（v3.3 定稿 439s/-14.0 LUFS/Dynamic）；项目报告/审查史/计划见该仓 `docs/`（REPORT.md/REVIEW_LOG.md/PLAN_*.md）。

## 仓库初始化与布局（2026-09-09 收编整理）

- **`init.sh`**：新环境（新机 / 新 clone）初始化——依赖自检（python3+numpy、ffmpeg、sox、libfluidsynth）+ 大模型能力开启指引。**ComfyUI AI 引擎 / demucs 等 GPU 大模型能力默认关闭**，init.sh 不会自动启动或配置它们；需要时按其输出提示手动开启（准备本地 runtime.json → 启动 ComfyUI → `bgm doctor` 校验）。`runtime.json` 的唯一写入者仍是 `bgm doctor`（BG-D3），init.sh 不代写。
- 确定性引擎（synth/sf2/sfz/sample/master-loudnorm）不依赖大模型，但仍须各自的外部工具、音色及本地配置就绪。

## 许可证与音色获取

本仓原创代码和文档采用 [MIT](<LICENSE>)，Copyright (c) 2026 music_tools contributors。第三方预览与内容适用 [NOTICE](<NOTICE.md>)，不能仅据本仓 MIT 推断所有内容都可自由再分发。

音色库、采样、乐谱与权重**不随仓分发**，`assets/`、`out/` 均 gitignored。请从官方源自行获取并核验当前条款：

| 库 | 官方源 | 许可 |
|---|---|---|
| Salamander Grand Piano V3 | [原库](https://archive.org/details/SalamanderGrandPianoV3)、[SFZ](https://github.com/sfzinstruments/SalamanderGrandPiano) | CC-BY 3.0，成品署名 |
| Virtual Playing Orchestra | [官网](https://virtualplaying.com/virtual-playing-orchestra/) | 音乐自由使用；采样分层许可，保留来源署名 |
| GeneralUser GS | [作者官网](https://schristiancollins.com/generaluser.php) | GeneralUser GS License v2.0 |
| FluidR3 | [FluidSynth 音源指引](https://www.fluidsynth.org/soundfonts/) | MIT |
| VSCO2 CE | [官方仓库 SFZ 分支](https://github.com/sgossner/VSCO-2-CE/tree/SFZ) | CC0 |
| Karoryfer | [官方免费库](https://www.karoryfer.com/karoryfer-samples) | 所登记三库 CC0 |
| Kenney | [官方源](https://kenney.nl/assets) | CC0 |
| Sonic Pi 鼓采样 | [官方采样目录](https://github.com/sonic-pi-net/sonic-pi/tree/dev/etc/samples) | 所登记鼓件 CC0，须随目录逐件核验 |
| GMD / E-GMD | [GMD](https://magenta.withgoogle.com/datasets/groove)、[E-GMD](https://magenta.withgoogle.com/datasets/e-gmd) | CC-BY 4.0，成品署名 Google LLC |
| Mixkit / Sonniss（仅本地可选） | [Mixkit](https://mixkit.co/free-sound-effects/)、[Sonniss](https://sonniss.com/gameaudiogdc) | 自行核验条款；不开源分发裸采样预览 |

乐谱官方源为 [Mutopia](https://www.mutopiaproject.org/)、[OpenScore](https://github.com/OpenScore)、[IMSLP](https://imslp.org/)；按逐件许可与辖区判断，PD/CC0/CC-BY 准入，CC-BY-SA 标记项保持挂起。MiniMax Music3 工作流仅配置，**权重需用户自行获取并遵守其条款，许可未登记、商用资格未核实前不得投产**。其它模型也须核验所取得版本的许可。

## 相关项目

音乐项目案例仓（music_project）与视频工具仓（video_tools）为**姊妹项目仓（私有）**，不属于本次开源交付；历史项目生成器、成品、个人 AI 助理配置及内部取证材料未随开源版发布，不承诺公网可访问。
