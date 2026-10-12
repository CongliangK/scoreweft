"""doctor 配置负例：临时 runtime + monkeypatch，不改真实本机配置。"""

import json
import sys
import pytest

from bgm_gen import doctor
import helpers

pytestmark = pytest.mark.fast


@pytest.fixture
def doctor_runtime(tmp_path, monkeypatch):
    """完整本机式路径配置；仅隔离外部探针，路径检查仍访问临时文件。"""
    binary = tmp_path / "python"
    binary.touch()
    sf2 = tmp_path / "soundfont.sf2"
    sf2.touch()
    rt = {
        "python_system": str(binary), "python_torch": str(binary),
        "assets_root": str(tmp_path), "samples_root": str(tmp_path),
        "tools": {"ffmpeg": str(binary), "fluidsynth_lib": "libfluidsynth.so.3"},
        "sf2": {"FluidR3_GM": str(sf2), "GeneralUser_GS": str(sf2)},
        "demucs": {"python": str(binary), "env": {"HF_HOME": str(tmp_path)}},
        "matchering": {"python": str(binary)},
        "comfyui": {"base_url": "http://127.0.0.1:8188"},
        "diffrhythm": {"installed": False, "note": "可选档"},
    }
    path = tmp_path / "runtime.json"
    monkeypatch.setattr(doctor, "RUNTIME_PATH", str(path))
    monkeypatch.setattr(doctor, "_torch_ok", lambda *a, **kw: (True, "test-version"))
    monkeypatch.setattr(doctor, "_http_ok", lambda *a, **kw: True)
    monkeypatch.setattr(doctor, "_probe_binary_versions", lambda rt: {})
    monkeypatch.setattr(doctor, "_check_fluidsynth_lib", lambda val: (True, val))
    return rt, path


def _write_runtime(path, rt):
    path.write_text(json.dumps(rt, ensure_ascii=False), encoding="utf-8")


def _set_path(rt, key, value):
    keys = key.split(".")
    node = rt
    for part in keys[:-1]:
        node = node[part]
    node[keys[-1]] = value


def _assert_schema(report):
    assert set(report) == {"ok", "items"}
    assert isinstance(report["ok"], bool)
    for it in report["items"]:
        assert set(it) == {"name", "ok", "detail", "optional", "severity"}
        assert isinstance(it["ok"], bool)
        assert it["severity"] in {"error", "warn"}


@pytest.mark.parametrize("key", [
    "python_system", "python_torch", "assets_root", "samples_root",
    "tools.ffmpeg", "tools.fluidsynth_lib",
    "sf2.FluidR3_GM", "sf2.GeneralUser_GS",
    "demucs.python", "matchering.python", "demucs.env.HF_HOME",
])
def test_doctor_placeholder_paths_are_errors(doctor_runtime, key):
    rt, path = doctor_runtime
    _set_path(rt, key, "  <本机路径>  ")
    _write_runtime(path, rt)
    report = doctor.doctor_report()
    _assert_schema(report)
    assert report["ok"] is False
    bad = [it for it in report["items"] if f"占位未替换：{key}" in it["detail"]]
    assert len(bad) == 1
    assert bad[0]["severity"] == "error" and not bad[0]["optional"]
    assert bad[0]["ok"] is False


@pytest.mark.parametrize("dirname", ["legal<dir>", "<legal-dir>", "prefix<dir>suffix"])
def test_doctor_existing_angle_bracket_directory_is_not_placeholder(doctor_runtime, dirname):
    rt, path = doctor_runtime
    directory = path.parent / dirname
    directory.mkdir()
    rt["assets_root"] = str(directory)
    _write_runtime(path, rt)
    report = doctor.doctor_report()
    _assert_schema(report)
    assert report["ok"] is True
    assert not any("占位未替换" in it["detail"] for it in report["items"])


@pytest.mark.parametrize("key", [
    "python_system", "python_torch", "assets_root", "samples_root",
    "tools.ffmpeg", "tools.fluidsynth_lib",
    "sf2.FluidR3_GM", "sf2.GeneralUser_GS",
    "demucs.python", "matchering.python", "demucs.env.HF_HOME",
])
@pytest.mark.parametrize("value", [42, True, 0, False])
def test_doctor_non_string_paths_are_schema_errors(doctor_runtime, key, value):
    rt, path = doctor_runtime
    _set_path(rt, key, value)
    _write_runtime(path, rt)
    report = doctor.doctor_report()
    _assert_schema(report)
    assert report["ok"] is False
    assert report["items"] == [{
        "name": f"runtime.{key}", "ok": False,
        "detail": f"类型错误：{key} 应为字符串路径",
        "optional": False, "severity": "error",
    }]


def test_doctor_partial_gpu_placeholders_never_false_green(doctor_runtime):
    """基础项及在线服务全绿时，GPU 子键仍必须阻断 ok/exit。"""
    rt, path = doctor_runtime
    keys = ("demucs.python", "matchering.python", "demucs.env.HF_HOME")
    for key in keys:
        _set_path(rt, key, "<独立环境路径>")
    _write_runtime(path, rt)
    report = doctor.doctor_report()
    assert report["ok"] is False
    for key in keys:
        assert any(it["severity"] == "error" and f"占位未替换：{key}" in it["detail"]
                   for it in report["items"])
    assert doctor.main(["--json"]) == 1


@pytest.mark.parametrize("engine", ["demucs", "matchering"])
def test_doctor_missing_interpreter_is_error(doctor_runtime, engine):
    rt, path = doctor_runtime
    rt[engine]["python"] = str(path.parent / "missing-python")
    _write_runtime(path, rt)
    report = doctor.doctor_report()
    assert report["ok"] is False
    bad = [it for it in report["items"] if "解释器路径不存在" in it["detail"]]
    assert len(bad) == 1
    assert bad[0]["name"] == f"runtime.{engine}.python"
    assert bad[0]["severity"] == "error"


@pytest.mark.parametrize("target", ["missing-directory", "python"])
def test_doctor_missing_hf_home_is_only_warn(doctor_runtime, target):
    rt, path = doctor_runtime
    rt["demucs"]["env"]["HF_HOME"] = str(path.parent / target)
    _write_runtime(path, rt)
    report = doctor.doctor_report()
    assert report["ok"] is True
    bad = [it for it in report["items"] if "HF_HOME 目录不存在" in it["detail"]]
    assert len(bad) == 1
    assert bad[0]["severity"] == "warn" and bad[0]["ok"] is False


@pytest.mark.parametrize("text", ["{bad", "null", "[]", "42", '"text"', "true"])
def test_doctor_invalid_runtime_single_error(tmp_path, monkeypatch, capsys, text):
    path = tmp_path / "runtime.json"
    path.write_text(text, encoding="utf-8")
    monkeypatch.setattr(doctor, "RUNTIME_PATH", str(path))
    report = doctor.doctor_report()
    _assert_schema(report)
    assert report["ok"] is False and len(report["items"]) == 1
    it = report["items"][0]
    assert it["name"] == "runtime.json" and it["severity"] == "error"
    assert it["ok"] is False and it["optional"] is False
    assert "runtime.json 解析失败：" in it["detail"]
    assert "重新自仓库根 runtime.json.example 复制" in it["detail"]
    assert doctor.main(["--json"]) == 1
    output = capsys.readouterr()
    assert json.loads(output.out) == report and not output.err
    assert doctor.main([]) == 1
    output = capsys.readouterr()
    assert "runtime.json 解析失败：" in output.out and not output.err
    assert "Traceback" not in output.out


@pytest.mark.parametrize("text", ["{bad", "null"])
@pytest.mark.parametrize("entry", ["script", "bgm"])
def test_doctor_invalid_runtime_cli_no_traceback(tmp_path, text, entry):
    path = tmp_path / "runtime.json"
    path.write_text(text, encoding="utf-8")
    # 子进程只注入 runtime 常量，再走真实 main；不改文件/CLI 契约。
    code = ("from bgm_gen import doctor; "
            f"doctor.RUNTIME_PATH={str(path)!r}; ")
    if entry == "script":
        code += "raise SystemExit(doctor.main(['--json']))"
    else:
        code += "from bgm_gen.cli import main; raise SystemExit(main(['doctor']))"
    result = helpers.run([sys.executable, "-c", code], timeout=30)
    assert result.returncode == 1
    assert not result.stderr and "Traceback" not in result.stdout
    report = json.loads(result.stdout)
    _assert_schema(report)
    assert report["ok"] is False and len(report["items"]) == 1
    assert "runtime.json 解析失败：" in report["items"][0]["detail"]


def _cli_code(path, entry):
    # repr 使用 ASCII 转义，使严格 ASCII 的 Python -c 参数也可安全解析。
    code = f"from bgm_gen import doctor; doctor.RUNTIME_PATH={ascii(str(path))}; "
    if entry == "bgm":
        return code + "from bgm_gen.cli import main; raise SystemExit(main(['doctor']))"
    args = ["--json"] if entry == "json" else []
    return code + f"raise SystemExit(doctor.main({args!r}))"


@pytest.mark.parametrize("entry", ["json", "bgm"])
@pytest.mark.parametrize("scenario", ["legal-directory", "integer-python"])
def test_doctor_path_cli_no_traceback(doctor_runtime, entry, scenario):
    rt, path = doctor_runtime
    if scenario == "legal-directory":
        directory = path.parent / "legal<dir>"
        directory.mkdir()
        rt["assets_root"] = str(directory)
    else:
        rt["demucs"]["python"] = 42
    _write_runtime(path, rt)
    result = helpers.run([sys.executable, "-c", _cli_code(path, entry)], timeout=30)
    assert result.returncode == 1  # 临时 python 文件不是可执行解释器，或类型错误。
    assert result.stdout and not result.stderr
    assert "Traceback" not in result.stdout
    report = json.loads(result.stdout)
    _assert_schema(report)
    if scenario == "legal-directory":
        assert not any("占位未替换" in it["detail"] for it in report["items"])
        assert next(it for it in report["items"] if it["name"] == "assets_root")["ok"]
    else:
        assert report["items"][0]["detail"] == "类型错误：demucs.python 应为字符串路径"


@pytest.mark.parametrize("entry", ["pretty", "json", "bgm"])
@pytest.mark.parametrize("text", ["{bad", "null"])
def test_doctor_strict_ascii_locale_no_traceback(tmp_path, entry, text):
    # 非 BMP 文件名也不得经 backslashreplace 变成无效 JSON 的 \\UXXXXXXXX。
    path = tmp_path / "坏配置\U0001f3b5.json"
    path.write_text(text, encoding="utf-8")
    result = helpers.run([sys.executable, "-c", _cli_code(path, entry)], timeout=30,
                         env_extra={"LC_ALL": "C", "PYTHONUTF8": "0",
                                    "PYTHONCOERCECLOCALE": "0"})
    assert result.returncode == 1
    assert result.stdout and not result.stderr
    assert "Traceback" not in result.stdout
    if entry != "pretty":
        report = json.loads(result.stdout)
        _assert_schema(report)
        assert report["ok"] is False and len(report["items"]) == 1
        assert "runtime.json 解析失败：" in report["items"][0]["detail"]
    else:
        assert "runtime.json 解析失败：" in result.stdout


def test_doctor_valid_local_style_runtime_has_no_new_items(doctor_runtime):
    rt, path = doctor_runtime
    # 文本记录不是运行时路径；模板风格备注不应误报。
    rt.update({"note": "<本机备注>", "generated": "<日期>",
               "gpu": {"serial_guard": "<说明>"}})
    _write_runtime(path, rt)
    report = doctor.doctor_report()
    _assert_schema(report)
    assert report["ok"] is True
    legacy_names = ["tools.ffmpeg", "tools.fluidsynth_lib", "sf2.FluidR3_GM",
                    "sf2.GeneralUser_GS", "assets_root", "samples_root",
                    "python_system.numpy", "python_torch.torch", "comfyui", "diffrhythm"]
    for engine in doctor.ENGINE_NAMES:
        legacy_names += [f"descriptor.{engine}", f"descriptor.{engine}.binary_pin"]
    assert [it["name"] for it in report["items"]] == legacy_names
    assert doctor.main(["--json"]) == 0


def test_doctor_missing_runtime_keeps_copy_guidance(tmp_path, monkeypatch):
    monkeypatch.setattr(doctor, "RUNTIME_PATH", str(tmp_path / "missing.json"))
    report = doctor.doctor_report()
    _assert_schema(report)
    assert report["ok"] is False and len(report["items"]) == 1
    assert "缺 bgm_gen/runtime.json" in report["items"][0]["detail"]
    assert "runtime.json.example" in report["items"][0]["detail"]
