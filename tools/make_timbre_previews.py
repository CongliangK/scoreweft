#!/usr/bin/env python3
"""make_timbre_previews —— 逐音色库生成"典型音色串烧"MP3 预览。

产物：catalog/preview/<slug>.mp3（每库一件）+ INDEX.md（时间码索引表，脚本再生成）。

设计要点：
- 预览声与产线同源：一律经 bgm_gen 真实引擎渲染（synth/sf2/sfz/sample），
  听到的=用工程引用该音色时实际得到的声音（同引擎同渲染路径）。
- 每库内按"乐器 → 固定乐句"排列：旋律件=C 大调七音短句（mf，~2.5s），
  持续/铺底件=柱式和弦，打击件=节奏型——库间可直接横向对比。
- 逐段峰值归一化（-6 dBFS）：VSCO2 电平缺陷族（-54~-77dB）等库间响度差
  会被抹平，听感公平；代价=原始电平特征丢失，电平补偿请查 catalog/timbres.md。
- 确定性：引擎逐位确定；ffmpeg 解码/编码（f32le / libmp3lame 160k）同版本确定
  ——整脚本可重跑再生成（中间件落 out/preview_build/，gitignored）。

用法（标准 argparse，--help 查看全部参数与前置说明）：
    python3 tools/make_timbre_previews.py                # 全量再生（先打印计划摘要）
    python3 tools/make_timbre_previews.py --only synth   # 只再生指定预览件（slug 见 PREVIEWS 键）
    python3 tools/make_timbre_previews.py --dry-run      # 只列出将再生的件与段数，不写盘

并发：BUILD/输出目录均使用 .make_timbre_previews.lock；存在即拒绝启动，
不支持并发。正常结束或 Ctrl-C 自动释放；崩溃残留锁须确认无生成进程后手动删除。

**向后兼容**：无参数调用 = 全量再生，行为与旧版一致；启动时先打印执行
计划摘要（件数/段数/目标/量级）再干活，误触发可感知。
"""

import argparse
import os
import subprocess
import sys
import wave
import tempfile
import re
from contextlib import contextmanager, ExitStack

import numpy as np


def _configure_streams():
    # ASCII locale 下中文可转义，避免提示本身导致崩溃（Python 3.7+）。
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError, OSError):
            pass


@contextmanager
def _atomic_path(target):
    """同目录临时件；成功后原子替换，中断/失败保留旧件并清理临时件。"""
    target = os.path.abspath(target)
    fd, temporary = tempfile.mkstemp(prefix=".scoreweft-", suffix=os.path.splitext(target)[1],
                                     dir=os.path.dirname(target))
    try:
        os.close(fd)
        yield temporary
        os.replace(temporary, target)
    finally:
        # temporary 来自 mkstemp 的已知绝对路径，不删除最终产物。
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def _directory_lock(directory, name):
    """不支持并发；保守拒绝既有锁（包括崩溃残留锁），不自动回收。"""
    path = os.path.join(os.path.abspath(directory), name)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise RuntimeError(f"目标目录已锁定，不支持并发：{path}；"
                           "请等待另一进程结束；若为残留锁，确认无生成进程后手动删除该锁。") from None
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(f"pid={os.getpid()}\n")
        yield
    finally:
        os.unlink(path)


_configure_streams()

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from bgm_gen.engines import run_engine                     # noqa: E402

SR = 44100
OUT_DIR = os.path.join(REPO, "catalog", "preview")
BUILD_DIR = os.path.join(REPO, "out", "preview_build")
from bgm_gen.paths import assets_root, local_runtime, samples_root  # noqa: E402

ATTRIBUTIONS = {
    "synth": "自产 synthlib 程序化渲染；MIT，Copyright (c) 2026 Scoreweft contributors。",
    "sf2_fluidr3": "FluidR3 by Frank Wen (MIT) — https://www.fluidsynth.org/soundfonts/；完整版权与许可声明见 [NOTICE](<../../NOTICE.md>)。",
    "sf2_generaluser": "GeneralUser GS by S. Christian Collins (GeneralUser GS License v2.0) — https://schristiancollins.com/generaluser.php；音乐使用许可与源样本边界见 [NOTICE](<../../NOTICE.md>)。",
    "sfz_vsco2_ce": "VSCO 2 CE / Versilian Studios 及贡献者 (CC0) — https://github.com/sgossner/VSCO-2-CE/tree/SFZ；无强制署名。",
    "sfz_karoryfer": "Karoryfer bigcat cello / Meatbass / War Tuba (CC0) — https://www.karoryfer.com/karoryfer-samples；无强制署名。",
    "sfz_salamander": "钢琴音源：Salamander Grand Piano V3 by Alexander Holm (CC-BY 3.0) — https://archive.org/details/SalamanderGrandPianoV3；SFZ 化 kinwie；许可 https://creativecommons.org/licenses/by/3.0/ 。",
    "sfz_vpo": "弦乐音源：Virtual Playing Orchestra by Paul Battersby — https://virtualplaying.com；音乐自由使用，采样来源分层许可详见 [NOTICE](<../../NOTICE.md>)。",
    "sample_kenney": "Kenney (CC0) — https://kenney.nl/assets；无强制署名。",
}

PREVIEW_NOTICE = "> 这些预览由固定乐句渲染/触发，经归一化、截断、淡入淡出、拼接与 MP3 编码（改动说明）；第三方权利与署名详见 [NOTICE](<../../NOTICE.md>)。Mixkit/Sonniss 裸采样预览未随开源版发布，可在核验条款后本地自建。"

# ---- 乐句素材（beats @120bpm，beat=0.5s） --------------------------------
MEL = [[60, 0.0, 0.45, 100], [64, 0.5, 0.45, 100], [67, 1.0, 0.45, 100],
       [72, 1.5, 0.45, 100], [67, 2.0, 0.45, 100], [64, 2.5, 0.45, 100],
       [60, 3.0, 1.8, 100]]
MEL_DYN = [[p, b, d, v] for (p, b, d, _), v
           in zip(MEL, (62, 74, 86, 98, 110, 100, 88))]
CHORD = [[48 + i, 0.06 * i, 4.0, 92] for i in (0, 7, 12, 16, 19)]  # 微错位=模拟合奏起音


def tr(notes, semis):
    return [[p + semis, b, d, v] for p, b, d, v in notes]


def _ffmpeg(args, *, data=None):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error"] + args,
                       capture_output=True, input=data)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg 失败：{' '.join(args[:6])}…\n{r.stderr.decode('utf-8', errors='replace')[:400]}")
    return r.stdout


def render_snippet(name, engine, payload):
    """引擎渲染一段 → 立体声 float64 数组。"""
    spec = {"engine": engine, "spec_version": "1", "sr": SR,
            "out": os.path.join(BUILD_DIR, f"{name}.wav"), "payload": payload}
    rt = _load_runtime()
    rt["assets_root"] = assets_root(rt)
    rt["samples_root"] = samples_root(rt)
    # 任何成功解析出的 sf2 根（env > runtime > 仓库 assets/ fallback）都注入默认
    # GeneralUser 映射——纯 fallback 场景 resolve_sf2 不再报"未知 sf2 名字"。
    generaluser = os.path.join(rt["assets_root"], "sf2", "GeneralUser_GS.sf2")
    if os.path.isfile(generaluser):
        rt["sf2"] = dict(rt.get("sf2") or {})
        rt["sf2"]["GeneralUser_GS"] = generaluser
    with _atomic_path(spec["out"]) as temporary:
        run_engine(dict(spec, out=temporary), runtime=rt)
    raw = _ffmpeg(["-i", spec["out"], "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"])
    x = np.frombuffer(raw, dtype="<f4").astype(np.float64).reshape(-1, 2)
    return x


def decode_hit(path, at, gain_db=0.0):
    """sample 引擎用的 hit 描述（文件须存在，调用方先校验）。"""
    return {"file": path, "at": at, "gain_db": gain_db}


def snippet(x, peak=0.5, cap_s=5.0, fade_ms=15):
    """归一化 + 截断 + 淡入淡出 + 0.4s 间隔静音。"""
    n_cap = int(cap_s * SR)
    if len(x) > n_cap:
        x = x[:n_cap]
    m = np.abs(x).max()
    if m > 1e-9:
        x = x / m * peak
    n_f = int(SR * fade_ms / 1000)
    if n_f and len(x) > 2 * n_f:
        env = np.ones(len(x))
        env[:n_f] = np.linspace(0, 1, n_f)
        env[-n_f:] = np.linspace(1, 0, n_f)
        x = x * env[:, None]
    return np.vstack([x, np.zeros((int(0.4 * SR), 2))])


def sfz_notes(sfz, notes, bpm=120):
    return {"sfz": sfz, "notes": notes, "bpm": bpm}


def sf2_notes(sf2, program, notes, bpm=120):
    return {"sf2": sf2, "bank": 0, "program": program, "notes": notes, "bpm": bpm}


def synth_notes(program, notes, bpm=120):
    return {"program": program, "notes": notes, "bpm": bpm}


def mel_entry(label, engine, payload):
    return (label, engine, payload)


def first_files(directory, suffix, count):
    fs = sorted(f for f in os.listdir(directory) if f.endswith(suffix))
    return [os.path.join(directory, f) for f in fs[:count]]


# ---- Kenney 盘点（环境变量或既有 runtime.json；缺件跳过） ----------------
def _load_runtime():
    rt = local_runtime()
    if not isinstance(rt, dict):
        raise ValueError("runtime.json 须为 JSON 对象，不能是 null 或数组")
    return rt


def build_previews():
    sample_root = samples_root(_load_runtime())
    kenney_root = os.path.join(sample_root, "_raw", "kenney")
    previews = []  # (slug, 标题, [entry…])；entry=(label, engine, payload)

    # ① synth（synthlib 六音色全览）
    previews.append(("synth", "synth · 程序化合成器（synthlib 六音色）", [
        ("kick · 底鼓（四分律动）", "synth", synth_notes("kick",
            [[36, 0, 0.25, 127], [36, 1, 0.25, 100], [36, 2, 0.25, 127], [36, 3, 0.25, 100]])),
        ("snare · 军鼓（2/4 反拍）", "synth", synth_notes("snare",
            [[38, 0, 0.25, 110], [38, 2, 0.25, 110]])),
        ("hat · 踩镲（八分）", "synth", synth_notes("hat",
            [[42, i * 0.5, 0.2, 90] for i in range(8)])),
        ("fm_ep · FM 电钢（旋律）", "synth", synth_notes("fm_ep", MEL)),
        ("bass · 合成贝斯（旋律）", "synth", synth_notes("bass", tr(MEL, -24))),
        ("lead · 合成主音（旋律）", "synth", synth_notes("lead", MEL)),
    ]))

    # ②③ 两个 GM 库：同 12 program 同乐句 → 直接 A/B
    gm_progs = [(0, "Acoustic Grand 声学大钢琴", "dyn"), (4, "Rhodes 电钢", "mel"),
                (11, "Vibraphone 颤音琴", "mel"), (16, "Drawbar Organ 拉杆风琴", "mel"),
                (24, "Nylon Guitar 尼龙吉他", "mel"), (33, "Finger E.Bass 电贝斯", "bass"),
                (40, "Violin 小提琴", "mel"), (48, "Strings Ensemble 弦乐合奏", "chord"),
                (56, "Trumpet 小号", "mel"), (65, "Alto Sax 中音萨克斯", "mel"),
                (73, "Flute 长笛", "mel"), (88, "Warm Pad 暖铺底", "chord")]
    for sf2_name, title in (("FluidR3_GM", "sf2 · FluidR3_GM（系统 GM 128 音色）"),
                            ("GeneralUser_GS", "sf2 · GeneralUser GS（assets GM 128 音色）")):
        entries = []
        for prog, label, mode in gm_progs:
            if mode == "bass":
                notes = tr(MEL, -24)
            elif mode == "chord":
                notes = CHORD
            elif mode == "dyn":
                notes = MEL_DYN
            else:
                notes = MEL
            entries.append((f"p{prog:03d} {label}", "sf2", sf2_notes(sf2_name, prog, notes)))
        previews.append((f"sf2_{sf2_name.split('_')[0].lower()}", title, entries))

    # ④ VSCO2 CE 管弦
    v = "VSCO2/"
    previews.append(("sfz_vsco2_ce", "sfz · VSCO2 CE 社区版管弦（CC0）", [
        ("独奏小提琴 SViolinVib（力度弧）", "sfz", sfz_notes(v + "SViolinVib.sfz", MEL_DYN)),
        ("小提琴组 ViolinEnsSusVib（和弦）", "sfz", sfz_notes(v + "ViolinEnsSusVib.sfz", CHORD)),
        ("中提琴组 ViolaEnsSusVib（和弦）", "sfz", sfz_notes(v + "ViolaEnsSusVib.sfz", CHORD)),
        ("大提琴组 CelloEnsSusVib（和弦）", "sfz", sfz_notes(v + "CelloEnsSusVib.sfz", CHORD)),
        ("低音提琴 ContrabassSusVB（旋律）", "sfz", sfz_notes(v + "ContrabassSusVB.sfz", tr(MEL, -24))),
        ("长笛 FluteSusVib", "sfz", sfz_notes(v + "FluteSusVib.sfz", MEL)),
        ("双簧管 OboeSusVib", "sfz", sfz_notes(v + "OboeSusVib.sfz", MEL)),
        ("单簧管 ClarinetSus", "sfz", sfz_notes(v + "ClarinetSus.sfz", MEL)),
        ("大管 BassoonSus", "sfz", sfz_notes(v + "BassoonSus.sfz", tr(MEL, -12))),
        ("圆号 FHornSus", "sfz", sfz_notes(v + "FHornSus.sfz", MEL)),
        ("竖琴 Harp", "sfz", sfz_notes(v + "Harp.sfz", MEL)),
        ("立式钢琴 UprightPiano（力度弧）", "sfz", sfz_notes(v + "UprightPiano.sfz", MEL_DYN)),
        ("定音鼓滚奏 TimpaniRolls", "sfz", sfz_notes(v + "TimpaniRolls.sfz", [[36, 0, 4, 110]])),
        ("钟琴 Glockenspiel（库内电平极低，已归一化）", "sfz",
         sfz_notes(v + "Glockenspiel.sfz", tr(MEL, 12))),
    ]))

    # ⑤ karoryfer 三件套（大提琴×大贝斯×战争大号）
    k = "karoryfer/"
    bc = k + "bigcat_cello/Karoryfer_Bigcat_cello/Programs/"
    mb = k + "meatbass/Meatbass/Programs/"
    wt = k + "war_tuba/War_tuba/Programs/"
    previews.append(("sfz_karoryfer", "sfz · Karoryfer 三件套（CC0：大提琴/大贝斯/战争大号）", [
        ("bigcat 大提琴 · 弓奏力度层", "sfz", sfz_notes(bc + "01- Bowed (velocity layer).sfz", MEL_DYN)),
        ("bigcat 大提琴 · 拨奏", "sfz", sfz_notes(bc + "03- Plucked.sfz", MEL)),
        ("meatbass 大贝斯 · 弓奏三层力度", "sfz", sfz_notes(mb + "02_arco_3vel.sfz", tr(MEL, -24))),
        ("meatbass 大贝斯 · 拨奏", "sfz", sfz_notes(mb + "04_pizz.sfz", tr(MEL, -24))),
        ("war_tuba · 独奏复音", "sfz", sfz_notes(wt + "2-solo-poly.sfz", tr(MEL, -24))),
        ("war_tuba · 双人复音（和弦）", "sfz", sfz_notes(wt + "4-duo-poly.sfz", tr(CHORD, -24))),
    ]))

    # ⑥ SalamanderGrand 大钢琴
    previews.append(("sfz_salamander", "sfz · SalamanderGrand V3 大钢琴（CC-BY）", [
        ("旋律（pp→f 力度弧，vel 62-110）", "sfz",
         sfz_notes("SalamanderGrand/Salamander Grand Piano V3.sfz", MEL_DYN)),
        ("柱式和弦强奏", "sfz",
         sfz_notes("SalamanderGrand/Salamander Grand Piano V3.sfz", CHORD)),
    ]))

    # ⑦ VPO 弦乐五声部
    vp = "VPO/Strings/"
    previews.append(("sfz_vpo", "sfz · VPO 虚拟演奏管弦弦乐（分层许可，SEC-sustain）", [
        ("第一小提琴 1st-violin", "sfz", sfz_notes(vp + "1st-violin-SEC-sustain.sfz", MEL)),
        ("第二小提琴 2nd-violin", "sfz", sfz_notes(vp + "2nd-violin-SEC-sustain.sfz", MEL)),
        ("中提琴 viola", "sfz", sfz_notes(vp + "viola-SEC-sustain.sfz", MEL)),
        ("大提琴 cello", "sfz", sfz_notes(vp + "cello-SEC-sustain.sfz", tr(MEL, -12))),
        ("低音提琴 bass", "sfz", sfz_notes(vp + "bass-SEC-sustain.sfz", tr(MEL, -24))),
        ("全弦乐齐奏 all-strings（和弦收束）", "sfz",
         sfz_notes(vp + "all-strings-SEC-sustain.sfz", CHORD)),
    ]))

    # ⑧ Kenney 采样包（每包 3 发）
    entries = []
    if os.path.isdir(kenney_root):
        for pack in sorted(d for d in os.listdir(kenney_root)
                           if d.startswith("kenney_") and os.path.isdir(os.path.join(kenney_root, d))):
            audio = os.path.join(kenney_root, pack, "Audio")
            if not os.path.isdir(audio):          # 少数包无 Audio/ 子目录（如 voiceover-pack）
                audio = os.path.join(kenney_root, pack)
            files = first_files(audio, ".ogg", 3)
            if files:
                rel = [os.path.relpath(f, sample_root) for f in files]
                hits = [decode_hit(r, 0.8 * i, -6) for i, r in enumerate(rel)]
                entries.append((f"{pack[len('kenney_'):]}（3 发代表件）", "sample",
                                {"hits": hits, "length_s": 0.8 * len(files) + 1.2}))
    if entries:
        previews.append(("sample_kenney", "sample · Kenney 全 10 包（CC0，one-shot）", entries))

    # Mixkit/Sonniss GDC：开源版不含裸采样预览，可本地自建；
    # 获取、生成和发布前须自行核验源库条款，禁止将受限采样作为工具素材再分发。

    return previews


def mmss(t):
    return f"{int(t // 60):02d}:{t % 60:04.1f}"


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


def _parse_args(argv=None):
    p = _ZhArgumentParser(
        prog="python3 tools/make_timbre_previews.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "逐音色库再生「典型音色串烧」试听 MP3：catalog/preview/<slug>.mp3（每库一件）\n"
            "+ INDEX.md（时间码索引表，同步再生成）。\n"
            "\n"
            "预览声一律经 bgm_gen 真实引擎渲染（synth/sf2/sfz/sample），与产线同源、\n"
            "可确定性重跑再生成。\n"
            "\n"
            "无参数 = 全量再生（与旧版行为一致）；启动时先打印执行计划摘要\n"
            "（件数/段数/目标/量级）再干活。"
        ),
        epilog=(
            "前置：assets/ 音色库（符号链接真身）与 runtime.json 已就位、ffmpeg 可用\n"
            "（缺件的段落逐段跳过并在索引披露；一件都没有再生成功则中文报错 exit 1，\n"
            "INDEX.md 保持不动）。中间件落 out/preview_build/（gitignored）。"
        ),
    )
    p.add_argument("--only", metavar="SLUG", default=None,
                   help="只再生指定预览件（slug 如 synth / sf2_fluidr3 / sfz_vpo / sample_kenney；"
                        "可用值随本机资产自动增减，传错将列出可用值并以 exit 2 退出）")
    p.add_argument("--dry-run", action="store_true",
                   help="只列出将再生的预览件与段数；不渲染、不写盘、不改 INDEX.md")
    return p.parse_args(argv)


def main(argv=None):
    if argv and argv[0].endswith(".py"):     # 兼容旧式 main(sys.argv) 传参
        argv = argv[1:]
    args = _parse_args(argv)

    previews = build_previews()
    slugs = [slug for slug, _title, _entries in previews]
    if args.only is not None and args.only not in slugs:
        print(f"错误：--only {args.only} 不是有效预览件。", file=sys.stderr)
        print(f"可用值（{len(slugs)} 个）：{'、'.join(slugs)}", file=sys.stderr)
        return 2
    todo = [pv for pv in previews if args.only is None or pv[0] == args.only]
    n_segs = sum(len(entries) for _slug, _title, entries in todo)
    scope = (f"--only {args.only}（其余件不动）" if args.only is not None
             else "全量（同时重写 INDEX.md）")
    print(f"[计划] 将再生 {len(todo)} 件预览 MP3、共 {n_segs} 段引擎渲染，模式：{scope}",
          file=sys.stderr)
    print(f"[计划] 输出目录 {OUT_DIR}；预计几十秒量级（本机实测 8 件 67 段约 23 秒，视库与机器而定）",
          file=sys.stderr)
    if args.dry_run:
        for slug, title, entries in todo:
            print(f"[dry-run] {slug}.mp3 <- {title}（{len(entries)} 段）")
        print(f"[dry-run] 共 {len(todo)} 件 / {n_segs} 段；未渲染、未写任何文件")
        return 0

    os.makedirs(BUILD_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    with ExitStack() as stack:
        for directory in sorted({os.path.abspath(BUILD_DIR), os.path.abspath(OUT_DIR)}):
            stack.enter_context(_directory_lock(directory, ".make_timbre_previews.lock"))
        return _generate(todo, args.only)


def _merge_index(existing, selected, slug):
    """精确识别二级库 section 与唯一文件行；只替换选中的完整 section。"""
    parts = re.split(r"(?m)(?=^## )", existing)
    if not parts[0].startswith("# catalog/preview") or len(parts) < 2:
        raise ValueError("索引标题或库 section 缺失")
    seen = set()
    for i in range(1, len(parts)):
        matches = re.findall(r"(?m)^\*\*文件\*\*：`([^`]+)\.mp3`", parts[i])
        if len(matches) != 1 or matches[0] in seen:
            raise ValueError("库 section 的文件标识缺失或重复")
        seen.add(matches[0])
        if matches[0] == slug:
            parts[i] = selected
    if slug not in seen:
        if not parts[-1].endswith("\n"):
            parts.append("\n")
        parts.append(selected)
    return "".join(parts)


def _generate(todo, only):
    index_rows = ["# catalog/preview —— 音色库试听预览索引", "",
                  "> 由 `tools/make_timbre_previews.py` 生成（引擎真实渲染，重跑确定性再生）。",
                  "> **逐段峰值归一化（-6 dBFS）**：库间原始电平差异已被抹平（如 VSCO2 电平缺陷族），",
                  "> 电平补偿请查 [../timbres.md](../timbres.md)。每行=一个乐器，时间码可直接拖动播放。",
                  PREVIEW_NOTICE, ""]

    n_ok = 0
    for slug, title, entries in todo:
        chunks, rows, t = [], [], 0.0
        for i, (label, engine, payload) in enumerate(entries):
            try:
                x = render_snippet(f"{slug}_{i:02d}", engine, payload)
            except Exception as e:  # 缺件/引擎拒载：跳过并在索引披露
                # 失败详情可能含本地工具/素材的绝对路径，仅留在本地控制台。
                rows.append(f"| 跳过 | {label} | 渲染失败（{type(e).__name__}），详见本地日志 |")
                print(f"[skip] {slug} · {label}: {str(e)[:120]}")
                continue
            s = snippet(x)
            chunks.append(s)
            rows.append(f"| {mmss(t)} | {label} | {engine} |")
            t += len(s) / SR
        if not chunks:
            print(f"[warn] {slug} 无可用段落，跳过")
            continue
        mix = np.vstack(chunks)
        pcm = (np.clip(mix, -1, 1) * 32767).astype("<i2")
        wav_p = os.path.join(BUILD_DIR, f"{slug}_master.wav")
        with _atomic_path(wav_p) as temporary:
            with wave.open(temporary, "wb") as w:
                w.setnchannels(2), w.setsampwidth(2), w.setframerate(SR)
                w.writeframes(pcm.tobytes())
        mp3_p = os.path.join(OUT_DIR, f"{slug}.mp3")
        with _atomic_path(mp3_p) as temporary:
            _ffmpeg(["-i", wav_p, "-codec:a", "libmp3lame", "-b:a", "160k", "-y", temporary])
        index_rows += [f"## {title}", "", f"**文件**：`{slug}.mp3` · 时长 {mmss(t)} · {len(chunks)} 段", "",
                       "**来源与义务**：" + ATTRIBUTIONS[slug], "",
                       "| 起 | 乐器/段落 | 引擎 |", "|---|---|---|"] + rows + [""]
        n_ok += 1
        print(f"[ok] {slug}.mp3  {mmss(t)}  {len(chunks)} 段")

    if n_ok == 0:
        print("错误：没有任何预览再生成功（音色资产或引擎不可用），INDEX.md 未改动。",
              file=sys.stderr)
        print("请先运行 bgm doctor 核对 assets/ 符号链接、runtime.json 与 ffmpeg/引擎后端。",
              file=sys.stderr)
        return 1
    index_path = os.path.join(OUT_DIR, "INDEX.md")
    text = "\n".join(index_rows) + "\n"
    if only is not None:
        try:
            with open(index_path, encoding="utf-8") as f:
                existing = f.read()
            selected = text[text.index("## "):]
            text = _merge_index(existing, selected, only)
        except (OSError, ValueError) as e:
            print(f"警告：既有 INDEX.md 缺失、不可读或结构不符（{e}）；"
                  "回退为仅写选中件索引，无法保留其他库段落。", file=sys.stderr)
    with _atomic_path(index_path) as temporary:
        with open(temporary, "w", encoding="utf-8") as f:
            f.write(text)
    print("索引 → catalog/preview/INDEX.md")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n已中止（用户中断）；临时文件已清理，既有产物未被截断。", file=sys.stderr)
        sys.exit(130)
    except Exception as e:  # 绝不裸 traceback：稳定中文提示 + exit 1
        print(f"错误：{type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
