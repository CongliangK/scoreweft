# AGENTS.md · Scoreweft 工具宪法

> 本文件是 Scoreweft 仓库（终端音乐/BGM 生产工具；本地开发目录名 music_tools，见 BG-D21）的**代理单一事实源**：内部决策、目录放置规则、迁移状态、坑表与遗留债务。新代理先读本文，再按指针深入。
> 决策编号 **BG-D1..BG-D21**（D1-D10 搬运自 docs/PLAN.md §2；D11-D14 搬运自 docs/PLAN_v3.md §5；D15 为 v3 R4 仲裁新增；D16/D17 为 v3.2/v3.4 增量轮新增；D18 为 2026-08-25 产线转向新增；D19 为 2026-09-09 音色先行门新增；D20 为 2026-09-09 仓库分家新增；D21 为 2026-10-11 项目定名新增）与上游视频项目的 D1-D17 相互独立（视频项目宪法：`<私有视频项目>/AGENTS.md` §六）。
> 最后更新：2026-10-11（BG-D21 项目定名 Scoreweft：对外名称/开源仓库名更名，CLI `bgm` 与包名 `bgm_gen` 不变；此前 2026-09-09 BG-D2 修正案/BG-D20/BG-D19）

---

## 一、内部决策（BG-D1..BG-D21，权威记录；D1-D10 搬运自 docs/PLAN.md §2，D11-D15 为 v3 落档，D16-D17 为 v3 增量轮落档，D18 为产线转向落档，D19 为音色先行门落档，D20 为仓库分家落档，D21 为项目定名落档）

- **BG-D1 CLI 名 `bgm`**：包目录 `bgm_gen/`（`__init__/__main__/cli.py`），入口 `python3 -m bgm_gen` + `~/.local/bin/bgm` 包装（钉 miniconda python3 + PYTHONPATH=本仓库根）。
- **BG-D2 大资产放 `$MUSIC_ASSETS_ROOT/`**：manifest（`bgm_gen/assets.json`）存约定根相对路径 + 许可证 + sha256 + 下载源 URL；数据主权原则——工程=磁盘开放 JSON，人与 AI 等权读写、可 diff、可 git；引擎全部 CLI 无头驱动，云端/黑盒仅限 ComfyUI 本地服务。**修正案（2026-09-09，用户裁定"方便找到所有的东西"）：音色库三目录（sf2 31M/sfz 7.6G/samples 753M）真身迁入本仓 `assets/`（gitignored），`$MUSIC_ASSETS_ROOT/` 同名符号链接作兼容层——历史绝对路径（music_project 生成器/冻结 project.json 哈希锚点）零破坏照常解析；manifest 根相对路径与 assets_root（$MUSIC_ASSETS_ROOT，含 models/scores/tools 实体）不变**。
- **BG-D3 解释器分档**：基础=系统 python3（miniconda base）；demucs/matchering=comfyui env python；DiffRhythm=venv-dr python（未建）。`runtime.json` 唯一写入者=doctor（探测逻辑），引擎只读；doctor 兼任 manifest↔runtime.json 一致性校验者。
- **BG-D4 旧脚本改造边界**：允许重构为函数+`if __name__` 守卫（判定=CLI 契约与输出不变）；SMF 写入器上移 `engines/midi_util.py`；gen.py 契约冻结，包内 ai 引擎为新模块复用其提交/轮询逻辑。
- **BG-D5 stems 契约**：meta.sr/channels 全局权威（默认 44100/2）；stem 渲染后强制归一（重采样到 meta.sr、mono 由 mixer 定声像、短 stem 补零至 section 窗、超长截断）；验收"正确 sr"=等于 spec 声明 sr。
- **BG-D6 引擎接口=envelope+payload**：envelope（engine/spec_version/sr/channels/时长出参）统一；payload 各引擎子 schema 各自版本化。
- **BG-D7 工程格式**：单文件 project.json（schema v1 见 `bgm_gen/schema/project_v1.json`）；记谱统一 `notes=[pitch(MIDI 0-127), beat(浮点), dur(浮点 beat), vel(0-127)]`；v1 语义=每轨**单 clip 绝对窗口**（`clip:{start_beat,end_beat}`，notes 为轨道局部 beat 经 clip 平移到全局），sections 纯标注不参与渲染，重复段用整轨复制表达；automation/sidechain/bus/master 按 schema。
- **BG-D8 GPU 串行保护**：ai/stem（及可选 diffrhythm）执行前 nvidia-smi 探测空闲显存，不足排队/提示；本包内 GPU 任务互斥（`engines/gpu_guard.py` 文件锁 + 显存闸，超时策略 cpu 降级/raise/proceed）。
- **BG-D9 out/ 命名规范**：冒烟 `out/smoke/<engine>/`；工程 `out/<project>/stems/<track>.<engine>.wav` 与 `out/<project>/{mix.flac,project.json,qc.json}`；ai 取回后按规范改名。**迁移补注（2026-08-22）：out/ 在仓库根，缺省输出与 cwd 解耦**（`engines/base.default_out` 统一解析到 `<仓库根>/out/`，render 不加 `-o` 也落在 `<仓库根>/out/<工程名>/`）。**v3 补注（2026-08-23）：命名族新增 stem 增量渲染边车 `<track>.<engine>.render.json`（gitignored）与工程旁 undo 快照栈 `.bgm_undo/`（见 §二注记）**。
- **BG-D10 扩散模型定位（用户裁定 2026-08-21）**：扩散=**整段素材生成器**（几十秒级波形、整体质感与人声层，产物按"录音素材"对待），**不是音色引擎**——音色合成是算法/采样的领地。扩散产物必须经降维闸口（audio→MIDI 转写或 demucs 分轨）转成符号/stem 后才进入逻辑编排。**模型准入三门槛**：①当年代际且本地 QC 实测有效；②许可证可商用；③本地无头可驱动。旧代际默认不进产线（MusicGen 2023 排除；DiffRhythm 2025-03 降可选，用户明确后才装）。

以下 BG-D11..D14 为 **v3 落档**（照录 docs/PLAN_v3.md §5 三轮规划审查定稿草案；执行期审查与实测记录见该文 §10.4-§10.8）：

- **BG-D11 操作层**：**五动词=show/insert/set/move/delete**（操作面元语；编辑动词=insert/set/move/delete，复合命令=split/merge/undo）；target 寻址=规范排序索引+窗口谓词；**索引跨编辑会漂移，连续编辑必须每次 edit 后重新 show 取索引**；每动词一 undo 快照点（布局保全，上限 50，undo 前漂移检测，--force 覆盖）；CLI 与 core/edit.py 同校验路径；宿主不封装任何音乐观点。
- **BG-D12 双布局**：spec_version "2" 支持 track 槽位 $ref（相对工程目录、单缝不嵌套、无兄弟字段；装载层版本前置门：v1 拒 events/$ref/params）；v1 零迁移零位变；save_project 原子写（tmp 同目录、键白名单）为唯一正本写回器；render 快照：v1 保持 copyfile、$ref 工程内联展开；增量渲染默认关闭、`--incremental` 显式开启、`BGM_NO_INCREMENTAL=1` 硬闸（读取于 render_project 内）、hash 键=组装后 payload 规范化 JSON+engine/binary_pin/descriptor 三版本+sr/channels。
- **BG-D13 描述符**：引擎能力以声明式描述符（git 版本化 JSON，文档性 schema+手写校验，零新增依赖）为源，三档来源 A 收割（第一事实源=引擎源码 payload 读取行为）/B 起草+探针/C 手写降级（gaps 强制标注，当前无实例）；单字段约束描述符生成、跨字段约束走 invariants 清单；探针=行为探针（exit 0+出参契约+非零产物+determinism 分级）；防漂移=pin（sha=advisory 黄灯）+探针+doctor+升级 diff 四件套。
- **BG-D14 事件流**：track.events 通用事件（cc/pitch_bend/keyswitch/program_change/note_on/off），note 载体与 notes[] XOR（同 pitch 交叠与悬空拒绝）；弯音=semitones+轨级 bend_range（sfz 必显式）；同 tick 全序单一 event_sort_key()：keyswitch→PC（bank 前置复合）→cc→bend→note_off→note_on，三级决胜 (t,类型序,pitch,插入序)；未知类型闭集拒绝；车道=投影视图；引擎消费由描述符声明（sf2 拒 program_change/keyswitch）；控制事件经 payload.events 进引擎，无 events 的 payload 保持旧路径字节不变；**track.params 透传槽承接参数级直通（校验由描述符驱动，组装为覆盖合并）**；payload.events 引入伴随 sfz/sf2 描述符 version bump，envelope spec_version 不变。
- **BG-D15 母前峰值限幅 `master.pre_limit`**（v3 R4 仲裁新增，2026-08-23）：v2 schema 声明字段（`{ceiling_db, attack_ms=5, release_ms=150}`），实现=mixer 确定性 numpy lookahead 峰值限幅器（滑窗最大包络、dB 域一阶指数释放、信号延迟 look-1 使峰值样本入自身治理窗、纯 numpy 逐位确定），**作用点=premix 求和之后**——crest 是全编制叠加的结构属性，压表情/调轨增益几乎不动。动因=管弦高动态素材 premaster 超 loudnorm linear 约束；**实测 ffmpeg linear 判定 binding 约束是 measured_LRA ≤ 目标 LRA(11) 而非 crest**：不限幅 LRA 12.4 / 削顶 +6dB 11.6 / +4dB 11.1 均 Dynamic，+3dB（LRA 12.4→10.5）转 Linear。**ceiling_db 定义在 premix float 域，可为正值**（削顶语义）；falsy 语义=null/缺省=显式关，`{}` 拒绝。

以下 BG-D16/D17 为 **v3.1-v3.4 增量轮落档**（2026-08-24；执行记录 docs/PLAN_v3.md §10.10-§10.13）：

- **BG-D16 空间化**（v3.2 机制 + v3.3 应用，`core/space.py`）：v2 schema 专属字段 `track.space{depth 0-1 必填, width 缺省 0.3, send_db 可选}`（封闭键集校验，v1 版本前置门拒绝）与 `master.space_ir{rt60_s 0.4-4.0, seed 整数}`（声明时启 wet 总线）；**send_db 缺省=-12+depth×9 dB（越远越湿）**。机制三件：合成厅堂 IR（**splitmix64 整数哈希自产噪声——不走 numpy.random（Generator 流跨版本不承诺，NEP 19 只冻 legacy RandomState），逐位确定且跨平台/跨 numpy 版本稳定**；早期反射簇 5-30ms 左右构造性不对称 + 晚期去相关指数混响；Σh²=1 能量归一；Schroeder 倒积分 RT60 自测 ±15%）+ **深度模型**（预延迟 depth×24ms≈8.2m 声程差 / 电平 -depth×4.5dB / 一阶 HF 滚降 8000→3500Hz 随 depth / M-S 宽度 side 增益=width/0.3）+ wet 总线 OLA 卷积（全轨送量求和→共享 IR→与 dry 求和，premix 含 IR 尾长）。**纯增量承诺：无 space 字段工程位级不变**（mixer A' 空间化级完全旁路；minimal+fate 双证锁定）；各算子中性点（depth=0 / width=0.3）逐位旁路。
- **BG-D17 资源感知并行渲染**（v3.4，`core/resources.py`；动因=PLAN_v3 §10.7 冻机事故——**宁可欠利用，不可冻机**）：并发规划纯函数 `workers = min(⌈(avail−floor)/per_task⌉, ⌊cpu×0.5⌋, 硬帽 8, n_tasks)`（保底 1），**内存地板 floor=max(6GB, 总内存×20%)**；`DispatchGate` 派发实时门控（每次派发前查 `mem_available_gb() ≥ floor + per_task×(在途+1)`——/proc/meminfo **现读绝不缓存**；不足 0.5s 轮询、超时 10 分钟抛 ResourceError 而非死等；acquire 检查与递增同锁段防 TOCTOU）；三开关 **`BGM_NO_PARALLEL=1`**（硬关走旧顺序路径，读取点在 run_pool）/ **`BGM_MAX_PARALLEL=N`**（与硬帽取 min 只能更小）/ **`BGM_MEM_FLOOR_GB=X`**（地板覆盖）；**GPU 引擎（demucs/ai）排除池外**（BG-D8 gpu_guard 已有本包互斥；池成员=synth/sf2/sfz/sample+track_chain）；per_task 表=render_guard 实测峰值 RSS×1.5；**确定性=并行≡顺序逐位相等**（BGM_NO_PARALLEL=1 对拍锁定；结果按任务序收集与完成顺序无关）。

以下 BG-D18 为 **产线转向落档**（2026-08-25 用户裁定；《归潮》两版被否，裁定音乐性瓶颈在作曲判断而非工程层）：

- **BG-D18 BGM 产线默认路线=公有领域经典作品改编实现**：底稿=公有领域机器可读乐谱（**音符层即可**——表情层由自研引擎重写：配器改写/力度弧线/warp/terrace/空间化/母带，全栈复用 fate 先例）；原创算法作曲线（归潮）降为实验线（存档不删，红线④）。**数据主权**：源登记=`catalog/scores/REGISTRY.md`（§9 R-IMSLP/R-Musopen/R-CPDL/R-MuseScore/R-Wikimedia/R-IA 六条验收规则为产线铁律），逐件四要素清单=`catalog/scores/MANIFEST.json`，数据落 `$MUSIC_ASSETS_ROOT/scores/`。**许可铁律**：kernScores（维护者第一方 LICENSE=CC BY-NC-SA 4.0 铁证）与 Project Gutenberg 音乐部（#156 "Copyrighted."）永久禁入；CC-BY-SA 件（Mutopia 804 条目）未裁定前**只检索不投产**；IMSLP 只收标签白名单件（`Public Domain` 三旗全 V 或 `(dedicated)`；NC 存量与 Performance-Restricted 禁入）。**管弦间接路线**：PD 钢琴缩谱扫描（IMSLP / IA `imslp` 官方镜像）→ OMR（Audiveris 5.11.0 免 sudo 装于 `$MUSIC_ASSETS_ROOT/tools/audiveris/`，本地无头执行不触发 AGPL 分发义务）→ 符号层人机校对 → 自研引擎重配器。

以下 BG-D19 为 **音色先行门落档**（2026-09-09 用户裁定；用户对历轮成品音色不满意的根因诊断=流程缺步）：

- **BG-D19 音色先行门（timbre-first gate）**：产线创作流程强制前置门——**任何编曲/编排开始前，必须先完成音乐要素契约（乐器清单 × 逐件音色实现）并经用户拍板**。契约四件套：①乐器清单（含角色/音域分工）；②逐件实现（引擎+音色源+关键参数，候选可 2-3 件并列）；③试听件两段（单音探针=timbres_GAPS 口径 C4/vel100/3s/bpm60，库内既有探针数据可引用 + 真实用法乐句 8-16 小节；多候选同乐句乱序盲标）+ 客观量具读数（RMS/峰值/谱质心/攻击占比）；④用户逐件拍板记录（日期+结论）。**契约落工程 `TIMBRE.md`（与 LISTEN.md 并列的工程必备产物）**；全清单拍板通过前**禁入编曲**，编曲中途换音色=回门重拍该件并评估编曲联动。**复用条款**：已拍板实现跨工程复用=引用原拍板指针（工程名+日期）免重听；换库/换参/引擎升级=重开门。MF 盲听仅参考、须先过客观量具门（§四 MF 双坑）。动因：音色是不可用混音补救的要素，编排期顺手决定、验收期才暴露=返工最大化（反例=闲时任务五 sting/床鼓）；先例=吉他轮 synth nylon 四轮盲听+量具门胜出后才投产（out/guitar_test30，孤例升格默认流程）。**操作细则=docs/PLAYBOOK_BGM.md §〇**。

以下 BG-D20 为 **仓库分家落档**（2026-09-09 用户裁定："尽可能保证工具本体的干净"）：

- **BG-D20 工具/项目分仓（tool-project split）**：music_tools 只留**工具本体**——核心代码 `bgm_gen/`、理念与手册（AGENTS/README/docs 的 PLAN/PLAN_v3/PLAYBOOK/OMR_PROOFREADING/MIGRATION/USAGE）、`catalog/` 库编目（音色+乐谱源登记=共享基础设施）、通用工作流 14 件、`examples/` 仅存 `minimal.json`（测试锚点示例）与 `convert_openscore.py`（库批转器）；**一切具体项目案例迁姊妹仓 `<私有项目仓>/`**——项目生成器+溯源材料（examples 13 gen_*.py + fate/spring/tide_sym）、项目确定性回归测试（11 个 test 文件+适配版 helpers/conftest，跑法=cd music_project && pytest tests，bgm_gen 经 MUSIC_TOOLS_ROOT 导入）、项目文档（REPORT/REVIEW_LOG/PLAN_full_bgm/PLAN_spring_omr/PLAN_musicxml/idle_tasks 五任务书）、voice-ime 工作流四件、**全部产物 out/（135G 同盘 mv）**。配套：REPORT 工具级两节（§⑤ CLI 速查+§7.6/§8.5 署名义务）抽取为本仓 `docs/USAGE.md`；`out/minimal/` 锚点分家后即时重渲重建；工具仓测试缺口=缺件即 skip（test_smf_import/test_legacy 同口径）；内部 W1B 调用手册（未随开源版发布） 随 out/ 迁走（git 跟踪例外随之消灭）。**红线④"旧产物不删除"在分家中以"迁移不删除"履行**（全部 mv 原样落 music_project）。

以下 BG-D21 为 **项目定名落档**（2026-10-11 用户裁定；开源前最后准备）：

- **BG-D21 项目定名 Scoreweft**：对外项目名/GitHub 开源仓库名 = **Scoreweft**（score 乐谱 + weft 纬线——把音符与音色织成音乐；读作 score-weft）。候选 Notelith/Timbreloom 因既有使用痕迹（LoL 玩家名/Pinterest 用户、Suno 艺人名 timbreloom.com）否决；命名核验 2026-10-11：GitHub 仓库/用户搜索 0、PyPI/npm/crates.io 同名包均 404、scoreweft.com RDAP 404、Google 精确检索无同名音乐工具/品牌——口径为"未发现冲突"，**非正式商标清查**（中美欧 WIPO 商标库检索未做，如需法律级确权另行补查）。**CLI `bgm` 与包名 `bgm_gen` 维持不变**（BG-D1 契约、红线⑤、music_project 经 MUSIC_TOOLS_ROOT 导入零破坏）；本地开发目录名 music_tools 不改（姊妹仓绝对路径依赖），发布文档统一以 scoreweft 作克隆目录示例。同步更名面：README/LICENSE/NOTICE/init.sh 横幅/预览义务行（INDEX.md+make_timbre_previews.py 同步改，保再生一致）/"Scoreweft contributors" 版权署名；历史条目（BG-D20 及更早）中的 music_tools 表述按"迁移不删除"原则原样保留。

**红线（docs/PLAN.md §0，不可违背）**：①BGM 产线仅用可商用许可（CC0/MIT/Apache/BSD/GeneralUser 类；CC-BY/Sonniss 系 2026-08-22 v2 提质轮经用户批准入白名单，禁 NC）；**SalamanderGrand 负 CC-BY 署名义务**（SalamanderGrand V3：archive.org/details/SalamanderGrandPianoV3）；**VPO 为自由使用许可**（用库制音乐完全自由含商用；再分发采样需按其分层许可署名 Paul Battersby，virtualplaying.com），成品署名仅作双保险——义务明细见 docs/USAGE.md §二（2026-09-09 分家自 REPORT §7.6/§8.5 抽取）；**v3 补记（2026-08-23）：命运底稿 Mutopia `Symphony5_1.mid`（Public Domain）入仓四要素封存**（URL + ID Mutopia-2017/11/05-941 + sha256 `0ce1bca9…df52046` + 取回 2026-08-23，2026-09-09 分家后见 `music_project/examples/fate/SOURCE.md`）；**三四乐章不存在许可干净机器源**（kernScores/CCARH=CC BY-NC-SA、IMSLP 合成板块=CC BY-NC 3.0、Project Gutenberg #156=Copyrighted、Musopen 无 MIDI——均排除）——全曲四乐章如需，须另行裁定人工录入路线（**2026-08-25 补注：缩谱+OMR 间接路线材料已备齐，见 REGISTRY §10**）；**乐谱源验收=REGISTRY §9 R-\* 白名单规则（BG-D18，2026-08-25）**；②不破坏 ComfyUI 环境（comfyui env 一律 --no-deps/独立 venv）；③sudo 最小化集中且存在完整免 sudo 替代路线；④旧产物不删除；⑤旧脚本 argv/cwd 行为冻结（ab_steps.py 依赖 gen.py 契约）。

## 二、目录结构与放置规则

| 位置 | 放什么 |
|---|---|
| **包内 `bgm_gen/`** | 一切需要被 import 的代码：`cli.py`（CLI）、`doctor.py`（体检）、`synthlib.py`（纯 numpy 合成器库）、`engines/`（引擎插件，见其 README 契约；`engines/descriptors/` = 描述符注册表 JSON + harvest 收割器 + 证据日志，引擎能力面声明式事实源，BG-D13）、`core/`（编排：project/mixer/qc + v3 三件 smf_import（SMF 读器）/edit（五动词+undo）/show（检视层视图族））、`schema/`（project_v1/v2 + engine_descriptor_v1）、`analysis/`（BPM/调性检测器）、`tests/`（五层测试三档 marker）、`legacy/`（旧脚本薄包装）、`assets.json`（资产 manifest）；`runtime.json` 为机器本地探测产物（gitignore，doctor 唯一写入者） |
| **仓库根** | 非代码资产：`workflows/`（ComfyUI 工作流 + README，通用 14 件）、`examples/`（**仅 `minimal.json` 示例工程 + `convert_openscore.py` 批转器**——各项目作曲生成器 2026-09-09 分家迁 music_project）、`catalog/`（编目文档：音色编目 + **`catalog/scores/` 乐谱源登记表** REGISTRY.md / 逐件清单 MANIFEST.json，BG-D18；**`catalog/preview/` 音色库试听 MP3 八件**=每库典型音色串烧，`tools/make_timbre_previews.py` 引擎真实渲染可确定性再生）、`docs/`（工具规划/创作手册/CLI 速查/迁移史——**项目报告与计划已分家迁 music_project/docs/**）、`tools/`（par_dl.sh 下载工具 + make_timbre_previews.py 预览生成器）、`out/`（gitignored，分家后仅存 `out/minimal/` 测试锚点与 `out/smoke/` 引擎证据）、`assets/`（**音色库真身 sf2/sfz/samples，gitignored，BG-D2 修正案**） |
| **姊妹仓 `<私有项目仓>/`** | **项目案例仓（2026-09-09 分家，BG-D20）**：具体项目的生成器（examples/：gen_fate/gen_tide/…13 件+fate/spring/tide_sym 溯源材料）、项目确定性回归测试（tests/：11 个 test 文件+适配版 helpers/conftest，依赖本仓 bgm_gen 包）、项目文档（docs/：REPORT/REVIEW_LOG/PLAN_full_bgm/PLAN_spring_omr/PLAN_musicxml/idle_tasks）、voice-ime 床乐工作流四件、**全部渲染产物 out/（135G，含各成品 LISTEN.md/PROOF.md）**。新项目落该仓 |
| **仓库外** | 大资产永不进仓库：`$MUSIC_ASSETS_ROOT/{sf2,sfz,samples,models,tools,scores}`（BG-D2；**scores=公有领域乐谱库**：mutopia 仓库+MIDI / openscore 两库 / scans 缩谱扫描 / tools 采集脚本，BG-D18）；one-shot 采样根=视频项目 assets_audio（见下节，跨项目指针） |

**v3 运行期目录注记（gitignored，不属"放置"对象）**：工程旁 `.bgm_undo/`（undo 快照栈，上限 50）；`.bgm_val_*/`（$ref 再校验瞬态镜像）；stem 边车 `<track>.<engine>.render.json`（增量渲染）。

**放置判断**：新代码要被包 import → 进 `bgm_gen/` 对应子目录；工作流/示例/文档/编目 → 仓库根对应目录；音视频大文件 → 仓库外资产根 + manifest 登记。

**legacy/ 契约冻结提醒**：`bgm_gen/legacy/` 的 gm_lofi/midi2wav/demo_lofi/gen/ab_steps 均为薄包装，**argv/cwd 契约不许改**（BG-D4/红线⑤）；裸跑依赖 cwd 相对路径，需包内导入的脚本要 PYTHONPATH 指向仓库根。

## 三、迁移状态（2026-08-22）

- 本仓库自 `<私有视频项目>/bgm_gen` 迁移而来（独立 git 仓库），结构重排：`out/` 提升至仓库根（缺省输出与 cwd 解耦，见 BG-D9 补注）；workflows/examples/docs/tools 自包内上移；旧脚本入 `bgm_gen/legacy/`、分析脚本入 `bgm_gen/analysis/`。迁移史与路径换算表：[docs/MIGRATION.md](docs/MIGRATION.md)。
- **samples_root 显式化**：`runtime.json` 的 `samples_root` 指向视频项目资产库 `$MUSIC_SAMPLES_ROOT`（Kenney one-shot 等；跨项目指针，doctor 校验；**改挪需用户拍板**——2026-08-26 上游 D27 重构已拍板并同步，`catalog/timbres.json` 与 examples 内绝对路径同批更新；缺键时回退旧的"包父目录/assets_audio"推导——迁移后已不适用）。
- **大资产不动**：仍在 `$MUSIC_ASSETS_ROOT/`（sf2 双音源 / sfz 四库 / drums_gdc 采样 / htdemucs 权重 / sfizz 工具），manifest 见 `bgm_gen/assets.json`（18 条）。另存在 `$MUSIC_ASSETS_ROOT/sfz/manifest_v2.json`（sfz 下载期详细版：逐条 sha256/署名/冒烟证据；其内 smoke 命令为迁移前旧路径，历史记录）——**日常权威=assets.json，manifest_v2 仅作证据存档**。
- **旧位置已清空**：`<私有视频项目>/bgm_gen` 整体迁出（含 out/ 产物——迁至仓库根 `out/`，全程 mv 未删除/重写任何音频文件；迁移前全量清单与产物锚点哈希见 内部迁移清单与哈希材料（未随开源版发布））。
- **外部引用已切换（2026-08-22 完成）**：视频项目 `<私有视频项目>/AGENTS.md`（D18 决策 + §六 存根 + §三/§四 指针）、video-edit skill、音频资产与混音惯例调查.md、assets_audio/LICENSE.md 均已指向本仓库。
- **v3 升级（2026-08-23）**：R1-R4 五轮执行完毕并放行——引擎描述符注册表（BG-D13）→ 通用事件流 + params 透传（BG-D14）→ 五动词 + show 检视层 + undo（BG-D11）→ schema v2 双布局 + 增量渲染（BG-D12）→ **命运第一乐章端到端验收**（out/fate_mvt1，qc ok=true / Linear / LUFS -14.0，试听指引 out/fate_mvt1/LISTEN.md）。计划、三轮规划审查、执行期记录与 R4 仲裁全文：[docs/PLAN_v3.md](docs/PLAN_v3.md)（§10.4-§10.8）。
- **v3.1-v3.4 增量轮（2026-08-24）**：表情迭代（144+warp/力度重写/humanize/Dynamic 正门）→ 空间化机制（BG-D16）→ 空间应用（富特文格勒式座位表+1.9s 厅堂，空间三指标达标）→ 资源感知并行渲染（BG-D17）；执行记录 [docs/PLAN_v3.md](docs/PLAN_v3.md) §10.10-§10.13。命运成品**现行定稿=v3.3**（Dynamic / LUFS -14.0 / 439.0s，mix.flac sha `9c4e5f43…`；对照分析 out/ref_analysis/ASSESSMENT.md）。
- **《归潮》交响曲 Op.1（2026-08-24，sym 五轮接力）**：产线第一部**完全原创**交响曲（四乐章 21:04，母细胞 Ω 从零生成、零 MIDI 依赖）——构想（examples/tide_sym/CONCEPT.md）→素材（materials+872 例不变量）→生成器（gen_tide.py 六断言+逐字节确定性）→表情空间全栈→红队终审 0 MAJOR+MF 模型复听独立确认。成品 `out/tide_sym_mvt{1..4}/mix.flac`（sha `eac77f1c`/`6bd23a5c`/`50cb7e82`/`8190efcf`，qc ok ×4）；成品报告与审查史=内部材料，未随开源版发布（BG-D20 分家后在 music_project/docs/）。缺口如实：III 台阶 p75/share（46bpm 长句 5s 块中位稀释，归因红队核验成立）、II master 侧交替 1（premaster 5 达标，双口径披露）。**压缩重构版（R6/R7，用户密度否决后）**：`out/tide_sym_condensed/mix.flac` 178.4s 四相一气呵成——织体最大驻留 5.5s/p75 11.6dB/交接 61.9 每 30s/MF 零静态窗；四乐章版零改动保留对照；R7 教训入坑表（断崖虚报+量具覆盖写缺陷）。
- **产线转向：公有领域乐谱库落成（2026-08-25，BG-D18）**：用户否决《归潮》音乐性并裁定 BGM 默认路线=公有领域经典作品改编实现。双工位普查采集：**3821 条目**（直用 3017=PD 1183+CC-BY 250+CC0 1584；CC-BY-SA 804 挂 FLAG 待裁定；零 NC）——Mutopia 整库（GitHub 镜像 @2144afd6+官网 MIDI+IA 快照补缺）+ OpenScore Lieder/StringQuartets（CC0，MusicXML 符号级）；六条 R-\* 源验收规则 + 管弦八件 PD 缩谱盘点（间接路线材料齐）+ Audiveris OMR 免 sudo 安装与试点成功。源登记 [catalog/scores/REGISTRY.md](catalog/scores/REGISTRY.md)；审查史=内部材料，未随开源版发布（分家后在 music_project/docs/）。
- **BG-D18 路线首件质量标杆：Gymnopédie No.1（2026-08-25）**：萨蒂《裸体歌舞第一号》钢琴独奏——v1（out/gymnopedie1/，126.4s）经用户对照参考演奏（BV1qvM8zJE66）确诊两缺陷（**反复段未展开=47 小节压缩形态缺 40% 材料**；速度 69.6 vs 传统 62）；**完整形态重制 v2=out/gymnopedie1_full/**（232.8s：78 小节展开拼接[切点签名断言]+62 BPM+四段表情弧[陈述2 高潮 S 峰 +2.5dB]+踏板 81 变化点，qc 全绿 Dynamic -14.0，乐句峰 13↔13 与参考版逐一对位）；Mutopia PD 底稿（音符层零改动溯源断言）+ SalamanderGrand 全表情栈；生成器 examples/gen_gymnopedie1.py 逐字节确定性 + test_gymnopedie_data 7 例；附 bed_mix.flac 垫底件。全链重渲两次 sha 全等；v1 按红线④原样存档。
- **拨弦垫底验证件 + 新尼龙吉他引擎（2026-08-25）**：用户裁定"30 秒但质量最高"——**synth nylon 引擎**（`synthlib.py` Karplus-Strong 物理模型：splitmix64 确定性激励/拨弦位置梳/T60 定标/三共振峰琴体，描述符 v1.1.0 走 harvest 正规流程）四轮 MF 盲听+客观量具门胜出 GM 采样件；成品 out/guitar_test30/（30.7s，LUFS -14.0/TP -1.2/Linear 型，Carulli op.241 no.4 圆舞曲 AABB 完整乐句，**CC-BY 4.0 署名义务**）+ bed_mix.flac（同口播 -20.5dB 垫底验证）；生成器 examples/gen_guitar_test.py 断言 G1-G8；fast 380+slow 14 全绿（位级锚点证既有引擎零漂移）。
- **双工位深查：选曲册+音源缺口（2026-08-25）**：①`catalog/scores/BGM_SHORTLIST.md` 建档——三梯队 50 件可投产（吉他拨弦 25/轻快键盘 15/Lieder+SQ 10，68 件 MIDI 实测+155 件 .ly 反复核查；**口播床黄金密度判据 3-7 音/s**；首投产件=Giuliani Op.50《Le Papillon》32 件全大调零反复）；挂起区 804 件 CC-BY-SA 维持（含 Vivaldi 四季全四部——《春》只能走 OMR 间接路线）。②`catalog/timbres_GAPS.md` 建档——乐器覆盖矩阵+八大缺口（钢弦吉他/音乐盒/萨克斯/羽管键琴族→VCSL 单库可解/felt piano…）+补源短名单（试听件 751MB 落 `$MUSIC_ASSETS_ROOT/samples/_audition/` 四要素齐，待主线登记引入：VCSL CC0 头号）；纠偏：竖琴/颤音琴/口哨其实不缺，吉他缺钢弦非尼龙。
- **上游 D27 重构同步（2026-08-26）**：上游视频项目工作区（`<私有视频项目>/`，位置经用户澄清维持原位）完成内部重构——顶层＝各期视频文件夹 + `_library/` 跨期资产 + `_archive/` 历史工程；assets_audio 现位于其 `_library/` 下，samples_root 与本仓库相关绝对路径已同步。本仓库本体未动。**新增 music 索引 skill**（`<个人代理配置（未发布）>`，只路由不装本体——重依赖 `$MUSIC_ASSETS_ROOT` + ComfyUI + 跨项目 samples_root，入 skill 无法自包含；决策依据见上游 D27）。
- **选曲册 v2 三维重排（2026-08-26，用户裁定补知名度×质量维）**：三源实测（CF 名人堂 2025+2026 双榜 600 条/维基双语 81 件/B 站 top3 播放 74 件可信）——**v1 十佳 7 件 fame<4 被数据拉下（"工程好但没人听"）**；双十佳分榜：曝光位（Canon in D 3553 万/欢乐颂 CF#9/Clair de lune v1 漏件修正/月光）×床乐位（Menuet in G eng 满分 16 万/Giuliani Op.50 保级/土耳其补位）；勘误 4 项（**Sor Op.35 实为 CC-BY-SA 不可投产**、Clair de lune 与小狗圆舞曲 PD 在库）；OMR 优先级按实测 fame 重排（四季·春全池第 5）。原始采集数据为内部材料，未随开源版发布，公开表仅保留派生评分；采集工具链在 `$MUSIC_ASSETS_ROOT/scores/tools/`。
- **MusicXML 转换链+Lieder 床乐首批（2026-08-27，闲时任务四）**：stdlib 自研读器 `bgm_gen/core/musicxml_import.py`（零观点：max_cursor 小节长/tie (part,pitch) 邻接制/cue 剔除/tempo 双分支）解锁 openscore 双库——1583/1584 件转 MIDI 落 `$MUSIC_ASSETS_ROOT/scores/openscore-midi/`（清单 `catalog/scores/OPENSCORE_MIDI.md`，抽检音高级解析错 0）；首批三件 Lieder 钢琴床乐 `out/lieder_beds/`（Ständchen/Du bist die Ruh/Mondnacht，主件 QC 全绿+床 -37.3 定档+确定性双证，LISTEN.md 含 CC-BY 义务行）；债务 10 已清账。计划 `docs/PLAN_musicxml.md`（三轮对抗审查 5 BLOCKER 全吸收）。
- **OMR 间接路线首件：《春》全链打通（2026-08-27，闲时任务三）**：IA 镜像失效取证→浏览器会话直取 IMSLP（Vilaprinyó 小提琴+钢琴缩谱 **Public Domain (dedicated)** worldwide，HTML 存证进仓）→Audiveris 400DPI TIFF 底稿（四新坑 REGISTRY §11.2.1）→两遍盲转录+三分片裁决+像素审计链（**e_raw 2.88%≤5% 门过**双口径披露；协议沉淀 docs/OMR_PROOFREADING.md 六坑）→去旋律化三轨改编（NOTE_MAP 溯源断言 S1-S8 机器可验/密度 6.36 音/s/key 回环 E major r=0.90/床 -37.4）。成品 out/spring_omr/（mix 71.9s qc 全绿 Dynamic + bed_mix）；校对报告 PROOF.md+57 修正逐条；间接路线自此可复制（MusicXML→notes 项目局部转换器 examples/spring/mxl2notes.py 首件实装，与任务四包级读器分工）。
- **整片 BGM 集成首件：两模块架构成片（2026-08-28，闲时任务五）**：240.0s 视频 BGM 成品 out/full_bgm_assembly/——①口播床（Canon 骨架@87+GMD groove6 床鼓 v3：kick 14/snare 4/chat 弃无镲、8 拍死循环无轮替）②曝光位五窗名曲（命运/Carulli/Ständchen/春/月光，15-22s 段尾淡出）③synthlib sting×5 调性对齐④间隙接管铁律（微间隙八处床在场实测）。**终混 I=-15.9 积分约束裁定**（契约结构积分-16.3 vs -14 齐次性无解，ab_drumtest 等响优先先例）；九窗 Δ≤0.4dB、床深 22.2dB、kick 主导/snare 极轻、确定性三重门、五硬门终审独立复算全过（0 MAJOR）。mix 含分离人声**整件禁发布**；instrumental.flac 理论可发布附六义务行（GMD=Google CC-BY 署名硬门在 LISTEN §7）。契约与五轮记录 docs/PLAN_full_bgm.md。
- **产线流程第一门：音色先行（2026-09-09，BG-D19）**：用户对历轮成品音色不满意，根因=流程缺步——音色在编排期顺手决定、缺陷到验收期才暴露。裁定创作流程五步=①**音乐要素契约**（乐器清单+逐件音色实现+试听件+用户逐件拍板，落工程 TIMBRE.md）→②底稿/溯源→③编曲（基于锁定音色设计）→④表情/混音/QC→⑤交付；操作细则与契约表模板=PLAYBOOK_BGM.md §〇。
- **仓库分家（2026-09-09，BG-D20）**：用户裁定"工具本体只留核心代码+理念（个人代理配置未发布）"——具体项目（生成器/溯源材料/项目测试/项目文档/voice-ime 工作流）与全部产物 out/（135G 同盘 mv 零拷贝）迁姊妹仓 `<私有项目仓>/`（独立 git 仓，README 含跑法与边界）。本仓配套变更：REPORT 工具级两节抽取为 `docs/USAGE.md`；`out/minimal/` 锚点重渲在位；test_smf_import/test_legacy 缺件即 skip、test_events 弯音证据改落临时目录；workflows 18→14 件（vime 四件随项目走）；`examples/` 仅存 minimal.json+convert_openscore.py；内部 W1B 调用手册（未随开源版发布）（唯一 git 跟踪产物）随 out/ 迁走。上述 §三 各历史条目中的 out//examples//docs/ 相对路径均按此换算为 music_project 侧。
- **音色库迁入仓库目录（2026-09-09，BG-D2 修正案）**：sf2/sfz/samples 三目录真身自 `$MUSIC_ASSETS_ROOT/` 迁入本仓 `assets/`（gitignored，同盘 mv 零拷贝），旧位置留符号链接兼容层——music_project 生成器与冻结工程里的历史绝对路径零破坏（doctor 全项 ok、双仓测试绿验证）；manifest/assets_root（$MUSIC_ASSETS_ROOT，仍含 models/scores/tools 实体）口径不变；`catalog/timbres.*` 记录的绝对路径经符号链接继续有效。上游 `<私有资产配置文档>`（资产宪法）尚未同步此变更——跨项目文档，待用户裁定后更新。

## 四、测试与坑表

```bash
cd scoreweft  # 进入克隆目录（本地开发目录名 music_tools 亦可）
python3 -m pytest bgm_gen/tests -q            # fast 档（默认，347 例——2026-10-11 开源整改后口径，含位级版本门收窄），预算 ≤90s；12 个显式 skip = 6 分家缺件（fate mid×2/eden_v2×2/fate_mvt1/gm_lofi 旧产物，件在 music_project 可指回）+ 6 位级版本门（ffmpeg/fluidsynth 漂移仅门位级哈希断言段，契约/QC/harvest 静态一致性仍无条件执行，见 tests/README.md「位级基线与冻结版本」）
python3 -m pytest bgm_gen/tests -q -m slow    # GPU 引擎冒烟（demucs/master）；位级复现锚点已随项目迁 music_project/tests
python3 -m pytest bgm_gen/tests -q -m service # ComfyUI 依赖项（8188 不可达显式 skip，绝不静默当绿）
```

- **python3 = miniconda base**（`/usr/bin/python3` 无 numpy 不可用）。
- **锚点再生成**：`test_cli` 的 sha 锚点依赖 `out/minimal/mix.flac`（gitignored）——清空 out 后首跑需先 `bgm render examples/minimal.json -o out/minimal`（**2026-09-09 分家后已重渲在位**）。slow 档 eden/fate 位级复现锚点与项目 data 测试已随项目迁 `music_project/tests/`（跑法见该仓 README；本仓 slow 档余=GPU 引擎冒烟）。
- **分家后测试缺口口径（BG-D20）**：`test_smf_import`（fate 底稿 mid 迁走）与 `test_legacy`（gm_lofi_demo.wav 旧产物迁走）为缺件即显式 skip——非静默当绿，件在 `music_project/` 时可指回；`test_events` 弯音量程证据文件改落临时目录（消费方 R4 命运 mapping 已随项目迁走）。
- **render 缺省输出=仓库根 out/**（迁移时已修复旧"相对 cwd 解析"坑：`default_out` 与 cwd 解耦；"必须显式 -o"为旧位置时代的教训，已过时）。
- **HF 下载**：hf-mirror 本机直连不通（HTTP 000）且 308 回源坑——走代理 HTTPS_PROXY（由使用者自行配置） + 官方端点 `HF_ENDPOINT=https://huggingface.co`；**运行期恒 `HF_HUB_OFFLINE=1` + `HF_HOME=$MUSIC_ASSETS_ROOT/models/hf`**（防 demucs 静默回退下载第二份旧格式 .th 权重）。
- **ComfyUI 前置**：service 档与 ai 引擎需 `127.0.0.1:8188`（`bash <ComfyUI 安装目录>/启动脚本`）。
- **GPU 串行（BG-D8）**：本包内 GPU 任务互斥（文件锁）；ComfyUI 等外部进程不持锁，显存探测是尽力而为（demucs CUDA OOM 可 payload.device="cpu" 重试）。
- **工程正本已在产物目录时** render 报 SameFileError → **历史注记（v3 R1 已修复：快照复制改 tmp+rename，不再需要 /tmp 副本）**；v1 报告（music_project/docs/REPORT.md §①/§7.1，2026-09-09 分家迁出）复现命令里的 `cp … /tmp` 写法为旧时代口径。
- **fluidsynth 默认 synth.gain=0.2**：sf2 轨先天偏冷 ~15dB，用力度+轨增益补偿。
- **bpm_check 断言按 top-3 口径**（IOI 折叠对等幅节拍器 78/156 并列）；采样鼓组注意 onset 偏移（多击/慢 attack 伪峰，驯服记录见 docs/REPORT.md §7.4）；管弦长音素材另有恒 +3.5% IOI 系统偏快偏差（命运实测，docs/REPORT.md §八）。

**v3 新坑（2026-08-23 落档）**：

- **VPO 音色失控清单（sfizz 1.2.3，R4 实测，命运工程教训）**：①PERF sustain 族（`*-SEC-PERF.sfz`）loop_continuous 采样**无限渲染**（同一 316.7s MIDI：SEC-sustain 版正常收尾，PERF 版 30s 写出 4.28GB；曾致整机冻死）——引擎层三重护栏兜底拦截（体积闸 1.8s 实拦）+ mapping 映射禁用；②SEC-sustain 族中 **oboe/horn/trumpet/viola 四件在大音符量上下文失控**（单音正常、beat 432 后上下文触发；flute 等 6 件正常）——命运工程换 VSCO2 CC0 四件；③**KS 事件×全量音符同型失控**（clarinet 93 KS×874 音符二分锁定）——双轨叠置回退。**铁律：单音探针通过不能外推全量**。
- **sfizz 一次性非确定实例**：VSCO2 TrumpetSus 1/14 次字节偏差（13 次复现一致）——v3.1 候选=stem 自校验。
- **fast 档预算口径=空闲桌面**：忙桌面（Firefox/ZCode 并行）+7~8s 方差（实测 70.6s→77s），预算 75s 以空闲口径衡量。
- **ffmpeg loudnorm linear 判定 = TP-offset AND measured_LRA ≤ 目标 LRA**（不是 crest——BG-D15 命运校准实证：LRA 12.4→10.5 转 Linear）。
- **大文件实验落磁盘目录而非内存临时目录**（/tmp 为 tmpfs，写入即耗内存——R4 冻机事故教训）；受控渲染统一经 `/tmp/render_guard.py`（进程树 RSS 帽 + MemAvailable 地板 + 越线 SIGKILL）。

**v3.1-v3.4 增量轮坑（2026-08-24 落档）**：

- **sfizz 失控清单第 5 件（v3.1）**：VPO bassoon-SEC-sustain **@192 恒速网格正常、@144+warp 非网格上下文失控**（护栏 7.7s 拦截，197MB>164MB 上限）——失控=音色×全量音符**上下文交互**缺陷，随音符数据变化可复发、**非固定音色黑名单**（同一音色 v3.0 正常 v3.1 失控）；全链渲染必经 render_guard+引擎护栏（mapping `runaway_inventory` 注记），失控件换 VSCO2 同族（CC0）。
- **子智能体任务书陷阱（v3.3 教训）**："等空闲再测"类前置条件在**持续开发机上不可满足=活锁**（worker 等空闲与主线开发占用互为因果）——任务书应给资源上限/时限预算而非"空闲"前置；v3.3 worker 因此被用户叫停、主线收尾（成果 95% 已成）。
- **worker 交互提问通道的授权记录以该通道为准（0160492 教训）**：主线事后核不了 worker 与用户的交互细节——v3.1 曾把 worker 交互提问获得的用户裁定（Dynamic 正门）误判为无据归因而降级"待追认"，后经用户当面确认撤销。交互提问的授权留痕（问答原文/裁定语句）即权威，主线不得以"没见过"降级。

**乐谱源普查轮坑（2026-08-25 落档，BG-D18 配套）**：

- **sfizz 失控清单第 6 件（2026-08-27 Lieder 轮）**：SalamanderGrand V3×**CC64 循环踏板态声部泄漏**——纯音符/单次踏板正常，小节边界抬/踩循环下存在永不终止的泄漏 voice（29s MIDI 线性写 wav >60s，引擎护栏 21MB 拦截）；同音交叠钳制+间隙加宽+收拍抬踏板均不治本，**根治=CC120（all sound off）收尾兜底**（clip 端前 20ms；BG-D5 本截 stem 到 clip 窗，损失不可闻干尾，湿尾由 IR 延续）——`gen_lieder_beds.cc120_terminator` 先例；同日月光轮独立发现同族根因（**踩窗同 pitch≥3 → 0-0.7Hz DC 漂移 → 渲染不终止**，最小复现 p73×3，处置=PEDAL_AVOID 避让+manual_stems 流式截断，见 PLAN_v3 月光段/REVIEW_LOG）——两轮互证：**sfizz×Salamander 踏板态长音=已知缺陷族，投产必带护栏与兜底**。教训：sfizz 失控=**音色×事件组合×上下文**交互缺陷家族（第 5 件同型），单事件探针通过不能外推。

- **站内反爬两闸**：MuseScore.com=Cloudflare challenge（裸 curl 取回 15KB 挑战页）+ MusicXML 导出登录墙；IMSLP `/images/*` 直链=JS friendlytest 302 闸——**批量取件通道=IA `imslp` collection 官方镜像**（权利口径沿用 IMSLP 审核，双站互核）。
- **Audiveris 两坑**：封面/空白页触发 `Sheet removed`→`Error in reaching step PAGE` 整本中止，须 `-sheets M-N` 跳页；deb 解包含无 Tesseract traineddata（`No installed OCR languages`——力度/文本识别降级，补装待办）。
- **shell 引号 `~` 坑**：带引号的 `'~/assets/…'` 不做家目录展开，会在 cwd 建出字面 `~` 目录树（本轮已清）；家目录路径勿整体加引号或改用 `$HOME` 展开。
- **Mutopia MIDI=不展开反复的压缩导出口径（2026-08-25 Gymnopédie 教训）**：带反复记号（volta/alternative）的曲子，MIDI 是"主体一遍+各结尾连奏"形态，完整演奏形态需数据层展开拼接（Gymnopédie 1：谱面 47→演奏 78 小节，LilyPond 源 `\repeat volta` 可佐证切段）——**入库/投产前凡带反复结构的曲子必查 .ly 源或参考演奏时长**；用户对照参考版听出"起伏不到位+偏快"即此结构性缺失，已修复为先例（out/gymnopedie1_full，切点签名断言模式）。
- **MF 盲听两坑（2026-08-25 吉他轮教训）**：①**满幅溢出噪声 MF 仍幻觉"完美无瑕"**——MF 音质结论必须过客观量具门（RMS/谱质心/自相关等）再采信；②**近天花板 0.5 分差排名跨轮翻转**（同文件两轮被判"竖琴 9.5"与"合成器"）——MF 定档只作参考，最终以"音色身份忠实+确定性"裁决。
- **床乐电平标定必须按 S-LUFS 中位实测口径迭代**（吉他轮教训）：轨增益写 -20dB 实测仅差 15.5dB（源文件响度结构差异）——垫底标定一律以目标 S-LUFS 中位反算增益，不按名义轨增益。
- **Guitar-Skole 系列 .ly 源缺失**（IA 快照补 MIDI 的那批）：反复状态无法查证——投产前须听辨对照参考演奏（Gymnopédie 教训的残留风险面）。
- **Mutopia composer 字段极脏**（Bach 9 种拼写、日期后缀变体）：检索必须多拼写聚合，单拼写计数会严重低估。
- **VSCO2_CE 打击/管风琴电平缺陷**（音源轮实测）：Glocken 高位键 -63.5dB / Marimba -54~-57dB / GM-StylePerc -77.7dB（废）/ OrganQuiet -61dB——该库 idiophones/organ 用前须 +20dB 补偿或换 VPO/VCSL。
- **codeload tarball 经代理反复截断**：大仓取件走 git clone（--depth 1 / sparse-checkout）。
- **平台采集限制**：采集受平台风控限制，需自行合规获取。

**闲时任务五坑（2026-08-28 落档，响度测量族）**：

- **ebur128 S 打印 t<3s 为门控无效值**（3s 窗未填满时 ~-121dB）：片首窗中位若不滤 >-60 会被拉低 0.6dB（实测 W0=[0,22] -14.9 假 vs -14.3 真）——凡片首起测的 S 统计必须带 >-60 过滤或排除 t<3s 打印点。
- **stems bus 层测量双口径坑**：bus wav 为 float32 交织流（wave 模块直读报 unknown format: 3，走 _wavio.read_audio）；**单声道下混有 -3.0dB 系统偏差**（LUFS 能量折算），元素标定必须立体声域；帧级统计口径（间隙段均值 vs 滑窗中位）同数据差 1.5-4dB，披露须钉死口径。
- **en.wikipedia.org 直连域经代理会被 TLS 切断**：wiki API 走 `api.wikimedia.org` 官方域（429 时 0.7s→1.4s 限速+补跑）；条目挑选按"归属优先"两级规则防 disambiguation/通用曲式条目陷阱。

## 五、遗留债务（docs/PLAN.md §8 + 仓库现状；v3 落档划账 2026-08-23，v3.1-v3.4 增量轮划账 2026-08-24）

1. **可选档未装**：DiffRhythm（BG-D10 用户明确后再装）、Stable Audio Open（gated）、Carla；VPO 原为可选档，已于 v2 提质轮装上（`sfz/VPO`，454 sfz）。
2. **sudo 段引擎未接引擎层、未冒烟**：lmms/calf/jalv/yoshimi/amsynth/synthv1/drumkv1/samplv1/zam-plugins（可选引擎，仅 fluidsynth CLI 出过声）。
3. ~~cli stem/master/qc 负分支无 pytest~~ **已清账（v3 R4-W2：`tests/test_cli_negative.py` 6 例，exit 1 无 Traceback）**。
4. **gen_eden/gen_eden_v2 生成器重跑无自动回归**（渲染链已有 `test_eden_repro` 位级锚点；**防前科重演的生成器确定性回归目前仅覆盖 gen_fate**——v3 `test_fate_data` 已锁 tmp 对拍逐字节一致；gen_eden/gen_eden_v2 维持债务，生成器本身两次人工逐位复现已证）。
5. **Karoryfer 原始 zip 476MB 与解压目录并存**（待用户裁定删否）。
6. **doctor 二进制探测缓存不对称**（v3 新记，低优先）：测试会话缓存已做（`tests/helpers.doctor_report_once`，fast 73.6→70.0s），但 `doctor.py` CLI 子进程路径未缓存——仅影响手动 `bgm doctor` 的 ~2s 探测耗时。
7. **空间化顺序段未并行**（v3.4 新记，v3.5 候选）：命运工程忙载实测仅 1.10×——Amdahl 瓶颈=wet 总线 OLA 卷积与轨链依赖的顺序段+外部负载（夹具微工程 2.97×）；空间化段池化为 v3.5 候选项。
8. **长音内连续渐强缺口（采样器层）**（ASSESSMENT §二/§4.6 预告，v3.1 确认遗留）：sus 轨（SEC/VSCO2 sustain）无 CC 响应，单音内 swell 只能音头 vel+轨级 gain 自动化近似——乐句级弧线已达成，单音内渐强仍未有；CC1/CC11 响应的 sfz 长音库调研待做。
9. **乐谱库待裁定/待办（2026-08-25 新记，BG-D18）**：①Mutopia CC-BY-SA 804 条目（含 ksnortum 制谱 WTC 全集等核心曲目）ShareAlike 传染性对改编成品的影响待用户裁定，裁定前只检索不投产；②霍尔斯特《行星》US 分发路径（1914 手稿 OMR 难 vs Curwen 印刷版约 2044 入 US 公版）待拍板；③Musopen FAQ 逐字引文未固化（CF 盾，人工浏览器一次可补）；④Mutopia 180 件 ly-only 无 MIDI（本机无 lilypond，投产需渲染链或转换链）；⑤Audiveris Tesseract traineddata 补装（力度/文本识别当前降级）。
10. ~~**MusicXML→MIDI 转换链缺口**~~ **已清账（2026-08-27 闲时任务四）**：自研 stdlib 读器 `bgm_gen/core/musicxml_import.py`（零观点，notes 四元组对齐 smf_import 契约）+ 批转器 `examples/convert_openscore.py`——openscore 双库 1583/1584 件已转 MIDI 落 `$MUSIC_ASSETS_ROOT/scores/openscore-midi/`（260 万音符，vel 恒 64 无表情底稿、反复未展开按书写序单遍；抽检 6 件 mutopia 交叉源 Voice 相似度全 ≥0.95+4 件 roundtrip 零错配，清单 `catalog/scores/OPENSCORE_MIDI.md`）；首批三件 Lieder 钢琴床乐投产 `out/lieder_beds/`（Ständchen/Du bist die Ruh/Mondnacht 前奏延展段，QC 全绿+床 -37.3 S-LUFS 定档）；计划与三轮规划审查+各轮执行记录 `docs/PLAN_musicxml.md`。
11. **音源引入待办（2026-08-25 音源轮新记）**：_audition 试听就绪待登记引入（VCSL CC0 头号/MTG.SoloSax BY4/Emilyguitar CC0/ganjo CC0/FreePats 尤克里里+尼龙吉他 CC0/CP80 BY3）；四件 FLAG 待用户裁定（Terkelsen 曼陀林无许可文本/Kay 班卓 GPL/FreePats 钢弦 GPL/jRhodes3d 双许可边界）。

12. **2026-09-11 健壮性体检遗留（未修项登记）**：①多路 ffmpeg 调用仍无统一超时包装（mixer/qc/project 终编/sf2/ai 共 ~7 处——本地短转码风险低，demucs 主险已加墙钟，M-2 见 commit 926a263）；②ai.py urlretrieve 无 timeout（/view 下载挂起会阻塞）+ wf 读 JSON 未显式 utf-8；③sf2 fluid_player_add 返回值未检（add 失败只渲 40 块尾巴静音且过存在性检查，内部路径受控）；④qc.measure 同文件解码 4 次（纯性能）；⑤sf2 runtime.json 若手写带斜杠相对路径会静默回退系统库（doctor 文案已引导写全路径）。当日已修：sf2 三级解析+doctor 联动、demucs 墙钟、临时文件 finally×3、CLI 错误口径×2、轨名过滤、nylon 目录条目、确定性声明降级——见 commit 926a263。

## 六、指针

| 文档 | 内容 |
|---|---|
| [README.md](README.md) | 仓库总览：快速上手/引擎总表/音色目录/目录地图 |
| [docs/PLAN.md](docs/PLAN.md) | 整合规划 v1.4：§2 决策全文、五轮瀑布定义、QC 阈值、风险登记册 |
| [docs/PLAN_v3.md](docs/PLAN_v3.md) | **v3 升级计划 v1.1**：描述符/事件流/五动词/双布局 + 命运验收；BG-D11..D17 记录源与 §10.4-§10.13 执行期记录（§10.10-§10.13 = v3.1-v3.4 增量轮） |
| [docs/USAGE.md](docs/USAGE.md) | **CLI 速查 + 署名义务**（2026-09-09 分家自 REPORT §⑤/§7.6/§8.5 抽取的工具级常备内容） |
| [docs/MIGRATION.md](docs/MIGRATION.md) | 迁移史与路径换算 |
| [bgm_gen/engines/README.md](bgm_gen/engines/README.md) | 引擎插件开发契约（如何新增引擎）+ 描述符注册表 |
| [workflows/README.md](workflows/README.md) | ComfyUI 工作流逐件说明与提交方式（通用 14 件） |
| [catalog/scores/REGISTRY.md](catalog/scores/REGISTRY.md) | 公有领域乐谱源登记表：R-* 验收规则 / 逐源许可引文 / 管弦八件缩谱盘点 / OMR 事实卡（BG-D18 配套） |
| [catalog/scores/GUIDE.md](catalog/scores/GUIDE.md) | 古典音乐库全景科普：五时期听感画像 / 体裁课 / 情绪场景选曲速查 / 入门十首路径（选曲者无背景可读） |
| [docs/PLAYBOOK_BGM.md](docs/PLAYBOOK_BGM.md) | BGM 创作经验手册：§〇 音色契约门（BG-D19 第一门）/用户裁定记录/工艺栈清单/坑表精要/验收文化（后续创作子智能体必读） |
| `<私有项目仓>/` | **项目案例仓（BG-D20 分家目标）**：docs/（REPORT 成品报告/REVIEW_LOG 审查史/PLAN_musicxml/PLAN_full_bgm/PLAN_spring_omr/idle_tasks 五任务书）+ examples/（项目生成器+溯源）+ tests/（项目回归测试）+ out/（全部成品 135G 含 LISTEN/PROOF）——索引见该仓 README.md |
| `<私有资产配置文档>` | 上游 AI 资产宪法（ComfyUI/模型/H3 等，操作前先读对应项目节） |

> 最后更新：2026-10-11（BG-D21 项目定名 Scoreweft：对外名称/开源仓库名更名与文档同步，CLI `bgm` 与包名 `bgm_gen` 不变；此前 2026-09-09 BG-D20 仓库分家/BG-D19 音色先行门/BG-D2 修正案）
