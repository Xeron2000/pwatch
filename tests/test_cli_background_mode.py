from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pwatch.app import cli


class _FakeProcess:
    def __init__(self, pid=4321, poll_result=None):
        self.pid = pid
        self._poll_result = poll_result

    def poll(self):
        return self._poll_result


class _FakeCompletedProcess:
    def __init__(self, stdout=""):
        self.stdout = stdout


def test_main_defaults_to_background_start(monkeypatch):
    called = []

    monkeypatch.setattr(cli.argparse.ArgumentParser, "parse_args", lambda self: SimpleNamespace(command=None))
    monkeypatch.setattr(cli, "cmd_start", lambda args: called.append("start"))
    monkeypatch.setattr(cli, "cmd_run", lambda args: called.append("run"))

    cli.main()

    assert called == ["start"]


def test_get_pid_and_log_paths_live_in_config_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("pwatch.paths.get_config_dir", lambda: tmp_path)

    from pwatch.paths import get_log_path, get_pid_path

    assert get_pid_path() == tmp_path / "pwatch.pid"
    assert get_log_path() == tmp_path / "pwatch.log"


def test_cmd_start_launches_background_process_and_writes_pid(monkeypatch, tmp_path, capsys):
    pid_path = tmp_path / "pwatch.pid"
    log_path = tmp_path / "pwatch.log"

    monkeypatch.setattr(cli, "_get_running_pid", lambda: None)
    monkeypatch.setattr(cli, "_run_start_preflight", lambda: None)
    monkeypatch.setattr(cli, "_get_python_executable", lambda: "/usr/bin/python3")
    monkeypatch.setattr(cli, "_get_runner_module", lambda: "pwatch.app.runner")
    monkeypatch.setattr("pwatch.app.cli.get_pid_path", lambda: pid_path)
    monkeypatch.setattr("pwatch.app.cli.get_log_path", lambda: log_path)
    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: _FakeProcess(pid=4321, poll_result=None))

    cli.cmd_start(SimpleNamespace())

    assert pid_path.read_text(encoding="utf-8").splitlines()[0] == "4321"
    out = capsys.readouterr().out
    assert "started in background" in out.lower()
    assert str(log_path) in out


def test_cmd_start_reports_existing_process(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_get_running_pid", lambda: 9999)

    cli.cmd_start(SimpleNamespace())

    out = capsys.readouterr().out
    assert "already running" in out.lower()
    assert "9999" in out


def test_cmd_status_reports_running_process(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_get_running_pid", lambda: 5555)
    monkeypatch.setattr("pwatch.app.cli.get_log_path", lambda: Path("/tmp/pwatch.log"))

    cli.cmd_status(SimpleNamespace())

    out = capsys.readouterr().out
    assert "running" in out.lower()
    assert "5555" in out
    assert "/tmp/pwatch.log" in out


def test_cmd_stop_terminates_running_process_and_removes_pid(monkeypatch, tmp_path, capsys):
    pid_path = tmp_path / "pwatch.pid"
    pid_path.write_text("7777", encoding="utf-8")
    killed = []

    monkeypatch.setattr(cli, "_get_running_pid", lambda: 7777)
    monkeypatch.setattr("pwatch.app.cli.get_pid_path", lambda: pid_path)
    monkeypatch.setattr("os.kill", lambda pid, sig: killed.append((pid, sig)))

    cli.cmd_stop(SimpleNamespace())

    assert killed and killed[0][0] == 7777
    assert not pid_path.exists()
    assert "stopped" in capsys.readouterr().out.lower()


def test_cmd_logs_prints_log_contents(monkeypatch, tmp_path, capsys):
    log_path = tmp_path / "pwatch.log"
    log_path.write_text("line1\nline2\n", encoding="utf-8")
    monkeypatch.setattr("pwatch.app.cli.get_log_path", lambda: log_path)

    cli.cmd_logs(SimpleNamespace())

    out = capsys.readouterr().out
    assert "line1" in out
    assert "line2" in out


def test_cmd_start_runs_preflight_before_spawning(monkeypatch, tmp_path):
    pid_path = tmp_path / "pwatch.pid"
    log_path = tmp_path / "pwatch.log"
    calls = []

    monkeypatch.setattr(cli, "_get_running_pid", lambda: None)
    monkeypatch.setattr(cli, "_run_start_preflight", lambda: calls.append("preflight"))
    monkeypatch.setattr(cli, "_get_python_executable", lambda: "/usr/bin/python3")
    monkeypatch.setattr(cli, "_get_runner_module", lambda: "pwatch.app.runner")
    monkeypatch.setattr("pwatch.app.cli.get_pid_path", lambda: pid_path)
    monkeypatch.setattr("pwatch.app.cli.get_log_path", lambda: log_path)
    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: _FakeProcess(pid=4321, poll_result=None))

    cli.cmd_start(SimpleNamespace())

    assert calls == ["preflight"]


def test_get_running_pid_ignores_stale_pid_for_wrong_process(monkeypatch, tmp_path):
    pid_path = tmp_path / "pwatch.pid"
    pid_path.write_text("9999\npwatch.app.runner\n", encoding="utf-8")

    monkeypatch.setattr("pwatch.app.cli.get_pid_path", lambda: pid_path)
    monkeypatch.setattr(cli, "_pid_is_running", lambda pid: True)
    monkeypatch.setattr(cli, "_pid_matches_runner", lambda pid: False)

    assert cli._get_running_pid() is None
    assert not pid_path.exists()


def test_runner_uses_file_logging_without_console_duplication():
    import inspect
    import pwatch.app.runner as runner

    source = inspect.getsource(runner.main)
    assert "setup_logging(log_level, console=False)" in source
    assert "setup_logging(console=False)" in source
