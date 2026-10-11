# MIGRATION.md · 自私有视频项目仓库 bgm_gen 迁移与重构记录（2026-08-22）

> 用户决策：bgm_gen 是独立工具，不应寄居视频项目。整体迁移至 `<仓库根>`
> 并完成结构重排。上游决策：视频项目 AGENTS.md **D18**。本文是迁移的单一记录源
> （路径换算表 + 变更清单 + 验证证据 + 对抗审查轮次）。

## 一、路径换算表（旧 → 新）

| 旧（<私有视频项目>/bgm_gen/…） | 新（music_tools/…） |
|---|---|
| `bgm_gen/*.py`（cli/doctor/synthlib/__init__/__main__） | `bgm_gen/` 同名（包名与 CLI 入口不变：`python3 -m bgm_gen` / `bgm`） |
| `gm_lofi.py` `demo_lofi.py` `midi2wav.py` `gen.py` `ab_steps.py` | `bgm_gen/legacy/`（导入改包内绝对导入 `from bgm_gen.…`；**argv/cwd 契约冻结不变**，BG-D4） |
| `bpm_check.py` `key_check.py` `tempo_check.py` | `bgm_gen/analysis/`（qc.py 子进程路径同步） |
| `wf_*.json`（14 个） | `workflows/`（+README 逐件说明） |
| `par_dl.sh` | `tools/` |
| `examples/` | 仓库根 `examples/`（gen_eden* 的 PKG_DIR 推导改 REPO） |
| `PLAN.md` `REVIEW_LOG.md` `REPORT.md` | `docs/`（文首加迁移注记，正文历史保留） |
| R1 内部中间 manifest | 内部证据归档（未随开源版发布） |
| `out/`（3.7GB 产物，gitignored） | 仓库根 `out/`（mv 原样搬运；内嵌绝对路径的 14 个 json 已重写前缀） |
| `runtime.json` / `assets.json` / `schema/` / `core/` / `engines/` / `tests/` | 原位随包迁移 |

**不变的东西**：包名 `bgm_gen`、CLI `bgm` 与七子命令、引擎契约（envelope+payload）、
工程 schema v1、测试口径与位级锚点、大资产根 `$MUSIC_ASSETS_ROOT/`、解释器分档。

## 二、结构性变更（超出搬运的部分）

1. **sample 引擎采样根解耦**：废除「与 assets_audio 同级」隐式假设（`SAMPLES_ROOT` 按包位置推导），
   改为 `runtime.json → samples_root` 显式键（doctor 校验；缺键回退旧推导）。
   当前值=视频项目资产库 `$MUSIC_SAMPLES_ROOT`（Kenney one-shot 跨项目共用指针，挪动需用户拍板）。
2. **缺省输出统一**：synth/sf2/sfz/sample 原「cwd 相对 `out/smoke/…`」、master/demucs/ai 原
   「包内 out/ 绝对」两种口径 → 统一 `engines/base.default_out()` = `<仓库根>/out/…`；
   `render` 缺省同样落 `<仓库根>/out/<工程名>/`。**修复了 REPORT 记录的「render 默认输出相对
   cwd 解析」坑**（显式 -o 的既有用法完全不受影响）。
3. **新增 `bgm catalog` 子命令**（catalog.py + catalog/timbres.{md,json}）：一条命令总览
   四类音色源（synth 6 音色 / sf2 双音源 GM128 / sfz 四库 685 件 / sample Kenney 10 包 753 ogg
   + drums_gdc 12）。既有七子命令逻辑与输出零改动。
4. **仓库宪法与文档体系**：仓库根 README.md（总览导航）+ AGENTS.md（BG-D1..D10 权威记录
   + 目录放置规则 + 坑表）；engines/README.md（插件开发契约）；workflows/README.md（逐件说明）。
   视频 AGENTS.md §六 瘦身为指针存根 + D18 决策行。
5. **git 建仓**：本地仓库（main），提交链：`c93c80c` pristine 迁移基线 → `a900476` 结构重排
   →（后续：catalog/文档/审查修复）。回滚与 diff 审查自此有据。

## 三、验证证据（2026-08-22，全部实跑）

| 项 | 结果 |
|---|---|
| 迁移前后锚点哈希 | `out/minimal/mix.flac` `7aee9dac…`、`eden_track/mix.flac` `c0b245f8…`、`stems/bass.duck.wav` `a7f3b7…`、`eden_v2/mix.flac` `9b23d794…` —— mv 逐字节保持（内部哈希材料未随开源版发布） |
| fast 测试档 | **68/68**（迁移时 62 → +5 catalog → +1 default_out 回归锁）；含 w2a 基线 7 引擎位级 sha 回归 |
| slow + service 档 | **5/5**（demucs 四分轨 / master loudnorm / eden 全链复现 / ai 引擎真实 ComfyUI 提交 / gen.py 冒烟，269s）——三档合计 73/73 全绿 |
| eden 全链复现（slow） | **通过**：14 轨工程重渲 `mix.flac` 与交付逐位一致（`c0b245f8…` 前缀保持）——out/ 内嵌路径重写 + mixer 数值路径的最强端到端证据 |
| doctor | ok=true（含新增 samples_root 项；comfyui 探活 ✓） |
| `bgm` 包装脚本 | 自 /tmp 任意 cwd 可用（PYTHONPATH 改指仓库根） |
| `bgm catalog` | 自 /tmp 生成 catalog/timbres.{md,json}，cwd 无关 |
| out/ 内嵌路径 | 15 个含绝对路径 json 全部落新址（14 个 `bgm_gen/out/` 前缀 + `smoke/ai/spec_smoke.json` 的 workflow 字段——R1 审查抓出的漏网，已补） |

## 四、对抗审查轮次（多轮红队 → 修复 → 复审）

### R1（2026-08-22，双红队并行：契约回归猎杀 + 结构可见性审查）

**R1-A（契约回归）**：冻结面全部守住（legacy 五脚本逐字节/等价 diff、CLI 七子命令零变化、
baselines 零字节未动、测试语义零漂移、minimal 自 /tmp 重渲 sha 逐位一致）；抓出：
- **MAJOR**：`engines/base.py` 的 `REPO_ROOT` 少一层 dirname（文件在 engines/ 下，两层只到
  bgm_gen/），全部缺省输出会落进包内 `bgm_gen/out/`——恰好落在「所有测试都显式 -o」的盲区。
  → 修复：三层 dirname + 新增 fast 回归锁 `test_default_out_lands_in_repo_root` +
  .gitignore 防御 `bgm_gen/out/`。
- MINOR：`out/smoke/ai/spec_smoke.json` 的 workflow 字段漏改（前缀规则只覆盖 `bgm_gen/out/`，
  未覆盖 `bgm_gen/wf_*`）→ 已重写；MIGRATION 表述同步修正。
- MINOR：旧位置残留孤儿 `out/audition/fate_motif/project.json`（迁移窗口期误落）→
  迁回新址（红线④不删除），旧目录彻底清空。
- NIT：.gitignore 增 `wf_ab_*.json`（ab_steps 根目录跑的 cwd 中间产物）。

**R1-B（结构可见性）**：可见性基建判定达标（README 5 分钟测试、catalog 3 个随机检索
30 秒可答、抽验 3 条音色路径全真、三处引擎信息一致、文档互链 100% 有效、
workflows 14/14 覆盖、engines 五步法与实际机制相符）；抓出：
- **MAJOR**：README 写「七个子命令」实际 8 个（catalog 后加入未回头同步）→ 已改 8 个。
- MINOR×8：Kenney 段缺 samples_root 引用前缀（找到≠能引用）→ catalog 每包补
  `_raw/kenney/kenney_<包>/` 前缀并重生成；sfz 文件名缩写无 glossary → 补
  SEC/SOLO/SUS/KS/DXF 常见缩写行；README 目录地图缺 catalog.py、sample 行缺
  mixkit 1169、out/ 散件无解释（补分组说明）；REPORT §①/§7.1 复现命令仍为旧路径
  → 就地更新；双 manifest（sfz/manifest_v2.json）分工未声明 → AGENTS §三 补声明；
  「fast ~19s」三处过时 → 统一 ~26s。
- 提出的模式性风险：「最后加入的功能没回头同步文档」「数字多处硬编码必漂移」——
  已在本轮全部消除，遗留观察项记入 R2 复审范围。

**修复后复验**：fast 68/68（含新回归锁）；`bgm catalog --write` 重生成（前缀/glossary 在位）。

### R2（2026-08-22，新锐红队复审：修复核验 + 新鲜眼全查）

**任务 A（R1 修复核验）8/8 PASS**：REPO_ROOT 实跑=仓库根且回归锁双推导链物理隔离
（tests/helpers.py 独立两层推导 vs base.py 三层，改错必红）；.gitignore/spec_smoke/
旧位置清空/catalog 前缀（抽 1 条三层拼接实测文件存在）/文档六项/全量 68 过——全部属实。

**任务 B（新鲜眼）**：doctor 缺 samples_root 键→报 ✗ 不崩溃（临时副本实测）；conftest
chdir 无嵌套污染；wrapper 中文+空格路径实跑正常；sfz 685 实数吻合；render 缺省链路
单一（无第二套推导）。新发现：**MAJOR 无**；MINOR-1 `wf_ab_*.json` 未锚定根目录
（会静默忽略未来 workflows/ 下同名入库文件）→ 已改 `/wf_ab_*.json` 并 check-ignore 验证；
NIT：sample.py 回退措辞同步、README out/ 散件补 ace15/v2smoke（均已顺手修）；
数字硬编码重复点清单（68/~26s/753/685/1169/18 条）已记录，其中 timbres.md 为
`bgm catalog --write` 活数据、其余为死副本——维持现状（数字均实测准确），后续大改动时
以 catalog 为准刷新。

**总裁决：放行**。审查链终态：R1 双红队（16 项修复）→ R2 复审（8/8 核验 + 1 MINOR +
3 NIT 顺手清零）→ 无 R3 必要。
