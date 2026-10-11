> **迁移注记（2026-08-22）**：本工具已自 `<私有视频项目>/bgm_gen` 迁移至
> `<仓库根>`（独立仓库）。文中旧相对路径按此换算：包内文件
> `bgm_gen/…`；产物 `out/…`（已提升至仓库根）；工作流 `workflows/…`；旧脚本
> `bgm_gen/legacy/…`；分析脚本 `bgm_gen/analysis/…`；下载工具 `tools/…`。
> 迁移与重构详情见 [MIGRATION.md](MIGRATION.md)。

# bgm_gen 开源音色与生成器套件终端整合规划

> 版本 v1.4（2026-08-21，三轮对抗式审查 + 用户方向裁定）｜瀑布五轮 + worker/reviewer 交替协议
> 任务定义：下载配置所有值得装的开源音色/生成器套件，整合为统一 CLI 终端工具，补全功能，完成一轮测试，并用全部复杂功能合成一首电子乐成品。
> 本文档是唯一事实源：每轮子智能体的提示词必须引用本文档路径与所属轮次章节。
> 决策编号 BG-D1..BG-D10，与 AGENTS.md 的 D1-D17 独立（整合结果最终在 AGENTS.md 追加新节落位，清单见 §8）。

---

## 0. 验收总则（最终 DoD）

1. `bgm` 统一 CLI 可用，子命令：doctor/engines/render-engine/render/stem/master/qc。
2. 资产 manifest（JSON）记录每一件音源与模型：约定根相对路径、体积、许可证、驱动方式、冒烟验证状态；doctor 校验 manifest 与 runtime.json 一致性。
3. pytest 分档测试全绿：**fast（确定性引擎+资产+QC 回归+旧脚本回归）<10 分钟；slow（GPU 引擎冒烟，标记后可分批跑）全绿；service（ComfyUI 依赖项）在服务不可达时显式 skip 并计入报告，不得静默当绿**。`bgm doctor` 一键体检。
4. 一首 ≥2.5 分钟的多引擎电子乐成品（out/<project>/mix.flac）QC 达标（§6.3），全程 project.json 可复现（按引擎确定性分级判定，见 R5）。
5. 旧脚本回归自动化（test_legacy 层）：gm_lofi/midi2wav/demo_lofi/key_check/bpm_check 断言退出码 0+产物 sr/时长/RMS 阈值；gen.py 断言退出码 0+产物存在（AI 非确定性免 RMS）。CLI 契约（argv/cwd）冻结。
6. AGENTS.md 以"只增不改"方式追加整合结果一节（内容清单见 §8）。
7. **人工试听门（终验）**：R5 机器验收通过后，主线产出最终报告（成品路径、结构时间戳、功能清单①-⑩引擎出场对照、QC 摘要、试听指引），**用户试听确认后 R5 才关闭**（对齐 AGENTS.md D8"质量合格=用户人眼确认"惯例）。

**红线（不可违背）**：①BGM 产线仅用 CC0/MIT/Apache/BSD/GeneralUser 类可商用许可（AGENTS.md D17），禁 NC；②不破坏 ComfyUI 环境（comfyui env 一律 --no-deps/独立 venv）；③sudo 最小化集中且存在完整免 sudo 替代路线；④旧产物不删除；⑤旧脚本 argv/cwd 行为冻结（ab_steps.py 依赖 gen.py 契约）。

---

## 1. 调查结论摘要（两路调查 + 三轮审查实测，2026-08-21/22）

**现状**：三产线全通（ACE-Step 1.5 via ComfyUI 127.0.0.1:8188 常驻；synthlib 纯 numpy DSP；MIDI→libfluidsynth ctypes+FluidR3_GM）；双引擎环已闭环；QC 三件套在位；磁盘 1.1T；RTX 4080 16GB；espeak-ng 已在位。**缺口**：无包结构无统一 CLI；仅 1 个 sf2；无 SFZ 引擎/demucs/pretty_midi。代码形态：midi2wav/gm_lofi 模块级即执行；gen.py 输出名由 ComfyUI 决定且依赖 cwd；**bpm_check IOI 折叠对等幅节拍器 78/156 得票并列，top-1 恒出高频（测试断言必须按 top-3 口径写）**。

**生态判定**（核实+实测）：
- Fedora 源有：yoshimi、zynaddsubfx、lmms 1.2.2（`lmms -r`）、calf、amsynth、synthv1/drumkv1/samplv1、jalv、lv2、fluidsynth CLI、zam-plugins；无 sfizz/carla/surge。
- sfizz：audinux COPR rpm 直链下载→解压 $MUSIC_ASSETS_ROOT/tools/sfizz+LD_LIBRARY_PATH 免 sudo（已实证渲染）。旗标式 `--sfz/--midi/--wav`，默认 48kHz（BG-D5 统一重采样）。lexridge 无 tools 降补充；pysfizz 末级回退。
- 音色库：VSCO2 CE SFZ 在 `SFZ` 分支（git clone --depth 1 -b SFZ，~2.3GB，无 Range 不走分块）；GeneralUser GS 走 GitHub 镜像 `mrbumpy409/GeneralUser-GS`（93MB）；Karoryfer 需先定位直链否则降可选；Musyng Kite（BY-SA）/SGM-V2（许可不明）排除。
- AI：**扩散模型定位见 BG-D10（用户 2026-08-21 裁定）**——产线内保留 ACE 1.5 系列（本地实测：XL+4B 调性 r=0.91 断层领先，属当年代际有效配置）与 Music3；MusicGen（2023，NC 许可）排除；**DiffRhythm（2025-03 代际）降可选档**：差异化（人声全曲+RTF 快）与 Music3/ACE 重叠，且需独立 venv-dr+6.1GB 权重，用户明确后再装。demucs 4.1.0 兼容 comfyui env（处理工具非生成器，保留必装）；权重 HF `adefossez/HTDemucs`（HF_HOME+hf-mirror）。matchering 2.0.6 下限式依赖可进 comfyui env（--no-deps+补 resampy/statsmodels）。Stable Audio Open（gated）可选档。
- 插件合成器须过 Carla → 可选档；lv2apply 无 MIDI 端口只做效果器；混音总线=ffmpeg 滤镜链。

---

## 2. 总体架构（分层）

```
┌─ CLI 层    bgm（python -m bgm_gen）：doctor/engines/render-engine/render/stem/master/qc
├─ 编排层    project.json（单一事实源）→ 渲染计划 → stems 汇合（BG-D5）→ 混音 → 母带 → QC
├─ 引擎层    envelope+payload 接口（BG-D6）：
│   synth(synthlib)｜sf2(libfluidsynth ctypes)｜sfz(sfizz_render 子进程)｜sample(one-shot numpy)
│   ai(ComfyUI HTTP)｜stem(demucs)｜master(matchering/loudnorm)｜diffrhythm(可选档，venv-dr 存在才实现)
├─ FX 层     ffmpeg 滤镜链总线（comp sidechain/eq/delay/afir/loudnorm）
└─ 资产层    $MUSIC_ASSETS_ROOT/{sf2,sfz,samples,models,tools,venv-dr} + bgm_gen/assets.json
```

**数据主权原则**（审查必查）：工程=磁盘开放 JSON，人与 AI 等权读写、可 diff、可 git；引擎全部 CLI 无头驱动；云端/黑盒仅限 ComfyUI 本地服务。

**关键决策（BG-）**：
- **BG-D1** CLI 名 `bgm`：包目录 bgm_gen/（`__init__/__main__/cli.py`），入口 `python3 -m bgm_gen`+`~/.local/bin/bgm`；包骨架 R2 开工首项建立。
- **BG-D2** 大资产放 $MUSIC_ASSETS_ROOT/；manifest 存约定根相对路径+许可证+sha256；.gitignore 为 R3 交付。
- **BG-D3** 解释器分档：基础=系统 python3；demucs/matchering=comfyui env python；DiffRhythm=venv-dr python；runtime.json 唯一写入者=doctor（探测逻辑 R1 收尾实现，R4 只做呈现）；引擎只读；doctor 兼任 manifest↔runtime.json 一致性校验者。
- **BG-D4** 旧脚本改造边界：允许重构为函数+`if __name__` 守卫（判定=CLI 契约与输出不变）；SMF 写入器上移 engines/midi_util.py；gen.py 契约冻结，包内 ai 引擎为新模块复用其提交/轮询逻辑。
- **BG-D5 stems 契约**：meta.sr/channels 全局权威（默认 44100/2）；stem 渲染后强制归一（重采样到 meta.sr、mono 由 mixer 定声像、短 stem 补零至 section 窗、超长截断）；验收"正确 sr"=等于 spec 声明 sr。
- **BG-D6 引擎接口=envelope+payload**：envelope（engine/spec_version/sr/channels/时长出参）统一；payload 各引擎子 schema 各自版本化。
- **BG-D7 工程格式**：单文件 project.json，schema v1 语义规范见 §5 R3。
- **BG-D8 GPU 串行保护**：ai/stem（及可选 diffrhythm）执行前 nvidia-smi 探测空闲显存，不足排队/提示；互斥。
- **BG-D9 out/ 命名**：冒烟 out/smoke/<engine>/；工程 out/<project>/stems/<track>.<engine>.wav 与 out/<project>/{mix.flac,project.json,qc.json}；ai 取回后按规范改名。
- **BG-D10 扩散模型定位（用户裁定 2026-08-21）**：扩散=**整段素材生成器**（几十秒级波形、整体质感与人声层、产物按"录音素材"对待），**不是音色引擎**——音色合成是算法/采样的领地（参数空间精确导航、构造即事实、改一行=改谱）。扩散产物必须经降维闸口（audio→MIDI 转写或 demucs 分轨）转成符号/stem 后才进入逻辑编排。**模型准入三门槛**：①当年代际且本地 QC 实测有效；②许可证可商用；③本地无头可驱动。旧代际模型默认不进产线（MusicGen 2023 排除；DiffRhythm 2025-03 降可选，用户明确后才装）。

---

## 3. 资产清单（三档）

**必装（v1.4 起 ~3GB，2-4 小时；DiffRhythm 移可选）**
> 勘误（终审 MINOR-①，2026-08-22）：R1 实测后实际落盘总量 ≈6.4GB——VSCO2 SFZ 分支工作树 5.2GB（含 .git pack，PLAN 预估 2.3GB 系 clone 传输量口径），GeneralUser 31MB、Karoryfer 三库 497MB、工具与权重余量同前。
| # | 资产 | 许可证 | 渠道 | 驱动 | 体积 |
|---|---|---|---|---|---|
| 1 | 系统包（sudo 段）：fluidsynth CLI、yoshimi、calf、jalv、lv2、lmms、amsynth、synthv1/drumkv1/samplv1、zam-plugins | GPL/LGPL | dnf | CLI/LV2 | ~600MB |
| 2 | sfizz（含 sfizz_render） | BSD-2 | audinux rpm 直链→解压 tools/sfizz（免 sudo 实证）；sudo 后 dnf 补装 | sfizz_render | ~30MB |
| 3 | comfyui env（--no-deps）：demucs 4.1.0、matchering 2.0.6（补 resampy/statsmodels）、pretty_midi、midiutil | MIT/GPL/MIT/MIT | pip | python | <100MB |
| 4 | GeneralUser GS sf2 | 免费可商用 | GitHub mrbumpy409/GeneralUser-GS（代理） | fluidsynth ctypes | ~93MB |
| 5 | VSCO2 CE SFZ | CC0 | git clone --depth 1 -b SFZ（代理） | sfizz_render | ~2.3GB |
| 6 | Karoryfer CC0 选 2-3 库 | CC0 | 先定位直链，失败降可选 | sfizz_render | ~500MB |
| 7 | demucs htdemucs 权重 | MIT | HF adefossez/HTDemucs（HF_HOME→models） | demucs CLI | ~85MB |

**可选**：**DiffRhythm（2025-03，Apache-2.0；用户明确后再装：独立 venv-dr+官方 requirements+phonemizer+钉 commit，权重三件 ~6.1GB，--chunked 默认）**；Stable Audio Open Small（gated）；VPO（CC-BY）；Carla+audinux；yoshimi 音色库；Karoryfer（定位失败时）。
**排除**：MusicGen（NC）；SGM-V2；Musyng Kite；LinuxSampler；lv2apply 驱动合成器；sfizz 自编译。

---

## 4. 目录与命名规范

```
bgm_gen/
  __init__.py __main__.py cli.py          # CLI（骨架 R2，编排充实 R3）
  engines/{__init__,base,midi_util,synth,sf2,sfz,sample,ai,demucs,master}.py  # diffrhythm.py 可选档
  core/{project.py,mixer.py,qc.py}        # R3（qc.py 含无声窗/ebur128 测量，见 R3）
  assets.json runtime.json .gitignore
  tests/{test_assets,test_engines,test_cli,test_qc,test_legacy}.py   # marker: fast/slow/service
  PLAN.md REVIEW_LOG.md
  （旧脚本与 wf_*.json 原地保留，改造边界 BG-D4）
$MUSIC_ASSETS_ROOT/{sf2,sfz,samples,models,tools/sfizz}/（可选 venv-dr/）
out/smoke/<engine>/…；out/<project>/{stems/,mix.flac,project.json,qc.json}
```

---

## 5. 五轮瀑布开发定义（每轮：worker 并行 → reviewer 对抗审查 → 主线修复 blocker 放行下一轮）

### R1 资产层（3 worker 并行；验收分免 sudo 核心/sudo 补充两段）
- **W1A 工具链**：①免 sudo（先行）：audinux sfizz rpm 直链→解压 tools/sfizz→LD_LIBRARY_PATH 包装（ldd 缺失库同样 rpm 免 sudo 解压补齐）；②sudo 段（轮首弹一次密码框，超时不阻塞）：dnf 系统包。
- **W1B Python/AI**：comfyui env 装 demucs/matchering/pretty_midi/midiutil（逐个 pip download --no-deps 审树+装后 torch 冒烟）；htdemucs 权重经 hf-mirror 下到 music_assets/models（HF_HOME，尺寸校验）；冒烟：demucs 分轨 10s 音频。（DiffRhythm 已移可选档：用户明确后再执行 venv-dr+权重三件流程）
- **W1C 音色库**：GeneralUser 镜像直下；Karoryfer 定位直链（失败降可选记录）；VSCO2 SFZ 分支 clone（重试 3）；落位规范化+sfz 乐器入口索引。
- **R1 收尾**：doctor 探测+写 runtime.json（BG-D3）。
- 交付：资产落位+assets.json（相对路径/许可证/体积/sha256/冒烟状态/驱动方式）+每引擎 ≥2s 冒烟音频（out/smoke/）+runtime.json。
- 验收命令化（免 sudo 核心）：`sfizz_render --sfz <vsco2 乐器> --midi <测试 mid> --wav out/smoke/sfizz/x.wav` 成功；`demucs`/venv-dr 冒烟产物存在且 RMS>0；manifest 与磁盘 diff 为空；许可证全白名单。
- 验收（sudo 补充，可挂起）：fluidsynth CLI/lmms -r/calf/jalv 冒烟（全为可选引擎，不阻塞）。
- 回退：Karoryfer/VSCO2 失败→降可选（sfz 冒烟用 VPO 或任一 SFZ 顶替）；AI 素材统一由 ACE 承担（BG-D10）。

### R2 引擎适配层（2 worker 并行；W2A 首项=建包骨架）
- **W2A 确定性引擎**：①包骨架（__init__/__main__/cli.py 空树+engines/core）；②base.py envelope（BG-D6）；③midi_util.py（SMF 上移+旧脚本薄包装，回归 §0.5）；④sf2（ctypes 复用，任意 sf2+program+通道表）；⑤sfz（sfizz_render 子进程+48k→meta.sr 重采样）；⑥sample（Kenney one-shot）；⑦synth（synthlib 包装）。
- **W2B AI/处理引擎**：ai（新模块复用 gen.py 逻辑，契约冻结）；diffrhythm（可选档：venv-dr 存在才实现，否则 manifest 记录跳过原因）；demucs（HF_HOME 注入+stems 约定）；master（matchering/loudnorm 双策略）；GPU 串行（BG-D8）。
- 交付：引擎模块+冒烟+`bgm render-engine --engine X --spec spec.json`（spec=JSON 文件；CLI 校 envelope、引擎校 payload）。
- 验收：各引擎渲染 sr=spec 声明值、时长/RMS 达标；**确定性预检：同 spec 渲两遍，逐分帧 RMS diff，逐引擎分级"确定/容差/不确定"并记入 manifest**；**逐引擎 RMS 基线实测冻结进测试（≥3dB 余量；sfz 断言基于重采样后基线）**；GPU 引擎不与 ComfyUI 冲突；旧脚本回归通过。

### R3 编排层（1 worker 串行）
- `bgm render project.json -o out/<project>/` 全链路：stems 并行渲染→BG-D5 归一→ffmpeg 总线（sidechain ducking）→母带→qc.json；充实 stem/master/qc/engines/doctor 子命令；.gitignore；**core/qc.py 新增测量器：无声窗口（silencedetect/能量闸）、LUFS/真峰值（ffmpeg ebur128 两遍法）、高频能量占比（>8kHz ratio，替代肉眼"削平"判定）**。
- **project.json schema v1 语义规范**：
  - meta：sr(44100)/channels(2)/bpm/key/timesig/seed/duration_hint/spec_version。
  - 记谱统一：notes=[pitch(MIDI 0-127), beat(浮点), dur(浮点 beat), vel(0-127)]；鼓=GM 打击位；引擎内部换算 tick/秒/音名。
  - tracks[]：engine、instrument（sf2=bank:program、sfz=sfz 文件、synth=音色函数、sample=文件）、notes、gain_db、pan、clip 窗口。
  - sections[]：{name,start_beat,length_beat} 时间窗；~~track.clips[] 引用 section+局部原点~~ **语义修订（2026-08-22 主线裁定，R3 审查 MAJOR-2）**：v1 实现为每轨单 clip 绝对窗口（clip:{start_beat,end_beat}，notes 为轨道局部 beat 经 clip 平移到全局），sections 纯标注不参与渲染；重复段落（如 drop2）用整轨复制表达——数据层显式且确定性优先，clips[] 多段引用延后到 v2 有真实需求再议。
  - automation[]：{target_track, param(引擎注册参数名), points[[beat,value]], curve(linear/exp)}。
  - sidechain：{trigger_track, targets[], threshold/ratio/release}。
  - bus：per-track ffmpeg 滤镜链数组；master：{target_lufs, true_peak, chain, qc 目标}。
  - JSON Schema 文件+最小示例工程随 R3 交付。
- 交付：schema+最小示例工程端到端渲染成功（out/<project>/{mix.flac,qc.json}）。
- 验收：旧脚本回归；最小工程 mix+qc 产出；schema 版本字段与实现一致；**R2 确定性引擎冒烟集重跑通过（秒级成本）**。

### R4 测试层（1 worker）
- pytest 五层+三档 marker（fast/slow/service）：
  - ①资产存在性（manifest 全项+大小+许可证白名单+**驱动方式字段非空且与 runtime.json 一致**）[fast]
  - ②引擎冒烟（确定性引擎 2s 渲染：sr/时长/RMS≥冻结基线-3dB）[fast]；（GPU 引擎按各自最小可行档：ai=ComfyUI 最短工作流、diffrhythm=30s 样片、demucs=10s 分轨）[slow]
  - ③CLI 端到端（最小 project.json→渲染→QC 断言调性/BPM 容差）[fast]
  - ④QC 回归：合成节拍器（**加轻微幅度抖动+底噪破坏 IOI 并列**）→**断言 top-3 候选含 78±3 或其 1/2/2 倍频**；合成三和弦→**top-1 r≥0.70 且 top-2 必含 D minor** [fast]
  - ⑤test_legacy：旧脚本全跑（§0.5 判定）[fast]
  - service 档：ComfyUI 8188 不可达时 pytest.mark.skip+计数入报告。
- `bgm doctor` 呈现层（探测逻辑 R1 已有）：解释器/依赖/资产/ComfyUI/GPU/磁盘逐项绿红。
- 交付：`python -m pytest bgm_gen/tests -q`（fast 全绿 <10min）+slow 清单与执行记录。
- 验收：fast 全绿<10min；slow 全绿（可分批）；skip 显式计数；失败可定位；不依赖外网（前置服务清单写入 tests/README：ComfyUI 8188、conda comfyui、venv-dr、代理仅下载期用）。

### R5 电子乐成品（1 worker，作曲+工程+渲染+QC）
- 委托作曲：≥2.5 分钟，intro-build-drop-break-drop2-outro；功能清单全勾：
  ①synthlib：808 鼓组+贝斯+FM 电钢+lead（automation 走 schema）；②sf2：pad/弦乐；③sfz：VSCO2/Karoryfer 管弦 hit/旋律（Karoryfer 缺席则 VSCO2 双乐器）；④sample：Kenney one-shot；⑤AI：ACE 生成素材（DiffRhythm 可选装后可换），尝试 demucs 分轨取一轨并记录质量，不合格则以 AI stem 与确定性 stem 交叉混用等效替代；⑥sidechain ducking；⑦≥2 条 automation；⑧母带 -14LUFS±1/TP≤-1dBTP；⑨QC 三件套+ebur128 复测；⑩mix.flac+stems+qc.json+spec 频谱图（BG-D9 落位）。
- 交付：out/eden_track/{mix.flac,project.json,qc.json,stems/,spectrum.png}+**最终报告 REPORT.md**（模板见 §8）。
- 验收：§6.3 机器阈值全过+**复现判定按 R2 确定性分级裁剪：确定引擎逐位一致；"容差/不确定"引擎比 BPM 相同+调性一致+per-stem RMS 带（±1dB）；LUFS 不作复现判据（被 loudnorm 钉死无信息量）**；schema 变更走控制流程（协作协议第 3 条）。
- **R5 关闭条件=用户试听确认（DoD 7）**。

### 协作协议
1. worker 提示词必含：PLAN.md 路径+本轮章节+验收标准+网络约定（代理 HTTPS_PROXY（由使用者自行配置）、HF_ENDPOINT=https://hf-mirror.com、git 走代理、分块模板 par_dl.sh）+红线+改动范围（仅 bgm_gen/ 与 $MUSIC_ASSETS_ROOT/）+输出要求（改动清单+验证证据）。
2. reviewer 提示词必含：PLAN.md 路径+本轮验收标准+对抗立场，输出 BLOCKER/MAJOR/MINOR，只审不改。
3. **轮间回归与变更控制**：每轮验收含重跑确定性引擎冒烟集；R5 作曲中发现 schema 不够用→报主线批准+spec_version bump+R3 最小示例回归重跑，禁止 worker 静默改 schema。
4. 主线：派发、汇总、修 blocker、放行、维护 REVIEW_LOG.md 与 AGENTS.md 追加节（收尾，清单 §8）。

---

## 6. 风险登记册与回退

| 风险 | 概率 | 缓解/回退 |
|---|---|---|
| sudo 密码框无人应答 | 高 | 两段制验收；sudo 段全可选引擎，挂起不阻塞 |
| pip 破坏 comfyui env | 中 | --no-deps+叶子补装；DiffRhythm 独立 venv-dr；装后 torch 冒烟 |
| 显存竞争 | 高 | BG-D8 串行+--chunked |
| DiffRhythm（可选档） | — | 不在关键路径；R5 AI 素材由 ACE 承担（BG-D10） |
| 音色库 URL 失效（已实锤 404×2） | 高 | 镜像/先定位/SFZ 分支 clone |
| 大文件下载卡死 | 中 | hf-mirror+代理+分块断点+sha256 |
| 旧脚本回归破坏 | 中 | BG-D4+test_legacy 每轮重跑 |
| 并行 worker 写冲突 | 中 | BG-D9 命名空间；manifest 主线合并 |
| 测试指标脆断 | 中 | 断言全部按 top-3/容差口径+基线冻结≥3dB 余量 |
| lmms 1.2.2 参数差异 | 低 | 仅可选引擎 |
| 许可证误用 | 低 | manifest 强制 license+R4 白名单断言 |

## 6.3 成品 QC 阈值（R5 机器验收，工具已指定）
- 时长 ≥150s；无声窗口 ≤1.5s（qc.py silencedetect/能量闸）；LUFS 综合 -14±1 与 TP ≤-1dBTP（ebur128 两遍法）；
- BPM 误差 ≤2%（bpm_check top-3 口径）；调性 top-1 r≥0.70 或 top-2 命中（key_check）；
- 高频能量占比异常检测（>8kHz ratio 阈值，替代肉眼削平判定）；复现按确定性分级（R5 验收）。

---

## 7. 审查记录

**第 1 轮（技术可行性/环境网络）**：3 BLOCKER（sfizz 源/VSCO2 分支/DiffRhythm venv）+5 MAJOR+6 MINOR → v1.1（详见 REVIEW_LOG.md）。
**第 2 轮（架构/数据/CLI/哲学）**：3 BLOCKER（schema 语义/轮次倒置/stems 契约）+4 MAJOR+5 MINOR → v1.2。
**第 3 轮（测试完备性/验收）**：4 BLOCKER（人工试听门缺位/R4 指标矛盾（分档 marker+skip 记账）/复现判定空洞（确定性预检+分级裁剪+LUFS 除名）/节拍器断言恒挂（top-3 口径+抖动破坏并列））+5 MAJOR（test_legacy 层/三项测量器实现归属/RMS 基线冻结/chroma 阈值定值/轮间回归+变更控制）+4 MINOR（doctor 兼任一致性校验/REVIEW_LOG 模板+AGENTS 落位清单/验收命令化/服务前置清单）→ v1.3。

**用户方向裁定（2026-08-21，规划批准问答）**：扩散模型定位=**整段素材生成器，非音色引擎**；音色=算法/采样的领地（逻辑编排与扩散是两条路，扩散仅在几十秒整段生成上有优势，音色级不如算法）；模型准入=当年代际且本地实测有效。据此新增 BG-D10；DiffRhythm（2025-03）降可选档（用户明确后再装），必装下载量 ~9-10GB→~3GB。→ v1.4。

---

## 8. 收尾交付清单

**REPORT.md（最终报告，R5 交付）字段**：①成品与工程路径（mix.flac/project.json/stems/）；②结构时间戳表（段落→beat→秒+各引擎出场对照功能清单①-⑩）；③QC 摘要（§6.3 全指标实测值）；④资产总账（新增件数/体积/许可证汇总）；⑤CLI 用法速查（bgm 各子命令示例）；⑥试听指引与已知限制（如 demucs 分轨质量记录、可选档未成项原因）。
**REVIEW_LOG.md 记录模板**：轮次/审查员立场/发现（级别+条目）/处置（修订版本号）/证据指针（命令输出或文件）。
**AGENTS.md 追加节内容清单**：新决策条目（BG-D1..9 精简版）；资产指针（$MUSIC_ASSETS_ROOT 布局+assets.json）；入口命令（bgm 用法+测试命令）；产线更新（代码合成产线从 PoC 升级为整合工具链）；遗留风险与可选档未成项。
