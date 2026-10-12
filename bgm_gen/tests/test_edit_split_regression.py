"""split 回归锁：changed 外部轨条目 after 必须 str（json.dumps TypeError bug）。

背景（2026-10-11 修复，总控 decode 改动）：edit_split 曾把 _read_bytes 的
bytes 原样塞进 changed[].after，CLI 层 json.dumps(result) 抛
"Object of type bytes is not JSON serializable"；修复=decode("utf-8")。
本文件锁三层：
① changed 外部轨条目 after 为 str（非 bytes）且整个 result 可 json.dumps；
② 生成的外部轨文件可 json.load；
③ edit_merge 后主文件 tracks 内联 notes 与拆分前逐位一致。

fixture 沿 test_edit.py split/merge 用例写法（minimal → v2 副本落
helpers.tmpdir，一律 tmp 目录执行，红线④正本不动）。
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import helpers                                              # noqa: E402

helpers.in_proc_env()
from bgm_gen.core.edit import edit_merge, edit_split        # noqa: E402

MINIMAL = os.path.join(helpers.EXAMPLES_DIR, "minimal.json")


def _copy_v2(d, name="proj.json"):
    """examples/minimal.json → tmp 副本并升 spec_version="2"（split 双布局；
    与 test_edit.py 的 _copy_project(version="2") 同口径）。"""
    with open(MINIMAL, encoding="utf-8") as f:
        proj = json.load(f)
    proj["meta"]["spec_version"] = "2"
    path = os.path.join(d, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(proj, f, ensure_ascii=False)
    return path


@pytest.mark.fast
def test_split_after_str_external_json_and_merge_roundtrip():
    d = helpers.tmpdir("edit_split_reg")
    path = _copy_v2(d)
    with open(path, encoding="utf-8") as f:
        before = json.load(f)
    before_notes = {t["name"]: t["notes"] for t in before["tracks"]}
    assert before_notes, "minimal 前置：至少一轨带 notes"

    r = edit_split(path)

    # ① 外部轨条目（path 形如 tracks/<slug>.json；主文件 diff 条目为
    # tracks[i] 风格、不含 .json 后缀）——after 必须 str 非 bytes
    ext = [c for c in r["changed"] if c["path"].endswith(".json")]
    assert len(ext) == len(before["tracks"]), "每轨一个外部轨条目"
    for c in ext:
        assert c["before"] is None
        assert isinstance(c["after"], str), (
            f"after 必须是 str（bytes 会致 CLI 层 json.dumps TypeError："
            f"bug 回归）：{c['path']}")
        assert not isinstance(c["after"], bytes)
        # after 本身即外部轨文件的 JSON 文本
        json.loads(c["after"])
    # 整个 result 可序列化（CLI --json 出口锁）
    json.loads(json.dumps(r, ensure_ascii=False))

    # ② 生成的外部轨文件可 json.load，且 notes 与拆分前一致
    for c in ext:
        with open(os.path.join(d, c["path"]), encoding="utf-8") as f:
            track = json.load(f)
        assert track["notes"] == before_notes[track["name"]], c["path"]

    # ③ merge 后主文件 tracks 内联 notes 与拆分前逐位一致
    rm = edit_merge(path)
    assert rm["verb"] == "merge"
    with open(path, encoding="utf-8") as f:
        after = json.load(f)
    assert all("$ref" not in t for t in after["tracks"]), "merge 内联展开"
    assert {t["name"]: t["notes"] for t in after["tracks"]} == before_notes, \
        "split→merge 往返后内联 notes 不变"
