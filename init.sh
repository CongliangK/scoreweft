#!/usr/bin/env bash
# Scoreweft 初始化脚本
# 用途：新环境（新机 / 新 clone）快速就绪——基础依赖自检 + 大模型能力开启指引。
# 约定：runtime.json 的唯一写入者是 `bgm doctor`（BG-D3），本脚本不代写、不改动任何配置。
# 大模型策略：ComfyUI AI 引擎（ACE-Step/Music3）与 demucs 等 GPU 能力**默认关闭**——
#             本脚本不启动、不配置它们；确定性引擎（synth/sf2/sfz/sample/master-loudnorm）
#             只需系统 python3 + numpy + ffmpeg/sox/libfluidsynth，自检通过即可用。
set -uo pipefail
cd "$(dirname "$0")"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "  ${GREEN}[OK]${NC} $1"; }
miss() { echo -e "  ${RED}[缺失]${NC} $1"; FAIL=1; }
opt()  { echo -e "  ${YELLOW}[可选]${NC} $1"; }

echo "=== Scoreweft init ==="
FAIL=0

echo "--- 1/5 Python 与核心库（确定性引擎的硬底座）---"
if command -v python3 >/dev/null 2>&1; then
  ok "python3 $(python3 --version 2>&1 | awk '{print $2}')"
  python3 -c "import numpy" 2>/dev/null && ok "numpy $(python3 -c "import numpy;print(numpy.__version__)" 2>/dev/null)" \
    || miss "numpy（pip/conda 安装后重跑）"
else
  miss python3
fi

echo "--- 2/5 系统依赖 ---"
command -v ffmpeg >/dev/null 2>&1 && ok "ffmpeg（master 引擎 loudnorm）" || miss ffmpeg
command -v sox     >/dev/null 2>&1 && ok "sox" || opt "sox 未装——部分音频处理不可用"
python3 -c "import ctypes; ctypes.CDLL('libfluidsynth.so.3')" 2>/dev/null \
  && ok "libfluidsynth（sf2 引擎，ctypes 零安装）" || opt "libfluidsynth 未装——sf2 引擎不可用"

echo "--- 3/5 外部资产根（大资产永不入库，BG-D2；仅探测提示）---"
ASSETS_ROOT="$(python3 -c 'from bgm_gen.paths import assets_root; print(assets_root())' 2>/dev/null || echo "${MUSIC_ASSETS_ROOT:-$PWD/assets}")"
[ -d "$ASSETS_ROOT" ] && ok "资产根存在（MUSIC_ASSETS_ROOT / runtime.json / assets）" \
  || opt "资产根不存在——请设置 MUSIC_ASSETS_ROOT 或配置 runtime.json，其余引擎不受影响"

echo "--- 4/5 大模型能力（默认关闭）---"
if curl -s --max-time 2 http://127.0.0.1:8188 >/dev/null 2>&1; then
  opt "ComfyUI 8188 当前可达——但按默认策略仍视为关闭，未做任何配置"
else
  echo "  ComfyUI 未运行（默认状态）。开启 AI 引擎的完整步骤："
  echo "    1) 按 ComfyUI 官方安装说明启动本地服务 # 权重清单见 workflows/README.md"
  echo "    2) bgm doctor                          # 探测环境并写 runtime.json（其唯一写入者）"
  echo "    3) bgm engines                         # 确认 ai/demucs 引擎状态"
fi

echo "--- 5/5 结果与验证建议 ---"
if [ "$FAIL" -eq 0 ]; then
  echo -e "${GREEN}基础依赖齐备。${NC}验证安装：python3 -m pytest bgm_gen/tests -q（fast 档，无 GPU 也可跑）"
  echo "最小试 render：bgm render examples/minimal.json -o out/try_init"
else
  echo -e "${RED}有基础依赖缺失（见上），补齐后重跑 init.sh。${NC}"
fi
exit $FAIL
