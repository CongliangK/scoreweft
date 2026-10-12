# 贡献指南

## 环境与测试

从克隆仓库根运行。安装 `python3 -m pip install -r requirements.txt`，再执行 `bash init.sh` 自检。原验证机 `python3` 指 miniconda base；其它机器先确认该解释器能 import numpy/pytest，不要盲用缺依赖的系统 Python。外部音色/CLI 与本地运行配置需自行准备，安装与配置见 [README](<README.md>)；项目案例及其旧锚点为私有材料，不随仓发布。

```bash
python3 -m pytest bgm_gen/tests -q             # fast（默认），预算 ≤90s
python3 -m pytest bgm_gen/tests -q -m slow     # GPU/外部工具较慢冒烟
python3 -m pytest bgm_gen/tests -q -m service  # ComfyUI 本地服务
```

服务不可达、已迁走项目缺件的显式 skip 必须计数披露，不能静默算通过。默认 fast 仍需要本地资产、ffmpeg/FluidSynth/sfizz 与运行配置，不是无资产 CI。`-m ""` 不表示全量；全量用 `-m "fast or slow or service"`。

**fresh clone 首跑前置（顺序固定）**：冒烟 spec 与 demucs/master 输入、minimal 位级锚点均 gitignored，先 ①`python3 tools/make_smoke_specs.py`（重建 8 份基线 spec + 两件输入 wav，缺资产时逐条给出补齐指引）→ ②`python3 -m bgm_gen render examples/minimal.json -o out/minimal` → ③pytest。详情见 [测试手册](<bgm_gen/tests/README.md>)「fresh clone 首跑前置」。

## 确定性与接口纪律

- 位级复现承诺仅在 Linux + 钉版本环境成立（FFmpeg 8.1.2 / FluidSynth 2.5.4）；实测支持环境及 Windows 不支持的原因见 [README「支持环境」](<README.md#支持环境>)。确定性引擎同 spec/固定工具版本逐位复现；并行必须与顺序逐位相等；GPU 容差与非确定性引擎按自身分级验收，不承诺 seed 即位级相等。
- BG-D5：spec 声明的 sr/channels 权威，stem 强制归一；避免改变无新字段工程的旧字节路径。不要修改基线、降低断言或补 skip 来掩盖回归。
- envelope + payload 为引擎契约，参数/事件能力来自描述符；升级需 pin、行为探针、doctor 与描述符 diff 一致。插件五步法见 [引擎开发契约](<bgm_gen/engines/README.md>)。
- 修改音色编目后重新 `python3 -m bgm_gen catalog --write`；发布副本路径占位化、实时扫描仍用本地真实路径，同步测试除路径占位和日期外精确比较全部数据。
- 运行根通过 MUSIC_ASSETS_ROOT / MUSIC_SAMPLES_ROOT 或既有本地配置解析；绝不把用户路径、代理地址、凭据或内部取证材料写进发布文件。下载如需代理自行设置 HTTPS_PROXY。
- 不破坏 ComfyUI 环境；可选 demucs/matchering 等放独立环境。旧脚本 argv/cwd 契约冻结，不删除既有音频产物。

## 产线纪律与内容贡献

任何编曲前先完成乐器清单、逐件音色实现、单音与真实乐句试听、客观量具读数及用户拍板，记录 TIMBRE.md；换库/换参/升级重新过门。操作模板与许可、反复核查、QC 纪律见 [PLAYBOOK_BGM §〇](<docs/PLAYBOOK_BGM.md>) 和 [AGENTS](<AGENTS.md>)。只投产经核验的可商用源，CC-BY 发布附作者/源 URL/许可/改动；CC-BY-SA 挂起项与 NC 禁入项不可偷渡。

提交贡献前披露变更、三档实际测试与 skip、确定性证据、第三方来源与许可；新增预览须同步 [NOTICE](<NOTICE.md>) 和 [预览索引](<catalog/preview/INDEX.md>)。本仓原创贡献按 [MIT](<LICENSE>) 接收，第三方素材仍各按自己的条款。
