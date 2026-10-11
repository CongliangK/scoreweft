"""可移植资产根：环境变量 > 既有 runtime.json > 仓库 assets/。

只读取本地配置，不改写 runtime.json；发布编目中的 $ROOT 标记不是运行时路径。
"""

import json
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def local_runtime():
    path = os.path.join(REPO_ROOT, "bgm_gen", "runtime.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def assets_root(runtime=None):
    rt = local_runtime() if runtime is None else runtime
    value = os.environ.get("MUSIC_ASSETS_ROOT") or rt.get("assets_root")
    return os.path.abspath(os.path.expanduser(value or os.path.join(REPO_ROOT, "assets")))


def samples_root(runtime=None):
    rt = local_runtime() if runtime is None else runtime
    value = os.environ.get("MUSIC_SAMPLES_ROOT") or rt.get("samples_root")
    return os.path.abspath(os.path.expanduser(value or os.path.join(assets_root(rt), "samples")))
