"""openscore 双库 .mxl → MIDI 批量转换器（docs/PLAN_musicxml.md §三）。

一次性外部工具（包内只留读器 musicxml_import）；R3 批量转换与
tests/test_musicxml_import.py L3 roundtrip 共用本写出层。

写出规则（PLAN_musicxml §三，三轮审查钉死）：
    - **per-voice 分 channel**：per-file 全局分配器——按 (part 文档序,
      voice 数值序) 枚举 (part,voice) 对，从 ch0 顺取跳过 ch9（GM 打击）；
      对数 >15 raise（全库 max=15 零触发）；同 part 各 channel 写相同
      program（源 midi-program 1-based → MIDI 0-based，解析器已转）。
    - **唯一写出路径=手工 Trk.ev**（tick=round(beat×ppq)）+
      write_smf(ppq=LCM)；禁 Trk.note（PPQ=480 钉死）与 events_to_smf
      （标量 ch 单通道签名）。
    - **ppq=LCM(各 part divisions 值集)**，护栏 100000——超限回退
      384×max_divisions 并披露量化残差。
    - **vel 恒 64**（无表情底稿）；**grace 默认剔除**（批转库=干净符号
      层，n_grace 披露）；cue 解析层已剔除。
    - **残留交叠降级**：同 (voice,pitch) onset<off 冲突 → 冲突音追加
      溢出 channel（找同 pitch 无 span 冲突者）；无余量 → 件级 skip。

用法（标准 argparse，--help 查看全部参数与前置说明）：
    python3 examples/convert_openscore.py                     # 全量批转（两库；先打印计划摘要）
    python3 examples/convert_openscore.py --limit 5           # 只转前 5 件（跨库截取，试跑）
    python3 examples/convert_openscore.py --limit 5 --dry-run # 只列出将处理的文件，不写盘
    python3 examples/convert_openscore.py --out <目录>        # 覆盖 MIDI 输出根目录（默认不变）

**向后兼容**：无参数调用 = 全量批转，行为与旧版一致（既有人脚本依赖面）；
启动时先打印执行计划摘要（件数/目标/量级）再干活，误触发可感知。
"""

import argparse
import json
import os
import sys
from math import gcd

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from bgm_gen.core.musicxml_import import (MusicXmlImportError,   # noqa: E402
                                          import_musicxml)
from bgm_gen.engines.midi_util import Trk, write_smf             # noqa: E402

from bgm_gen.paths import assets_root                         # noqa: E402

def _configure_streams():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError, OSError):
            pass


_configure_streams()


def _score_paths():
    # 参数解析之后才读配置；import 写出层与 --help 均零配置依赖。
    from bgm_gen.paths import local_runtime
    rt = local_runtime()
    if not isinstance(rt, dict):
        raise ValueError("runtime.json 须为 JSON 对象，不能是 null 或数组")
    root = os.path.join(assets_root(rt), "scores")
    libs = {"lieder": os.path.join(root, "openscore-lieder", "scores"),
            "sq": os.path.join(root, "openscore-stringquartets", "scores")}
    return root, libs, os.path.join(root, "openscore-midi")
PPQ_CAP = 100000
VEL = 64


def _voice_sort_key(v):
    """voice 数值序（数字串按 int，非数字串按字典序殿后——确定性）。"""
    return (0, int(v), "") if v.isdigit() else (1, 0, v)


def allocate_channels(parsed):
    """(part 文档序, voice 数值序) 枚举 → ch0 顺取跳 ch9。

    返回 {(part_idx, voice): channel}；对数 >15 抛 ChannelOverflow。
    """
    pairs = []
    for pi, part in enumerate(parsed["parts"]):
        for v in sorted(set(part["note_voices"]), key=_voice_sort_key):
            pairs.append((pi, v))
    free = [c for c in range(16) if c != 9]
    if len(pairs) > len(free):
        raise ChannelOverflow(f"(part,voice) 对数 {len(pairs)} > 15")
    return {p: free[i] for i, p in enumerate(pairs)}


class ChannelOverflow(Exception):
    """(part,voice) 对数超出 15 可用通道（全库零触发，防库漂移）。"""


def pick_ppq(parsed):
    """LCM(各 part divisions 值集)；超护栏回退 384×max（quantized 标记）。"""
    vals = [d for part in parsed["parts"] for d in part["divisions"]] or [480]
    l = 1
    for d in vals:
        l = l * d // gcd(l, d)
    if l > PPQ_CAP:
        return 384 * max(vals), True
    return l, False


class _ChannelGrid:
    """(channel, pitch) → 已占 span 列表；溢出分配探测用。"""

    def __init__(self):
        self.spans = {}

    def fits(self, ch, pitch, on, off):
        for a, b in self.spans.get((ch, pitch), ()):
            if on < b and a < off:
                return False
        return True

    def add(self, ch, pitch, on, off):
        self.spans.setdefault((ch, pitch), []).append((on, off))


def build_tracks(parsed, drop_grace=True):
    """parsed → (Trk 列表, 证据 dict)。Trk.ev 手工填（PLAN_musicxml §三）。

    溢出通道复用制（R2 审查 M2 修订）：冲突音先在已开溢出道里找 fits，
    全不 fits 才开新道——零复用版会把时间上不相邻的冲突各耗一道
    （Bartók Op.7 82 处冲突实测可 12 道收敛，零复用版误跳）。
    """
    chan_map = allocate_channels(parsed)
    ppq, quantized = pick_ppq(parsed)
    grid = _ChannelGrid()
    tracks = []
    n_overlap_moved = 0
    occupied = set(chan_map.values())          # 全文件已占通道（program 语义域）
    overflow_pool = []                         # 已开溢出道（可复用）
    for pi, part in enumerate(parsed["parts"]):
        tr = Trk(ch=0, prog=None)              # ch 由逐事件决定
        if part["program"] is not None:
            for ch in sorted({chan_map[(pi, v)]
                              for v in set(part["note_voices"])}):
                tr.ev.append((0, bytes([0xC0 | ch, part["program"]])))
        for row, voice in zip(part["notes"], part["note_voices"]):
            pitch, beat, dur, _vel = row
            if drop_grace and dur <= 0:
                continue
            on = int(round(beat * ppq))
            off = on + max(1, int(round(dur * ppq)))
            ch = chan_map[(pi, voice)]
            if not grid.fits(ch, int(pitch), on, off):
                moved = False
                for cand in overflow_pool:     # 先复用已开溢出道
                    if grid.fits(cand, int(pitch), on, off):
                        ch = cand
                        moved = True
                        n_overlap_moved += 1
                        break
                if not moved:                  # 开新溢出道
                    for cand in range(16):
                        if cand == 9 or cand in occupied:
                            continue           # 溢出道须全新（防 program 串色）
                        if part["program"] is not None:
                            tr.ev.append((0, bytes([0xC0 | cand,
                                                    part["program"]])))
                        occupied.add(cand)
                        overflow_pool.append(cand)
                        ch = cand
                        moved = True
                        n_overlap_moved += 1
                        break
                if not moved:
                    raise ChannelOverflow(
                        f"part {pi} voice {voice} pitch {pitch} beat {beat}"
                        " 交叠且无溢出通道")
            grid.add(ch, int(pitch), on, off)
            tr.ev.append((on, bytes([0x90 | ch, int(pitch), VEL])))
            tr.ev.append((off, bytes([0x80 | ch, int(pitch), 0])))
        tracks.append(tr)
    ev = {"ppq": ppq, "quantized": quantized, "n_overlap_moved": n_overlap_moved,
          "n_channels": len(occupied)}
    return tracks, ev


def convert_one(src, dst, drop_grace=True):
    """单件转换：.mxl → .mid。返回 (parsed, 证据 dict)。"""
    parsed = import_musicxml(src, log=False)
    tracks, ev = build_tracks(parsed, drop_grace=drop_grace)
    bpm = parsed["meta"]["bpm"] or 120.0
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    write_smf(dst, tracks, bpm=bpm, ppq=ev["ppq"])
    return parsed, ev


_WARN_CLASSES = {                    # 清单警告分类（PLAN_musicxml §三 披露制）
    "backup_clamp": "backup 越界",
    "desync": "失同步",
    "tie_fallback": "非邻接配对",
    "tie_dangling": "悬空",
    "nominal_dev": "名义",
    "dual_tempo": "双 tempo 并存",
    "dyn_trunc": "截断",
}


def _warn_stats(parsed):
    """逐 part warnings → 分类计数（R2 审查 M3：清单可见性）。"""
    stats = {k: 0 for k in _WARN_CLASSES}
    total = 0
    for part in parsed["parts"]:
        for w in part.get("warnings", ()):
            total += 1
            for k, mark in _WARN_CLASSES.items():
                if mark in w:
                    stats[k] += 1
                    break
    stats["total"] = total
    return stats


def _enumerate_libs(libs):
    """两库 .mxl 全量枚举 → {lib: [排序后路径]}（lib 名序 × 路径序，确定性）。

    与批转/试跑/计划摘要共用同一枚举，保证"列出的=将处理的"。
    """
    out = {}
    for lib, root in sorted(libs.items()):
        files = []
        for dirpath, _dirs, fs in os.walk(root):
            for f in fs:
                if f.endswith(".mxl"):
                    files.append(os.path.join(dirpath, f))
        files.sort()
        out[lib] = files
    return out


def batch(limit=None, out_root=None, libs=None, dry_run=False):
    """两库批转 + inventory（R3 产出清单；警告逐类计数披露）。

    limit=跨库取前 N 件（lib 名序 × 路径序）；dry_run=True 只列出不写盘。
    """
    if libs is None or out_root is None:
        _root, default_libs, default_out = _score_paths()
        libs = default_libs if libs is None else libs
        out_root = default_out if out_root is None else out_root
    pairs = [(lib, src) for lib, srcs in _enumerate_libs(libs).items()
             for src in srcs]
    if limit:
        pairs = pairs[:limit]
    inv = []
    for lib, src in pairs:
        root = libs[lib]
        rel = os.path.relpath(src, root)
        dst = os.path.join(out_root, lib, os.path.splitext(rel)[0] + ".mid")
        if dry_run:
            inv.append({"lib": lib, "src": src, "dst": dst, "status": "dry-run"})
            print(f"[dry-run] {lib}/{rel} -> {dst}")
            continue
        rec = {"lib": lib, "src": src, "dst": dst, "status": "ok"}
        try:
            parsed, ev = convert_one(src, dst)
            rec.update({
                "n_parts": parsed["meta"]["n_parts"],
                "n_measures": parsed["meta"]["n_measures"],
                "bpm": parsed["meta"]["bpm"],
                "notes": sum(len(p["notes"]) for p in parsed["parts"]),
                "n_grace_dropped": sum(p["n_grace"] for p in parsed["parts"]),
                "n_cue_dropped": sum(p["n_cue"] for p in parsed["parts"]),
                "ppq": ev["ppq"], "quantized": ev["quantized"],
                "n_overlap_moved": ev["n_overlap_moved"],
                "n_channels": ev["n_channels"],
                "has_repeat": parsed["meta"]["has_repeat"],
                "has_ending": parsed["meta"]["has_ending"],
                "warn": _warn_stats(parsed),
            })
        except (MusicXmlImportError, ChannelOverflow) as e:
            rec["status"] = "skip"
            rec["error"] = str(e)
        inv.append(rec)
        print(f"[{rec['status']}] {rel}", file=sys.stderr)
    return inv


class _ZhArgumentParser(argparse.ArgumentParser):
    """参数错误 → 稳定中文提示 + exit 2（不裸 traceback）。"""

    def error(self, message):
        zh = (message
              .replace("unrecognized arguments: ", "存在无法识别的参数：")
              .replace("expected one argument", "该参数后面需要一个值")
              .replace("argument ", "参数 "))
        self.print_usage(sys.stderr)
        print(f"错误：{zh}", file=sys.stderr)
        print("用法详见 --help。", file=sys.stderr)
        sys.exit(2)


def _positive_int(s):
    try:
        v = int(s)
    except ValueError:
        raise argparse.ArgumentTypeError(f"须为正整数，收到 {s!r}")
    if v < 1:
        raise argparse.ArgumentTypeError(f"须为 ≥1 的正整数，收到 {v}")
    return v


def _parse_args(argv=None):
    p = _ZhArgumentParser(
        prog="python3 examples/convert_openscore.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "openscore 双库 .mxl → MIDI 批量转换器（读器 bgm_gen/core/musicxml_import.py，\n"
            "写出层契约见 docs/PLAN_musicxml.md §三）。\n"
            "\n"
            "无参数 = 全量批转（两库全部 .mxl，历史实测 1584 件约 2 分钟），\n"
            "行为与旧版一致；启动时先打印执行计划摘要（件数/目标/量级）再干活。"
        ),
        epilog=(
            "前置：$MUSIC_ASSETS_ROOT/scores/ 下须有 openscore-lieder/ 与\n"
            "openscore-stringquartets/ 两库（缺库将中文报错并以 exit 1 退出，不执行转换）；\n"
            "产物 MIDI 落 --out（默认 scores/openscore-midi/），逐件清单落\n"
            "out/openscore_midi_inventory.json（--dry-run 不写任何文件）。"
        ),
    )
    p.add_argument("--limit", type=_positive_int, metavar="N",
                   help="只批转前 N 件（跨库按库名序×路径序截取，试跑用；默认全量）")
    p.add_argument("--dry-run", action="store_true",
                   help="只列出将处理的文件与目标 MIDI 路径；不解析、不写盘、不写清单")
    p.add_argument("--out", metavar="DIR", default=None,
                   help="覆盖 MIDI 输出根目录（默认资产根下 scores/openscore-midi/）")
    return p.parse_args(argv)


def main(argv=None):
    if argv and argv[0].endswith(".py"):     # 兼容旧式 main(sys.argv) 传参
        argv = argv[1:]
    args = _parse_args(argv)
    scores_root, libs, default_out = _score_paths()
    args.out = args.out if args.out is not None else default_out

    missing = [f"{lib} -> {root}" for lib, root in sorted(libs.items())
               if not os.path.isdir(root)]
    if missing:
        print("错误：openscore 乐谱库目录缺失，未执行任何转换：", file=sys.stderr)
        for m in missing:
            print(f"  {m}", file=sys.stderr)
        print("请核对 $MUSIC_ASSETS_ROOT/scores/ 布局（可运行 bgm doctor 体检）。",
              file=sys.stderr)
        return 1
    enumerated = _enumerate_libs(libs)
    total = sum(len(fs) for fs in enumerated.values())
    if total == 0:
        print(f"错误：两库目录存在但未发现任何 .mxl 文件（{scores_root}），未执行转换。",
              file=sys.stderr)
        return 1
    n_sel = min(args.limit, total) if args.limit else total
    lib_desc = " + ".join(f"{lib} {len(enumerated[lib])} 件"
                          for lib in sorted(enumerated))
    mode = f"（--limit {args.limit} 试跑）" if args.limit else ""
    if args.dry_run:
        mode += "（--dry-run 只列不写）"
    scale = ("秒级" if n_sel <= 10 else
             "约 2 分钟量级（历史实测 1584 件）" if n_sel == total else "分钟级以内")
    print(f"[计划] 将批转 {n_sel}/{total} 件 .mxl（{lib_desc}）{mode}", file=sys.stderr)
    print(f"[计划] MIDI 输出 -> {args.out}"
          + ("" if args.dry_run else f"；预计{scale}，Ctrl-C 可中止"),
          file=sys.stderr)

    if args.dry_run:
        inv = batch(limit=args.limit, out_root=args.out, libs=libs, dry_run=True)
        print(f"[dry-run] 共列出 {len(inv)} 件，未写任何文件")
        return 0

    inv = batch(limit=args.limit, out_root=args.out, libs=libs)
    out_dir = os.path.join(_ROOT, "out")
    os.makedirs(out_dir, exist_ok=True)
    out_json = os.path.join(out_dir, "openscore_midi_inventory.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(inv, f, ensure_ascii=False, indent=1)
    ok = sum(1 for r in inv if r["status"] == "ok")
    skip = sum(1 for r in inv if r["status"] != "ok")
    print(f"converted {ok} / skipped {skip} / total {len(inv)}")
    print(f"inventory: {out_json}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n已中止（用户中断）；已写出的件不受影响。", file=sys.stderr)
        sys.exit(130)
    except Exception as e:  # 绝不裸 traceback：稳定中文提示 + exit 1
        print(f"错误：{type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
