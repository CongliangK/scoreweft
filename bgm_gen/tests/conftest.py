"""R4 测试引导（PLAN.md §5 R4 / §0 DoD3）：

- sys.path 注入工作区根（可 import bgm_gen）；
- cwd 固定到工作区根（引擎/QC 的相对路径口径与正式用法一致）；
- marker 三档 fast/slow/service：默认只跑 fast（slow/service 记为 deselected），
  `-m slow` / `-m service` / `-m "fast or slow"` 显式选择。

用法（cwd 必须是工作区根，即 bgm_gen 的父目录）：
    python3 -m pytest bgm_gen/tests -q                        # fast 档（默认）
    python3 -m pytest bgm_gen/tests -q -m slow
    python3 -m pytest bgm_gen/tests -q -m service
    python3 -m pytest bgm_gen/tests -q -m "fast or slow or service"   # 全量三档
    # 注意：-m "" 经下方判空落入"默认只收 fast"分支（fast-only），不是全量。
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_WORKSPACE = os.path.dirname(os.path.dirname(_HERE))

if _WORKSPACE not in sys.path:
    sys.path.insert(0, _WORKSPACE)
os.chdir(_WORKSPACE)          # cwd 固定（进程级一次）

# v3 R1 前置：测试临时目录按进程隔离（helpers.tmpdir 读此 env），
# 并发 worker/审查者各自跑 pytest 时不共享 /tmp/r4smoke 子目录。
os.environ.setdefault("BGM_TMP_ROOT", f"/tmp/r4smoke_{os.getpid()}")


def _purge_stale_tmp_roots(age_s=86400):
    """清理 >24h 的 r4smoke_* 残目录（tmpfs 容量保护——R2 审查 E1：临时目录
    从不清理曾致 /tmp 80% 满、ENOSPC flake）。仅动陈旧的 pid 后缀目录。"""
    import glob
    import shutil
    import time
    now = time.time()
    for p in glob.glob("/tmp/r4smoke_*"):
        try:
            if os.path.isdir(p) and now - os.path.getmtime(p) > age_s:
                shutil.rmtree(p, ignore_errors=True)
        except OSError:
            pass


_purge_stale_tmp_roots()

# v3 R1-W2 增量渲染硬闸（PLAN_v3 §3.3）：测试默认强制全量渲染（缺省行为
# 逐位一致）；增量专项用例经 helpers.run(env_extra={"BGM_NO_INCREMENTAL": "0"})
# 子进程覆写，绝不改进程内 env。
os.environ.setdefault("BGM_NO_INCREMENTAL", "1")

# v3.4 并行渲染（BGM_NO_PARALLEL）：**刻意不注入**——默认启用并行走新路径，
# 由 test_parallel.py 锁定"并行≡顺序（BGM_NO_PARALLEL=1）位级一致"与既有
# test_cli sha 锚点；顺序路径专项用例经 monkeypatch.setenv/delenv 进程内
# 覆写或 helpers.run(env_extra=...) 子进程覆写（镜像 BGM_NO_INCREMENTAL 模式）。

import pytest                                                 # noqa: E402


def pytest_configure(config):
    config.addinivalue_line("markers", "fast: 确定性引擎+资产+CLI+QC+旧脚本回归（默认档，<10min）")
    config.addinivalue_line("markers", "slow: GPU 引擎冒烟（demucs/master；可分批跑）")
    config.addinivalue_line("markers", "service: ComfyUI 8188 依赖项（不可达→显式 skip 计数）")


def pytest_collection_modifyitems(config, items):
    """收集期纪律：①未打 fast/slow/service 三档 marker 的用例直接 fail
    （PLAN_v3 §6 ①）；②无 -m 时默认只收 fast 档（slow/service 记 deselected）。"""
    unmarked = [it.nodeid for it in items
                if not (it.get_closest_marker("fast")
                        or it.get_closest_marker("slow")
                        or it.get_closest_marker("service"))]
    if unmarked:
        pytest.fail("收集期纪律（PLAN_v3 §6 ①）：以下测试未打 fast/slow/service "
                    "三档 marker，请补 @pytest.mark.fast|slow|service：\n  "
                    + "\n  ".join(unmarked))
    expr = (config.getoption("-m") or "").strip()
    if expr:
        return
    keep, dropped = [], []
    for item in items:
        if "slow" in item.keywords or "service" in item.keywords:
            dropped.append(item)
        else:
            keep.append(item)
    if dropped:
        config.hook.pytest_deselected(items=dropped)
        items[:] = keep


@pytest.fixture(scope="session")
def py3():
    from helpers import py3 as _py3
    return _py3()
