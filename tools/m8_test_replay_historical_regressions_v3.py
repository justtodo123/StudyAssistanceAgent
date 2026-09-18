#!/usr/bin/env python3
"""Hermetic self-test for the M8 v3 historical regression replay."""
from __future__ import annotations

import ast
import importlib.util
import json
import time
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).with_name("m8_replay_historical_regressions_v3.py")
TOOLS = SCRIPT.parent
if os.fspath(TOOLS) not in sys.path:
    sys.path.insert(0, os.fspath(TOOLS))
SPEC = importlib.util.spec_from_file_location("m8_replay_historical_regressions_v3", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
replay = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(replay)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_env(pycache_root: Path | None = None) -> dict[str, str]:
    blocked = {
        "BASH_ENV",
        "CDPATH",
        "ENV",
        "HOME",
        "IFS",
        "LD_AUDIT",
        "LD_LIBRARY_PATH",
        "LD_PRELOAD",
        "LOCALAPPDATA",
        "PYTHONHOME",
        "PYTHONPATH",
        "SHELLOPTS",
        "XDG_CONFIG_HOME",
    }
    env = {
        name: value
        for name, value in os.environ.items()
        if name.upper() not in blocked
        and not name.upper().startswith(("DYLD_", "GIT_"))
    }
    env.update(
        {
            "GIT_AUTHOR_DATE": "2001-02-03T04:05:06+0000",
            "GIT_AUTHOR_EMAIL": "m8-test@example.invalid",
            "GIT_AUTHOR_NAME": "M8 Test",
            "GIT_COMMITTER_DATE": "2001-02-03T04:05:06+0000",
            "GIT_COMMITTER_EMAIL": "m8-test@example.invalid",
            "GIT_COMMITTER_NAME": "M8 Test",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
        }
    )
    if pycache_root is not None:
        env["PYTHONPYCACHEPREFIX"] = str(pycache_root)
    return env


def git(repo: Path, *args: str) -> bytes:
    executable = replay.select_git_executable()
    result = subprocess.run(
        [
            str(executable),
            "--no-replace-objects",
            "--no-lazy-fetch",
            "-C",
            str(repo),
            "-c",
            "core.quotepath=false",
            "-c",
            "core.fsmonitor=false",
            "--literal-pathspecs",
            *args,
        ],
        env=test_env(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    check(result.returncode == 0, f"git command failed: {args!r}")
    return result.stdout


def create_repo(repo: Path, source_root: Path) -> tuple[Path, str]:
    repo.mkdir()
    git(repo, "init", "--quiet")
    git(repo, "config", "core.autocrlf", "false")
    for logical_path in replay.EXPECTED_PATHS:
        source = source_root.joinpath(*logical_path.split("/"))
        check(source.is_file(), f"missing source fixture: {logical_path}")
        destination = repo.joinpath(*logical_path.split("/"))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
    git(repo, "add", "--all")
    git(repo, "commit", "--quiet", "-m", "historical replay fixture")
    commit = git(repo, "rev-parse", "HEAD").decode("ascii").strip()
    return repo, commit


def cli(repo: Path, commit: str, cwd: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo",
            str(repo),
            "--commit",
            commit,
            *args,
        ],
        cwd=cwd,
        env=test_env(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60,
    )


def report_from(result: subprocess.CompletedProcess[bytes]) -> dict:
    check(result.stderr == b"", f"unexpected stderr: {result.stderr!r}")
    check(result.stdout.endswith(b"\n"), "canonical report lacks final LF")
    check(b"\r" not in result.stdout, "canonical report contains CR")
    report = json.loads(result.stdout.decode("utf-8"))
    check(replay.canonical(report) == result.stdout, "report is not canonical JSON")
    return report


def replace_repo_assignment(source: bytes, replacement: str) -> bytes:
    text = source.decode("utf-8")
    module = ast.parse(text)
    assignment = next(
        statement
        for statement in module.body
        if isinstance(statement, ast.Assign)
        and len(statement.targets) == 1
        and isinstance(statement.targets[0], ast.Name)
        and statement.targets[0].id == "REPO"
    )
    call = assignment.value
    assert isinstance(call, ast.Call)
    literal = call.args[0]
    assert isinstance(literal, ast.Constant)
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    end_lineno = literal.end_lineno
    end_col_offset = literal.end_col_offset
    assert end_lineno is not None and end_col_offset is not None
    start = offsets[literal.lineno - 1] + literal.col_offset
    end = offsets[end_lineno - 1] + end_col_offset
    return source[:start] + replacement.encode("utf-8") + source[end:]


def commit_mutation(repo: Path, logical_path: str, data: bytes, message: str) -> str:
    path = repo.joinpath(*logical_path.split("/"))
    path.write_bytes(data)
    git(repo, "add", "--", logical_path)
    git(repo, "commit", "--quiet", "-m", message)
    return git(repo, "rev-parse", "HEAD").decode("ascii").strip()


def clone_case(repo: Path, commit: str, workspace: Path) -> None:
    workspace.mkdir()
    clone = workspace / "clone"
    executable = replay.select_git_executable()
    result = subprocess.run(
        [
            str(executable),
            "--no-replace-objects",
            "--no-lazy-fetch",
            "clone",
            "--quiet",
            "--no-local",
            "--no-hardlinks",
            "--no-checkout",
            str(repo),
            str(clone),
        ],
        cwd=workspace,
        env=test_env(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    check(result.returncode == 0, "full clone failed")
    check(not (clone / ".git/shallow").exists(), "clone is shallow")
    alternates = clone / ".git/objects/info/alternates"
    check(not alternates.exists() or not alternates.read_bytes().strip(), "clone uses alternates")
    git(clone, "checkout", "--detach", "--quiet", commit)
    clone_cwd = workspace / "clone-unrelated-cwd"
    clone_cwd.mkdir()
    clone_result = cli(clone, commit, clone_cwd)
    check(clone_result.returncode == 0, "clone replay failed")
    clone_report = report_from(clone_result)
    check(clone_report["status"] == "PASS", "clone replay did not pass")
    check(git(clone, "status", "--porcelain=v1", "--untracked-files=all") == b"", "clone became dirty")



def test_descendant_pipe_cleanup(workspace: Path) -> None:
    """A descendant retaining both pipes must not hang the bounded runner."""
    child = workspace / "pipe-child.py"
    child.write_text(
        "import subprocess, sys\n"
        "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n",
        encoding="utf-8",
    )
    started = time.monotonic()
    return_code, stdout, stderr = replay.run_bounded_process(
        [sys.executable, "-I", str(child)],
        workspace,
        allowed_python_script=child,
        timeout_seconds=5,
    )
    elapsed = time.monotonic() - started
    check(return_code == 0, "descendant-pipe fixture leader did not exit cleanly")
    check(stdout == b"" and stderr == b"", "descendant-pipe fixture emitted output")
    check(elapsed < 12, "descendant retaining output pipes caused a hang")


def test_bounded_destination_contract(workspace: Path) -> None:
    """Reject absent, ambiguous, or mismatched process authority."""
    child = workspace / "bounded-child.py"
    other = workspace / "other-child.py"
    child.write_text("pass\n", encoding="utf-8")
    other.write_text("pass\n", encoding="utf-8")

    cases = (
        (
            "missing authority",
            [sys.executable, "-I", str(child)],
            {},
            "exactly one bounded process destination is required",
        ),
        (
            "ambiguous authority",
            [sys.executable, "-I", str(child)],
            {
                "allowed_python_script": child,
                "allowed_isolated_code": "pass",
            },
            "exactly one bounded process destination is required",
        ),
        (
            "command mismatch",
            [sys.executable, "-I", str(other)],
            {"allowed_python_script": child},
            "bounded process destination mismatch",
        ),
        (
            "wrong script authority",
            [sys.executable, "-I", str(child)],
            {"allowed_python_script": other},
            "bounded process destination mismatch",
        ),
        (
            "wrong isolated code authority",
            [sys.executable, "-I", "-c", "pass"],
            {"allowed_isolated_code": "raise SystemExit(1)"},
            "bounded process destination mismatch",
        ),
    )
    for label, command, kwargs, expected in cases:
        try:
            replay.run_bounded_process(command, workspace, **kwargs)
        except replay.FreezeError as exc:
            check(expected in str(exc), f"{label} failed incorrectly: {exc}")
        else:
            raise AssertionError(f"{label} was accepted")


def fresh_materialization_mutation_source(source: bytes) -> bytes:
    """Make validator one corrupt validator two only in its private copy."""
    marker = b'print("ALL CHECKS PASS")'
    injection = (
        b'(REPO / "tools/m8_validate_p0_r02.py").write_bytes(b"mutated by validator one\\n")\n'
        + marker
    )
    mutated = source.replace(marker, injection, 1)
    check(mutated != source, "fresh-materialization mutation did not apply")
    return mutated


def test_fresh_second_materialization(
    repo: Path,
    good_commit: str,
    original_validator: bytes,
    unrelated_cwd: Path,
) -> None:
    """Validator-one writes cannot influence validator-two source bytes."""
    git(repo, "checkout", "--detach", "--quiet", good_commit)
    mutation_commit = commit_mutation(
        repo,
        "tools/m8_validate_p1_materials.py",
        fresh_materialization_mutation_source(original_validator),
        "mutate sibling validator in private materialization",
    )
    result = cli(repo, mutation_commit, unrelated_cwd)
    check(result.returncode == 0, f"fresh materialization replay failed: {result.stderr!r}")
    report = report_from(result)
    check(report["status"] == "PASS", "fresh materialization replay is not PASS")
    check(
        [(item["checks"], item["passed"], item["failed"]) for item in report["validators"]]
        == [(88, 88, 0), (77, 77, 0)],
        "validator-one mutation influenced validator two",
    )

def shallow_repository_case(
    repo: Path,
    good_commit: str,
    workspace: Path,
) -> None:
    """The replay helper must reject shallow object stores."""
    shallow = workspace / "shallow"
    result = subprocess.run(
        [
            str(replay.select_git_executable()),
            "clone",
            "--quiet",
            "--depth",
            "1",
            "--branch",
            "fixture-tip",
            f"file:///{repo.as_posix()}",
            str(shallow),
        ],
        env=test_env(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    check(result.returncode == 0, "shallow clone fixture failed")
    check((shallow / ".git/shallow").is_file(), "fixture repository is not shallow")
    shallow_commit = git(shallow, "rev-parse", "HEAD").decode("ascii").strip()
    check(shallow_commit == good_commit, "shallow clone changed selected commit")
    cwd = workspace / "shallow-unrelated-cwd"
    cwd.mkdir()
    replay_result = cli(shallow, good_commit, cwd)
    check(replay_result.returncode == 2, "shallow repository was accepted")
    check(
        b"shallow repositories are not allowed" in replay_result.stderr,
        "shallow rejection reason differs",
    )


def main() -> int:
    try:
        source_root = SCRIPT.resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix="m8-v3-historical-selftest-") as directory:
            workspace = Path(directory)
            repo, good_commit = create_repo(workspace / "repo", source_root)
            unrelated_cwd = workspace / "unrelated-cwd"
            unrelated_cwd.mkdir()

            first = cli(repo, good_commit, unrelated_cwd)
            second = cli(repo, good_commit, unrelated_cwd)
            check(first.returncode == 0, f"baseline replay failed: {first.stderr!r}")
            check(second.returncode == 0, "second baseline replay failed")
            check(first.stdout == second.stdout, "canonical output is not deterministic")
            report = report_from(first)
            check(report["status"] == "PASS", "baseline status is not PASS")
            check(report["inventory_file_count"] == 8, "inventory is not exactly eight paths")
            check(
                [item["path"] for item in report["inventory"]] == list(replay.EXPECTED_PATHS),
                "inventory paths differ",
            )
            check(
                [(item["checks"], item["passed"], item["failed"]) for item in report["validators"]]
                == [(88, 88, 0), (77, 77, 0)],
                "historical check totals differ",
            )
            check(
                all(item["all_checks_pass_marker_count"] == 1 for item in report["validators"]),
                "ALL CHECKS PASS marker differs",
            )
            check(directory.encode("utf-8") not in first.stdout, "host temporary path leaked")

            ambient = workspace / "ambient"
            ambient.mkdir()
            ambient_env = test_env()
            ambient_env.update(
                {
                    "REPO": str(workspace / "wrong-repo"),
                    "GIT_DIR": str(workspace / "wrong-git-dir"),
                    "GIT_WORK_TREE": str(workspace / "wrong-work-tree"),
                    "M8_AMBIENT_SENTINEL": "must-not-reach-validator",
                }
            )
            ambient_result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--commit",
                    good_commit,
                ],
                cwd=ambient,
                env=ambient_env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=60,
            )
            check(ambient_result.returncode == 0, "ambient environment changed replay")
            check(ambient_result.stdout == first.stdout, "ambient output differs")

            relative = subprocess.run(
                [sys.executable, str(SCRIPT), "--repo", "repo", "--commit", good_commit],
                cwd=workspace,
                env=test_env(),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=30,
            )
            check(relative.returncode == 2, "relative --repo was accepted")
            check(cli(repo, "HEAD", unrelated_cwd).returncode == 2, "symbolic commit was accepted")
            check(cli(repo, good_commit.upper(), unrelated_cwd).returncode == 2, "uppercase commit was accepted")
            test_descendant_pipe_cleanup(workspace)
            test_bounded_destination_contract(workspace)

            original_validator = (repo / "tools/m8_validate_p1_materials.py").read_bytes()
            test_fresh_second_materialization(
                repo,
                good_commit,
                original_validator,
                unrelated_cwd,
            )
            git(repo, "checkout", "--detach", "--quiet", good_commit)
            duplicate_source = original_validator + b"\nREPO = Path('duplicate')\n"
            duplicate_commit = commit_mutation(
                repo,
                "tools/m8_validate_p1_materials.py",
                duplicate_source,
                "duplicate repo assignment",
            )
            duplicate = cli(repo, duplicate_commit, unrelated_cwd)
            check(duplicate.returncode == 2, "duplicate REPO assignment was accepted")

            git(repo, "checkout", "--detach", "--quiet", good_commit)
            mismatch_source = original_validator.replace(
                b'print("ALL CHECKS PASS")',
                b'print("ALL CHECKS FAIL")',
                1,
            )
            check(mismatch_source != original_validator, "marker mutation did not apply")
            mismatch_commit = commit_mutation(
                repo,
                "tools/m8_validate_p1_materials.py",
                mismatch_source,
                "mismatch marker",
            )
            mismatch = cli(repo, mismatch_commit, unrelated_cwd)
            check(mismatch.returncode == 1, "mismatch did not produce truthful nonzero exit")
            mismatch_report = report_from(mismatch)
            check(mismatch_report["status"] == "FAIL", "mismatch report is not FAIL")
            check(bool(mismatch_report["mismatches"]), "mismatch report lacks reasons")

            git(repo, "checkout", "--detach", "--quiet", good_commit)
            bad_shape = replace_repo_assignment(original_validator, "Path('one', 'two')")
            bad_shape_commit = commit_mutation(
                repo,
                "tools/m8_validate_p1_materials.py",
                bad_shape,
                "bad repo assignment shape",
            )
            bad_shape_result = cli(repo, bad_shape_commit, unrelated_cwd)
            check(bad_shape_result.returncode == 2, "bad REPO assignment shape was accepted")

            clone_case(repo, good_commit, workspace / "clone-case")
            git(repo, "branch", "--force", "fixture-tip", good_commit)
            shallow_repository_case(
                repo,
                good_commit,
                workspace / "shallow-case",
            )

            git(repo, "checkout", "--detach", "--quiet", good_commit)
            (repo / replay.EXPECTED_PATHS[0]).write_bytes(b"ambient mutable checkout bytes\n")
            dirty_result = cli(repo, good_commit, unrelated_cwd)
            check(dirty_result.returncode == 0, "mutable checkout altered object replay")
            check(dirty_result.stdout == first.stdout, "mutable checkout bytes affected replay")
        print("ALL PASS: M8 v3 historical regression replay self-test")
        return 0
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
