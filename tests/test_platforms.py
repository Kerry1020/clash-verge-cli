from pathlib import Path

from clash_verge_cli import platforms


def test_detect_platform():
    assert platforms.detect_platform("darwin") == "macos"
    assert platforms.detect_platform("win32") == "windows"
    assert platforms.detect_platform("cygwin") == "windows"
    assert platforms.detect_platform("linux") == "linux"


def test_macos_candidates(tmp_path):
    c = platforms.candidate_config_dirs("darwin", {}, tmp_path)
    assert c[0] == tmp_path / "Library" / "Application Support" / platforms.APP_ID


def test_windows_candidates_use_appdata(tmp_path):
    env = {"APPDATA": str(tmp_path / "Roaming"), "LOCALAPPDATA": str(tmp_path / "Local")}
    c = platforms.candidate_config_dirs("win32", env, tmp_path)
    assert c[0] == tmp_path / "Roaming" / platforms.APP_ID
    assert tmp_path / "Roaming" / "clash-verge-rev" in c
    assert tmp_path / "Local" / "clash-verge-rev" in c


def test_windows_missing_appdata_is_not_relative(tmp_path):
    # Old code produced Path('') / 'clash-verge-rev' == relative path in CWD.
    c = platforms.candidate_config_dirs("win32", {}, tmp_path)
    assert all(p.is_absolute() or str(p).startswith("C:") for p in c)
    assert c[0] == tmp_path / "AppData" / "Roaming" / platforms.APP_ID


def test_linux_candidates_respect_xdg(tmp_path):
    env = {"XDG_DATA_HOME": str(tmp_path / "data")}
    c = platforms.candidate_config_dirs("linux", env, tmp_path)
    assert c[0] == tmp_path / "data" / platforms.APP_ID


def test_resolve_order(tmp_path):
    env = {"CLASH_VERGE_DIR": str(tmp_path / "env")}
    assert platforms.resolve_config_dir("/explicit", "linux", env, tmp_path) == Path("/explicit")
    assert platforms.resolve_config_dir(None, "linux", env, tmp_path) == tmp_path / "env"


def test_resolve_prefers_existing_candidate(tmp_path):
    env = {"APPDATA": str(tmp_path / "Roaming")}
    legacy = tmp_path / "Roaming" / "clash-verge-rev"
    legacy.mkdir(parents=True)
    assert platforms.resolve_config_dir(None, "win32", env, tmp_path) == legacy


def test_resolve_falls_back_to_default(tmp_path):
    assert platforms.resolve_config_dir(None, "linux", {}, tmp_path) == (
        tmp_path / ".local" / "share" / platforms.APP_ID
    )
