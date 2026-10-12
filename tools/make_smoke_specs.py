#!/usr/bin/env python3
"""make_smoke_specs —— 一条命令重建测试冒烟前置件（fresh clone 首跑卡点）。

背景：`bgm_gen/tests/baselines_w2a.json` 的 8 条确定性引擎基线按指针读取
`out/smoke/{synth,sf2,sfz,sample,master}/spec_*.json`，slow 档还需
`out/smoke/demucs/demucs_in10s.wav`——这些件 gitignored 不随 clone 分发，
且此前无文档化再生成途径（out/RUNTHROUGH_2026-10-11.md 卡点②）。本工具
把 8 份 spec 以**模板形式内置**（内容=开发树规范件原样），并确定性生成
demucs 分轨输入与 master 正弦输入两个 wav。跑完本工具 → 渲染 minimal
锚点 → pytest（顺序见 bgm_gen/tests/README.md「fresh clone 首跑前置」）。

产物（默认 `<仓库根>/out/smoke/`，--out 可覆盖；测试只消费默认位置的件）：

    synth/spec_synth_kick.json  synth/spec_synth_hat.json    纯合成，无外部资产
    sf2/spec_sf2_fluidr3.json   sf2/spec_sf2_gugs.json       sf2 名 → runtime.json 解析
    sfz/spec_sfz_vsco2.json     sfz/spec_sfz_tuba.json       相对引用 → assets_root/sfz
    sample/spec_sample.json                                  相对采样 → samples_root
    master/spec_master_loudnorm.json + master_in_sine.wav    input 指向生成件
    demucs/demucs_in10s.wav                                   纯 numpy 合成

路径模板方案（研究规范件内容后的可移植性决策）：
- **sfz / sf2 / sample 保持规范件的相对引用原样**——渲染期由引擎按
  runtime.json 解析（resolve_sfz / resolve_sf2 / resolve_sample），spec 内
  不落任何绝对路径，跨 clone 天然可移植；本工具只做**存在性预检**
  （复用引擎自己的 resolve 函数，口径与渲染期完全一致）。
- **master 的 payload.input 引擎按原样使用**（os.path.isfile 直查，无相对
  解析），模板内置 `{SMOKE_DIR}` 占位符，生成时替换为**目标目录的绝对
  路径**——spec 在目标机器上由本工具再生，绝对路径永远指向本机在位的
  master_in_sine.wav（与规范件的历史形态一致，仅消除对开发树个人路径的
  硬编码）。
- 各 spec 的 `out` 字段保持仓库相对路径（测试会覆盖到临时目录重渲；
  裸跑渲染时由引擎 default_out 的仓库根约定兜底）。

wav 生成方式（逐位确定，公式即注释）：

- `master_in_sine.wav` = 0.25·sin(2π·440·t) + 0.25·sin(2π·660·t)，3.0s
  单声道 44100Hz PCM16（(clip(x,-1,1)·32767).astype(int16) 截断量化）——
  与开发树规范件**逐字节一致**（sha256 e675cd6b…da81），钉版本 ffmpeg 下
  baselines_w2a 的 master 位级输出锚点因此保持有效。
- `demucs_in10s.wav`：历史件 = legacy gm_lofi_demo.wav 截前 10.03s
  （baselines_w2b note 实录，纯器乐、vocals stem 等效静音）。本工具改用
  `bgm_gen.synthlib` 纯 numpy 合成 10.0s 立体声器乐小样（鼓组→drums 路由、
  bass 律动→bass、fm_ep 和弦+lead 旋律→other；无 vocal 内容，与原纯器乐
  口径一致）。slow 档对此输入只断言 stem RMS **下限**（3dB 余量）与 loudnorm
  LUFS 目标，无位级锚点——合成内容电平余量 >15dB，不依赖逐位复刻历史件。

并发：同一 --out 不支持并发；目录 .make_smoke_specs.lock 存在即拒绝启动。
正常结束或 Ctrl-C 自动释放锁；崩溃残留锁须确认无生成进程后手动删除。

退出码：0 = 全部生成成功；1 = 环境缺件（runtime.json 缺失 / 资产不可解析
等——先逐条打印「缺什么 / 在哪 / 怎么办」，**不写任何文件**，补齐后重跑）。

用法：
    python3 tools/make_smoke_specs.py            # 重建到 <仓库根>/out/smoke/
    python3 tools/make_smoke_specs.py --out DIR  # 覆盖目标目录（调试/比对用）
    python3 tools/make_smoke_specs.py --help     # 参数说明
"""

import argparse
import json
import os
import sys
import wave
import tempfile
from contextlib import contextmanager


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

RUNTIME_GUIDANCE = ("复制 runtime.json.example（仓库根）为 bgm_gen/runtime.json → "
                    "手工替换全部 <…> 占位为真实绝对路径 → "
                    "再跑 python3 -m bgm_gen doctor 校验")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import numpy as np                                             # noqa: E402

SR = 44100
DEFAULT_OUT = os.path.join(REPO, "out", "smoke")

# ---------------------------------------------------------------------------
# ① spec 模板（内容 = 开发树 out/smoke 规范件原样；字段顺序亦保持一致，
#    便于与历史件 diff。仅 master 的 payload.input 用占位符，见模块 docstring。
#    不得改动 baselines_w2a.json 的指针与任何基线哈希——模板值与冻结基线
#    （时长/RMS/sha256）配套，动一个参数即破坏基线。）
# ---------------------------------------------------------------------------
KICK_HAT_NOTES_COMMON = [[36, 0.0, 0.9, 100], [48, 1.9, 0.9, 100],
                         [60, 3.8, 0.9, 100], [72, 5.7, 0.9, 100]]

SPEC_TEMPLATES = {
    "synth/spec_synth_kick.json": {
        "engine": "synth", "spec_version": "1", "sr": 44100,
        "out": "out/smoke/synth/engine_kick_bar.wav",
        "payload": {
            "program": "kick", "bpm": 120,
            "notes": [[36, 0, 0.25, 127], [36, 1, 0.25, 110],
                      [36, 2, 0.25, 127], [36, 3, 0.25, 110]],
        },
    },
    "synth/spec_synth_hat.json": {
        "engine": "synth", "spec_version": "1", "sr": 44100,
        "out": "out/smoke/synth/engine_hat_bar.wav",
        "payload": {
            "program": "hat", "bpm": 120,
            "notes": [[42, 0, 0.25, 90], [42, 0.5, 0.25, 60],
                      [42, 1, 0.25, 90], [42, 1.5, 0.25, 60],
                      [42, 2, 0.25, 90], [42, 2.5, 0.25, 60],
                      [42, 3, 0.25, 90], [42, 3.5, 0.25, 60]],
            "params": {"decay": 0.04},
        },
    },
    "sf2/spec_sf2_fluidr3.json": {
        "engine": "sf2", "spec_version": "1", "sr": 44100,
        "out": "out/smoke/sf2/engine_fluidr3_p48.wav",
        "payload": {"sf2": "FluidR3_GM", "bank": 0, "program": 48,
                    "notes": KICK_HAT_NOTES_COMMON, "bpm": 120},
    },
    "sf2/spec_sf2_gugs.json": {
        "engine": "sf2", "spec_version": "1", "sr": 44100,
        "out": "out/smoke/sf2/engine_gugs_p0.wav",
        "payload": {"sf2": "GeneralUser_GS", "bank": 0, "program": 0,
                    "notes": KICK_HAT_NOTES_COMMON, "bpm": 120},
    },
    "sfz/spec_sfz_vsco2.json": {
        "engine": "sfz", "spec_version": "1", "sr": 44100,
        "out": "out/smoke/sfz/engine_vsco2_celloens.wav",
        "payload": {"sfz": "VSCO2/CelloEnsSusVib.sfz",
                    "notes": KICK_HAT_NOTES_COMMON, "bpm": 120},
    },
    "sfz/spec_sfz_tuba.json": {
        "engine": "sfz", "spec_version": "1", "sr": 44100,
        "out": "out/smoke/sfz/engine_war_tuba.wav",
        "payload": {"sfz": "Karoryfer/war_tuba/War_tuba/Programs/1-solo-legato.sfz",
                    "notes": KICK_HAT_NOTES_COMMON, "bpm": 120},
    },
    "sample/spec_sample.json": {
        "engine": "sample", "spec_version": "1", "sr": 44100,
        "out": "out/smoke/sample/engine_kenney_impact.wav",
        "payload": {
            "hits": [
                {"file": "_raw/kenney/kenney_impact-sounds/Audio/"
                         "impactGeneric_light_000.ogg",
                 "at": 0.0, "gain_db": 0},
                {"file": "_raw/kenney/kenney_impact-sounds/Audio/"
                         "impactGeneric_light_000.ogg",
                 "at": 0.5, "gain_db": -3},
                {"file": "_raw/kenney/kenney_impact-sounds/Audio/"
                         "impactGeneric_light_000.ogg",
                 "at": 1.0, "gain_db": -6},
                {"file": "_raw/kenney/kenney_impact-sounds/Audio/"
                         "impactGeneric_light_000.ogg",
                 "at": 1.5, "gain_db": 0},
            ],
            "length_s": 2.5,
        },
    },
    "master/spec_master_loudnorm.json": {
        "engine": "master", "spec_version": "1", "sr": 44100, "channels": 1,
        "out": "out/smoke/master/engine_master_loudnorm.wav",
        "payload": {
            # 占位符：master 引擎对 input 无相对解析（按原样 isfile 直查），
            # 生成时替换为目标目录绝对路径——见模块 docstring 路径方案。
            "input": "{SMOKE_DIR}/master/master_in_sine.wav",
            "mode": "loudnorm", "target_lufs": -14, "true_peak": -1,
        },
    },
}

# ---------------------------------------------------------------------------
# ② 资产预检：复用引擎自己的 resolve 函数（口径=渲染期一致），逐条收集
#    「缺什么 / 在哪 / 怎么办」，全部通过才动笔写文件。
# ---------------------------------------------------------------------------
SAMPLE_REF = ("_raw/kenney/kenney_impact-sounds/Audio/"
              "impactGeneric_light_000.ogg")


def check_assets(rt):
    """返回缺件清单 [(缺什么, 在哪, 怎么办)]；空表 = 环境齐备。"""
    missing = []

    def add(what, where, how):
        missing.append((what, where, how))

    # sf2：名字经 runtime.json 的 sf2 表解析（resolve_sf2 同口径）
    from bgm_gen.engines.sf2 import resolve_sf2
    for name in ("FluidR3_GM", "GeneralUser_GS"):
        try:
            resolve_sf2(name, rt)
        except Exception as e:                                  # noqa: BLE001
            add(f"sf2 音色库「{name}」不可解析（{e}）",
                f"runtime.json 的 sf2 表（当前条目：{rt.get('sf2', {}).get(name, '无')}）",
                "安装对应 .sf2；" + RUNTIME_GUIDANCE)

    # sfz：相对引用经 assets_root/sfz 解析（resolve_sfz 同口径，含目录别名）
    from bgm_gen.engines.sfz import resolve_sfz
    for ref in ("VSCO2/CelloEnsSusVib.sfz",
                "Karoryfer/war_tuba/War_tuba/Programs/1-solo-legato.sfz"):
        try:
            resolve_sfz(ref, rt)
        except Exception as e:                                  # noqa: BLE001
            add(f"sfz 音色「{ref}」未找到（{e}）",
                f"runtime.json 的 assets_root={rt.get('assets_root', '未配置')} "
                "下的 sfz/ 目录（VSCO2_CE / Karoryfer 两库）",
                "按 bgm_gen/assets.json manifest 恢复音色库后重跑"
                "（`python3 -m bgm_gen doctor` 可校验资产一致性）")

    # sample：相对采样经 samples_root 解析（resolve_sample 同口径）
    from bgm_gen.engines.sample import resolve_sample, FALLBACK_SAMPLES_ROOT
    root = rt.get("samples_root") or FALLBACK_SAMPLES_ROOT
    try:
        resolve_sample(SAMPLE_REF, root)
    except Exception as e:                                      # noqa: BLE001
        add(f"one-shot 采样「{SAMPLE_REF}」未找到（{e}）",
            f"runtime.json 的 samples_root={root or '未配置'}"
            "（Kenney impact-sounds 包的 _raw/ 子树）",
            RUNTIME_GUIDANCE + "；samples_root 指向含 Kenney 包的采样根")
    return missing


# ---------------------------------------------------------------------------
# ③ wav 确定性生成
# ---------------------------------------------------------------------------
def _write_wav(path, sig, channels):
    """PCM16 wav：clip → ×32767 → 截断量化（与 helpers.write_wav 同口径）。"""
    a = np.asarray(sig, dtype=np.float64)
    if a.ndim == 1 and channels > 1:
        a = np.repeat(a[:, None], channels, axis=1)
    pcm = (np.clip(a, -1.0, 1.0) * 32767.0).astype("<i2")
    with _atomic_path(path) as temporary:
        with wave.open(temporary, "wb") as w:
            w.setnchannels(channels)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(pcm.tobytes())


def make_master_in_sine(path):
    """3.0s 单声道双音正弦——与开发树规范件逐字节一致（sha256 e675cd6b…）。

    公式：0.25·sin(2π·440·t) + 0.25·sin(2π·660·t)，量化 = ×32767 截断。
    loudnorm 两遍法同版本 ffmpeg 下逐位确定 → master 基线位级锚点保持有效。
    """
    t = np.arange(3 * SR) / SR
    sig = 0.25 * np.sin(2 * np.pi * 440.0 * t) + 0.25 * np.sin(2 * np.pi * 660.0 * t)
    _write_wav(path, sig, channels=1)


def make_demucs_input(path):
    """10.0s 立体声器乐小样（synthlib 纯 numpy，逐位确定）。

    内容与 stem 路由（对齐 baselines_w2b 的下限断言口径）：
      鼓组 kick/snare/hat（120BPM 五小节律动）→ demucs drums stem；
      synthlib.bass 根音律动（Am–F–C–G–Am）      → bass stem；
      fm_ep 柱式和弦 + lead 旋律                  → other stem；
      全程无 vocal 内容（与历史件"纯器乐、vocals 等效静音"口径一致，
      vocals 基线下限为 null 只验存在）。
    电平：峰值归一到 0.5 FS（整体 RMS ≈ -20dB），对 drums/bass/other 三条
    下限（-49.75/-56.69/-42.49dB，各含 3dB 余量）富余 >15dB。
    确定性：synthlib 全部单元种子化（噪声用固定 seed 的 default_rng——
    与 synth 引擎基线同一纪律，同机同库版本逐位一致）。
    """
    from bgm_gen import synthlib as S

    dur, beat = 10.0, 0.5                       # 120BPM，1 小节 = 2s，共 5 小节
    roots = ["A2", "F2", "C3", "G2", "A2"]      # 每小节 bass 根音
    chords = [["A3", "C4", "E4"], ["F3", "A3", "C4"], ["C4", "E4", "G4"],
              ["G3", "B3", "D4"], ["A3", "C4", "E4"]]
    melody = [  # (拍, 音名, 时值拍)：五声音阶短句，跨 3–5 小节
        (0, "E5", 0.9), (1, "G5", 0.9), (1.5, "A5", 0.9), (2, "G5", 1.4),
        (4, "E5", 0.9), (4.5, "D5", 0.9), (5, "C5", 1.4),
        (7, "E5", 0.45), (7.5, "D5", 0.9), (8, "C5", 1.8),
        (10, "A4", 0.9), (10.5, "B4", 0.9), (11, "C5", 1.8),
        (13, "E5", 0.9), (13.5, "D5", 0.9), (14, "B4", 1.9),
    ]

    drums, bass, keys, lead = (S.Track(dur) for _ in range(4))
    for bar in range(5):
        t0 = bar * 2.0
        for b, g in [(0, 1.0), (1.5, 0.7), (2.0, 1.0), (3.5, 0.8)]:
            drums.add(S.kick(), t0 + b * beat, g * 0.9)          # kick
        for b in (1.0, 3.0):
            drums.add(S.snare(), t0 + b * beat, 0.75)            # snare 2/4
        for b in range(8):
            drums.add(S.hat(), t0 + b * beat, 0.45)              # hat 八分
        for b, d in [(0, 0.9), (1.0, 0.45), (2.0, 0.9), (3.0, 0.45), (3.5, 0.45)]:
            bass.add(S.bass(S.hz(roots[bar]), d), t0 + b * beat, 0.6)
        for note in chords[bar]:
            keys.add(S.fm_ep(S.hz(note), 1.7), t0, 0.30)         # 柱式和弦
    for b, note, d in melody:
        lead.add(S.lead(S.hz(note), d), b * beat, 0.4)

    stereo = S.mixdown({"drums": drums.buf, "bass": bass.buf,
                        "keys": keys.buf, "lead": lead.buf})
    stereo = stereo[:int(dur * SR)]                              # 裁到整 10s
    stereo *= 0.5 / np.abs(stereo).max()                         # 峰值归一 0.5FS

    rms = np.sqrt((stereo.astype(np.float64) ** 2).mean())
    assert rms > 10 ** (-60 / 20), "demucs 输入意外静音（合成公式被破坏？）"
    _write_wav(path, stereo, channels=2)


# ---------------------------------------------------------------------------
# ④ 主流程
# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="make_smoke_specs.py",
        description="重建测试冒烟前置件：8 份引擎 spec 模板 + demucs 分轨输入 "
                    "+ master 正弦输入（fresh clone 首跑必经；详见模块 docstring）。",
        epilog="顺序提醒：本工具 → `python3 -m bgm_gen render examples/minimal.json "
               "-o out/minimal`（sha 锚点）→ pytest。缺件时逐条给出补齐指引，"
               "退出码 1。")
    ap.add_argument("--out", default=DEFAULT_OUT, metavar="DIR",
                    help=f"目标目录（默认 {DEFAULT_OUT}；测试只消费默认位置）")
    args = ap.parse_args(argv)
    out_dir = os.path.abspath(args.out)

    # -- 环境预检（先查后写：缺件时不产生任何半成品） -----------------------
    runtime_path = os.path.join(REPO, "bgm_gen", "runtime.json")
    if not os.path.isfile(runtime_path):
        print("[缺件] bgm_gen/runtime.json 不存在（机器环境探测产物，gitignore "
              "不随 clone 分发）")
        print("  在哪：本仓 bgm_gen/runtime.json")
        print("  怎么办：" + RUNTIME_GUIDANCE)
        return 1
    with open(runtime_path, encoding="utf-8") as f:
        rt = json.load(f)
    if not isinstance(rt, dict):
        raise ValueError("runtime.json 须为 JSON 对象，不能是 null 或数组")

    missing = check_assets(rt)
    if missing:
        print(f"环境缺件 {len(missing)} 项（未写任何文件；补齐后重跑本工具）：")
        for i, (what, where, how) in enumerate(missing, 1):
            print(f"  [缺件 {i}/{len(missing)}] {what}")
            print(f"    在哪：{where}")
            print(f"    怎么办：{how}")
        return 1

    # 创建/删除实际临时件探测目录权限；包含既有各子目录，避免半途 PermissionError。
    try:
        directories = {out_dir} | {os.path.join(out_dir, rel.split("/")[0])
                                   for rel in SPEC_TEMPLATES} | {os.path.join(out_dir, "demucs")}
        for directory in sorted(directories):
            os.makedirs(directory, exist_ok=True)
            # TemporaryFile 关闭/中断即清理；Linux 通常使用匿名临时文件。
            with tempfile.TemporaryFile(prefix=".scoreweft-probe-", dir=directory) as probe:
                probe.write(b"permission probe\n")
    except OSError as e:
        print(f"错误：输出目录缺少创建/写入权限：{e}；请修复目录权限或换 --out。",
              file=sys.stderr)
        return 1
    with _directory_lock(out_dir, ".make_smoke_specs.lock"):
        return _generate(out_dir)


def _generate(out_dir):
    # -- 写盘 ---------------------------------------------------------------
    wrote = []
    for rel, tpl in SPEC_TEMPLATES.items():
        spec = _subst_placeholders(tpl, out_dir)                 # 模板只读，直接派生
        dst = os.path.join(out_dir, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with _atomic_path(dst) as temporary:
            with open(temporary, "w", encoding="utf-8") as f:
                json.dump(spec, f, ensure_ascii=False, indent=2)
                f.write("\n")
        wrote.append(dst)

    for rel, fn in (("master/master_in_sine.wav", make_master_in_sine),
                    ("demucs/demucs_in10s.wav", make_demucs_input)):
        dst = os.path.join(out_dir, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        fn(dst)
        wrote.append(dst)

    for p in wrote:
        print(f"[写] {os.path.relpath(p, out_dir)}（{os.path.getsize(p)} B）")
    print(f"完成：{len(SPEC_TEMPLATES)} 份 spec + 2 件 wav → {out_dir}")
    print("下一步：`python3 -m bgm_gen render examples/minimal.json -o out/minimal` "
          "（sha 锚点）→ `python3 -m pytest bgm_gen/tests -q`")
    return 0


def _subst_placeholders(spec, out_dir):
    """递归替换 {SMOKE_DIR} → 目标目录绝对路径（当前仅 master payload.input）。"""
    if isinstance(spec, dict):
        return {k: _subst_placeholders(v, out_dir) for k, v in spec.items()}
    if isinstance(spec, list):
        return [_subst_placeholders(v, out_dir) for v in spec]
    if isinstance(spec, str) and "{SMOKE_DIR}" in spec:
        return spec.replace("{SMOKE_DIR}", out_dir)
    return spec


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n已中止（用户中断）；临时文件已清理，既有产物未被截断。", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"错误：{type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
