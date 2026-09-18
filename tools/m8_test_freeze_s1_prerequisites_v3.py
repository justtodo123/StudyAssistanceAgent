#!/usr/bin/env python3
"""Hermetic self-tests for the Git-object-only M8 v3 review freeze."""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

import m8_freeze_s1_prerequisites_v3 as freeze_module
from m8_freeze_s1_prerequisites_v3 import (
    CODE_FIXED_BOOTSTRAP_PATHS,
    DECLARED_TEMPLATE_PATHS,
    FREEZE_FORMAT,
    HISTORICAL_REPLAY_ENTRYPOINT,
    ORACLE_MANIFEST_FORMAT,
    ORACLE_MANIFEST_PATH,
    SUPPORTED_CLOSURE_VERSION,
    FreezeError,
    build_freeze,
    canonical,
    compare_worktree,
    derive_closure_digest,
    derive_gating_closure,
    expand_fixture_paths,
    parse_oracle_manifest,
    publish_output,
)

SCRIPT = Path(__file__).with_name("m8_freeze_s1_prerequisites_v3.py")


MANIFEST_SOURCE = (
    Path(__file__).resolve().parents[1]
    / "docs/plans/references/m8-minimal-1k-v3-s1-prereq-oracle-manifest.json"
).read_bytes()
MANIFEST = parse_oracle_manifest(MANIFEST_SOURCE)
MANIFEST_GATING = MANIFEST["gating"]
MANIFEST_FIXTURE = MANIFEST["fixture_expansion"]
assert isinstance(MANIFEST_GATING, dict) and isinstance(MANIFEST_FIXTURE, dict)
DEFAULT_PATHS = list(derive_gating_closure(MANIFEST))
FIXTURE_PATHS = list(expand_fixture_paths(MANIFEST_FIXTURE))
FIXTURE_ROOT = str(MANIFEST_FIXTURE["root"])
FIXTURE_GRAPHS = tuple(MANIFEST_FIXTURE["graphs"])
FIXTURE_MEMBERS = tuple(MANIFEST_FIXTURE["members"])


def check(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def expect_error(
    action,
    fragment: str,
    error_type: type[BaseException] = FreezeError,
) -> None:
    try:
        action()
    except error_type as exc:
        check(fragment in str(exc), f"expected {fragment!r}, got {exc!r}")
    else:
        raise AssertionError(f"expected {error_type.__name__} containing {fragment!r}")


def test_env() -> dict[str, str]:
    env = {
        name: value
        for name, value in os.environ.items()
        if not name.upper().startswith("GIT_")
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
        }
    )
    return env


def run_git(repo: Path, *args: str, stdin: bytes | None = None) -> bytes:
    executable = freeze_module.select_git_executable()
    result = subprocess.run(
        [
            str(executable),
            "--no-replace-objects",
            "--no-lazy-fetch",
            "-C",
            str(repo),
            "--literal-pathspecs",
            *args,
        ],
        input=stdin,
        env=test_env(),
        capture_output=True,
        check=False,
        timeout=30,
    )
    if result.returncode != 0:
        raise AssertionError(
            result.stderr.decode("utf-8", errors="replace")
            or f"git command failed: {args}"
        )
    return result.stdout


def explicit_git(repo: Path, *args: str, stdin: bytes | None = None) -> bytes:
    executable = freeze_module.select_git_executable()
    result = subprocess.run(
        [str(executable), *args],
        cwd=repo,
        input=stdin,
        env=test_env(),
        capture_output=True,
        check=False,
        timeout=30,
    )
    if result.returncode != 0:
        raise AssertionError(
            result.stderr.decode("utf-8", errors="replace")
            or f"git command failed: {args}"
        )
    return result.stdout


def clone_replay_tests(repo: Path, commit: str) -> None:
    """Prove an isolated full clone obtains identical Git-object freeze bytes."""
    with tempfile.TemporaryDirectory(prefix="m8-s1-freeze-clone-") as directory:
        workspace = Path(directory)
        clone = workspace / "clone"
        executable = freeze_module.select_git_executable()
        result = subprocess.run(
            [
                str(executable),
                "--no-replace-objects",
                "--no-lazy-fetch",
                "clone",
                "--no-local",
                "--no-hardlinks",
                "--no-checkout",
                str(repo),
                str(clone),
            ],
            cwd=workspace,
            env=test_env(),
            capture_output=True,
            check=False,
            timeout=30,
        )
        check(result.returncode == 0, "full --no-local clone failed")
        check(not (clone / ".git/shallow").exists(), "clone is shallow")
        alternates = clone / ".git/objects/info/alternates"
        check(
            not alternates.exists() or not alternates.read_bytes().strip(),
            "clone uses alternates",
        )
        explicit_git(clone, "checkout", "--detach", "--quiet", commit)
        check(
            explicit_git(clone, "rev-parse", "HEAD").decode("ascii").strip()
            == commit,
            "clone checkout differs",
        )
        explicit_git(clone, "fsck", "--full", "--strict", "--no-reflogs")
        check(
            explicit_git(
                clone,
                "status",
                "--porcelain=v1",
                "--untracked-files=all",
            )
            == b"",
            "clone is dirty before replay",
        )
        primary = build_freeze(commit, repo_root=repo)
        replay = build_freeze(commit, repo_root=clone, git_executable=executable)
        check(canonical(primary) == canonical(replay), "independent clone freeze differs")
        check(compare_worktree(replay, clone) == [], "clone worktree differs")
        check(
            [item["path"] for item in replay["frozen_files"]]
            == sorted(DEFAULT_PATHS, key=lambda path: path.encode("utf-8")),
            "clone freeze inventory is not deterministic",
        )
        for item in replay["frozen_files"]:
            object_type = explicit_git(
                clone,
                "cat-file",
                "-t",
                item["git_blob_oid"],
            )
            check(object_type == b"blob\n", f"clone lacks blob: {item['path']}")
        check(
            explicit_git(
                clone,
                "status",
                "--porcelain=v1",
                "--untracked-files=all",
            )
            == b"",
            "clone is dirty after replay",
        )


def write_inventory(repo: Path) -> None:
    for index, path in enumerate(DEFAULT_PATHS):
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if path == ORACLE_MANIFEST_PATH:
            target.write_bytes(MANIFEST_SOURCE)
        else:
            target.write_bytes(f"s1-prerequisite:{index}:{path}\n".encode("utf-8"))


def create_repo(repo: Path) -> Path:
    repo.mkdir()
    run_git(repo, "init", "--quiet")
    run_git(repo, "config", "core.autocrlf", "false")
    run_git(
        repo,
        "config",
        "core.filemode",
        "false" if os.name == "nt" else "true",
    )
    write_inventory(repo)
    run_git(repo, "add", "--all")
    run_git(repo, "commit", "--quiet", "-m", "test inventory")
    return repo


def cli(repo: Path, commit: str, *args: str):
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--commit",
            commit,
            "--repo",
            str(repo),
            *args,
        ],
        cwd=repo.parent,
        env=test_env(),
        capture_output=True,
        check=False,
        timeout=30,
    )


def make_tree_commit(repo: Path, message: str) -> str:
    tree = run_git(repo, "write-tree").decode("ascii").strip()
    parent = run_git(repo, "rev-parse", "HEAD").decode("ascii").strip()
    return run_git(
        repo,
        "commit-tree",
        tree,
        "-p",
        parent,
        "-m",
        message,
    ).decode("ascii").strip()


def manifest_validation_tests(repo: Path, commit: str) -> None:
    """Exercise canonical parsing, target binding, bootstrap, and class guards."""
    check(MANIFEST["format"] == ORACLE_MANIFEST_FORMAT, "wrong manifest format")
    check(parse_oracle_manifest(MANIFEST_SOURCE) == MANIFEST, "canonical manifest does not parse")
    expect_error(
        lambda: parse_oracle_manifest(MANIFEST_SOURCE.rstrip(b"\n") + b" \n"),
        "not canonical",
    )
    expect_error(
        lambda: parse_oracle_manifest(b'{"format":"x","format":"y"}\n'),
        "duplicate JSON key",
    )

    manifest_path = repo / ORACLE_MANIFEST_PATH
    original = manifest_path.read_bytes()
    manifest_path.write_bytes(b'{"dirty":"worktree"}\n')
    check(
        build_freeze(commit, repo_root=repo)["manifest"]["sha256"]
        == hashlib.sha256(original).hexdigest(),
        "dirty worktree changed target-commit manifest binding",
    )
    manifest_path.write_bytes(original)

    def commit_manifest(mutator, message: str) -> str:
        candidate = parse_oracle_manifest(original)
        mutator(candidate)
        manifest_path.write_bytes(canonical(candidate))
        run_git(repo, "add", "--", ORACLE_MANIFEST_PATH)
        candidate_commit = make_tree_commit(repo, message)
        manifest_path.write_bytes(original)
        run_git(repo, "add", "--", ORACLE_MANIFEST_PATH)
        return candidate_commit

    def first_subprocess(item: dict[str, object]) -> dict[str, object]:
        gating = item["gating"]
        assert isinstance(gating, dict)
        subprocesses = gating["allowed_subprocesses"]
        assert isinstance(subprocesses, list) and subprocesses
        child = subprocesses[0]
        assert isinstance(child, dict)
        return child

    def expect_manifest_error(mutator, message: str, expected: str) -> None:
        candidate = commit_manifest(mutator, message)
        expect_error(lambda: build_freeze(candidate, repo_root=repo), expected)

    def omit_bootstrap(item: dict[str, object]) -> None:
        gating = item["gating"]
        assert isinstance(gating, dict)
        modules = gating["support_modules"]
        assert isinstance(modules, list)
        modules.remove("tools/m8_freeze_s1_prerequisites_v3.py")

    expect_manifest_error(
        omit_bootstrap,
        "omit bootstrap",
        "process-control support module",
    )

    def add_forbidden(item: dict[str, object]) -> None:
        gating = item["gating"]
        assert isinstance(gating, dict)
        reads = gating["static_reads"]
        assert isinstance(reads, list)
        reads.append("docs/plans/references/external-gates/forbidden.json")
        reads.sort(key=lambda path: str(path).encode("utf-8"))

    expect_manifest_error(
        add_forbidden,
        "forbidden ambient path",
        "forbidden ambient path",
    )
    expect_manifest_error(
        lambda item: item["declared_templates"].reverse(),
        "bad template order",
        "declared_templates",
    )
    expect_manifest_error(
        lambda item: item["historical_replay"].update(
            {"entrypoint": "tools/other.py"}
        ),
        "bad replay entrypoint",
        "historical replay entrypoint",
    )
    expect_manifest_error(
        lambda item: first_subprocess(item).pop("success_oracle"),
        "missing child success oracle",
        "allowed subprocess has invalid keys",
    )
    expect_manifest_error(
        lambda item: first_subprocess(item).update({"extra": True}),
        "extra child field",
        "allowed subprocess has invalid keys",
    )
    def mutate_success_oracle(
        item: dict[str, object],
        key: str,
        value: object,
    ) -> None:
        oracle = first_subprocess(item)["success_oracle"]
        assert isinstance(oracle, dict)
        oracle[key] = value

    expect_manifest_error(
        lambda item: mutate_success_oracle(item, "kind", "unsupported"),
        "bad child oracle kind",
        "unsupported allowed subprocess success oracle",
    )
    expect_manifest_error(
        lambda item: mutate_success_oracle(item, "success_line", ""),
        "empty child success line",
        "non-empty string",
    )
    expect_manifest_error(
        lambda item: mutate_success_oracle(
            item,
            "success_line",
            "first\nsecond",
        ),
        "multiline child success line",
        "one non-empty line",
    )

    def mutate_unittest_count(item: dict[str, object], value: object) -> None:
        gating = item["gating"]
        assert isinstance(gating, dict)
        subprocesses = gating["allowed_subprocesses"]
        assert isinstance(subprocesses, list)
        child = next(
            candidate
            for candidate in subprocesses
            if isinstance(candidate, dict)
            and isinstance(candidate.get("success_oracle"), dict)
            and candidate["success_oracle"].get("kind") == "unittest"
        )
        child["success_oracle"]["expected_test_count"] = value

    for index, invalid_count in enumerate((True, 0, -1, 1.5)):
        expect_manifest_error(
            lambda item, value=invalid_count: mutate_unittest_count(
                item,
                value,
            ),
            f"bad unittest count {index}",
            "positive integer",
        )


def check_cli_error(result, fragment: bytes) -> None:
    check(result.returncode == 2, f"CLI error exited {result.returncode}")
    check(result.stdout == b"", "CLI error wrote stdout")
    check(result.stderr.startswith(b"ERROR "), "CLI error diagnostic missing")
    check(fragment in result.stderr, f"CLI error omitted {fragment!r}")
    check(b"Traceback" not in result.stderr, "CLI error exposed traceback")


def write_git_shim(directory: Path, body: str) -> Path:
    if os.name == "nt":
        shim = directory / "git.cmd"
        shim.write_text("@echo off\r\n" + body + "\r\n", encoding="utf-8")
    else:
        shim = directory / "git"
        shim.write_text("#!/bin/sh\n" + body + "\n", encoding="utf-8")
        shim.chmod(0o755)
    return shim


def capability_failure_tests() -> None:
    executable = freeze_module.trusted_git_executable()

    class FakeStream:
        def __init__(self, data: bytes):
            self.data = data
            self.read_once = False
            self.closed = False

        def read(self, _size: int) -> bytes:
            if self.read_once:
                return b""
            self.read_once = True
            return self.data

        def close(self) -> None:
            self.closed = True

    class FakeProcess:
        def __init__(self, stdout: bytes, stderr: bytes = b""):
            self.stdout = FakeStream(stdout)
            self.stderr = FakeStream(stderr)
            self.returncode: int | None = None
            self.pid = 4242

        def wait(self, timeout: float | None = None) -> int:
            self.returncode = 0
            return self.returncode

        def kill(self) -> None:
            self.returncode = -9

    freeze_module._GIT_EXECUTABLE = executable
    for output, fragment in (
        (b"git version malformed\n", "version output is malformed"),
        (b"git version 2.44.9\n", "2.45.0 or newer"),
        (b"git version \xff\n", "version is not ASCII"),
    ):
        freeze_module._GIT_CAPABILITY_CHECKED = None
        with mock.patch.object(
            freeze_module.subprocess,
            "Popen",
            return_value=FakeProcess(output),
        ):
            expect_error(
                lambda: freeze_module.validate_git_capability(executable),
                fragment,
            )

    class TimeoutProcess(FakeProcess):
        def __init__(self) -> None:
            super().__init__(b"")
            self.kill_calls = 0
            self.wait_calls = 0

        def wait(self, timeout: float | None = None) -> int:
            self.wait_calls += 1
            if self.wait_calls == 1:
                raise subprocess.TimeoutExpired(
                    [str(executable)],
                    timeout if timeout is not None else 0.0,
                )
            self.returncode = -9
            return self.returncode

        def kill(self) -> None:
            self.kill_calls += 1
            self.returncode = -9

    timed_out = TimeoutProcess()
    timed_out.pid = 0
    freeze_module._GIT_CAPABILITY_CHECKED = None
    with mock.patch.object(
        freeze_module.subprocess,
        "Popen",
        return_value=timed_out,
    ):
        expect_error(
            lambda: freeze_module.validate_git_capability(executable),
            "Git operation timed out: --version",
        )
    check(timed_out.kill_calls == 1, "timed-out Git process was not killed")
    check(timed_out.wait_calls == 2, "timed-out Git process was not reaped")
    check(timed_out.stdout.closed, "timed-out Git stdout was not closed")
    check(timed_out.stderr.closed, "timed-out Git stderr was not closed")

    freeze_module._GIT_CAPABILITY_CHECKED = None
    with mock.patch.object(
        freeze_module.subprocess,
        "Popen",
        side_effect=OSError("cannot launch"),
    ):
        expect_error(
            lambda: freeze_module.validate_git_capability(executable),
            "cannot be run",
        )
    freeze_module._GIT_CAPABILITY_CHECKED = None
    freeze_module.validate_git_capability(executable)


def batch_blob_failure_tests() -> None:
    data = b"payload\n"
    oid = hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()
    entry = [("tools/example.py", "100644", "blob", oid)]

    def response(
        *,
        response_oid: str = oid,
        object_type: str = "blob",
        size: int = len(data),
        body: bytes = data,
        suffix: bytes = b"\n",
    ) -> bytes:
        return (
            f"{response_oid} {object_type} {size}\n".encode("ascii")
            + body
            + suffix
        )

    with mock.patch.object(freeze_module, "git", return_value=response()):
        check(
            freeze_module.read_blob_batch(entry) == {entry[0][0]: data},
            "valid batch blob was not decoded",
        )

    cases = (
        (b"unterminated", "truncated git cat-file batch header"),
        (b"not a valid header\n", "malformed git cat-file batch header"),
        (response(response_oid="0" * 40), "unexpected git cat-file batch object"),
        (response(object_type="tree"), "unexpected git cat-file batch object"),
        (response(size=-1), "unexpected git cat-file batch object"),
        (response(size=len(data) + 1), "truncated git cat-file batch body"),
        (response(body=b"changed\n"), "blob object ID mismatch"),
        (response() + b"extra", "unexpected trailing git cat-file batch output"),
    )
    for raw, fragment in cases:
        with mock.patch.object(freeze_module, "git", return_value=raw):
            expect_error(lambda: freeze_module.read_blob_batch(entry), fragment)

    duplicate = [entry[0], entry[0]]
    with mock.patch.object(freeze_module, "git") as git_mock:
        expect_error(
            lambda: freeze_module.read_blob_batch(duplicate),
            "duplicate Git tree path",
        )
        check(not git_mock.called, "duplicate inventory reached Git")

    with mock.patch.object(freeze_module, "MAX_FILE_BYTES", len(data) - 1):
        with mock.patch.object(freeze_module, "git", return_value=response()):
            expect_error(
                lambda: freeze_module.read_blob_batch(entry),
                "blob exceeds per-file safety limit",
            )


def process_tree_failure_tests() -> None:
    executable = freeze_module.trusted_git_executable()

    class FakeStream:
        def __init__(self, data: bytes = b"") -> None:
            self.data = data
            self.read_once = False
            self.closed = False

        def read(self, _size: int) -> bytes:
            if self.read_once:
                return b""
            self.read_once = True
            return self.data

        def close(self) -> None:
            self.closed = True

    class FailingStream(FakeStream):
        def read(self, _size: int) -> bytes:
            raise OSError("stream failed")

    class FakeProcess:
        def __init__(self, stdout: FakeStream | None = None) -> None:
            self.stdin = None
            self.stdout = stdout or FakeStream()
            self.stderr = FakeStream()
            self.returncode: int | None = None
            self.pid = 4242
            self.kill_calls = 0
            self.wait_calls = 0

        def wait(self, timeout: float | None = None) -> int:
            self.wait_calls += 1
            self.returncode = 0
            return self.returncode

        def kill(self) -> None:
            self.kill_calls += 1
            self.returncode = -9

    class TimeoutProcess(FakeProcess):
        def wait(self, timeout: float | None = None) -> int:
            self.wait_calls += 1
            if self.wait_calls == 1:
                raise subprocess.TimeoutExpired([str(executable)], timeout or 0.0)
            self.returncode = -9
            return self.returncode

    class UnreapableProcess(TimeoutProcess):
        def wait(self, timeout: float | None = None) -> int:
            self.wait_calls += 1
            raise subprocess.TimeoutExpired([str(executable)], timeout or 0.0)

        def kill(self) -> None:
            self.kill_calls += 1

    command = [str(executable), "--version"]
    args = ("--version",)

    overflowing = FakeProcess(FakeStream(b"x" * 17))
    overflowing.pid = 0
    with mock.patch.object(freeze_module, "MAX_GIT_OUTPUT_BYTES", 16):
        with mock.patch.object(
            freeze_module.subprocess,
            "Popen",
            return_value=overflowing,
        ):
            expect_error(
                lambda: freeze_module.run_git_process(command, args),
                "Git output exceeds safety limit",
            )
    check(overflowing.kill_calls == 1, "overflowing Git process was not killed")

    stream_failed = FakeProcess(FailingStream())
    stream_failed.pid = 0
    with mock.patch.object(
        freeze_module.subprocess,
        "Popen",
        return_value=stream_failed,
    ):
        expect_error(
            lambda: freeze_module.run_git_process(command, args),
            "Git output stream failed",
        )

    unreapable = UnreapableProcess()
    unreapable.pid = 0
    with mock.patch.object(
        freeze_module.subprocess,
        "Popen",
        return_value=unreapable,
    ):
        expect_error(
            lambda: freeze_module.run_git_process(command, args),
            "Git operation could not be reaped",
        )

    if os.name != "nt":
        return

    timed_out = TimeoutProcess()
    killer = FakeProcess()
    killer.pid = 0
    with mock.patch.object(
        freeze_module.subprocess,
        "Popen",
        side_effect=[timed_out, killer],
    ) as popen_mock:
        expect_error(
            lambda: freeze_module.run_git_process(command, args),
            "Git operation timed out",
        )
    check(len(popen_mock.call_args_list) == 2, "taskkill was not launched")
    taskkill_command = popen_mock.call_args_list[1].args[0]
    check(
        taskkill_command[-4:] == ["/PID", str(timed_out.pid), "/T", "/F"],
        "taskkill command did not target the process tree",
    )
    check(timed_out.kill_calls == 0, "successful taskkill used root-only fallback")

    fallback = TimeoutProcess()
    with mock.patch.object(
        freeze_module.subprocess,
        "Popen",
        side_effect=[fallback, OSError("taskkill launch failed")],
    ):
        expect_error(
            lambda: freeze_module.run_git_process(command, args),
            "Git operation timed out",
        )
    check(fallback.kill_calls == 1, "failed taskkill did not use root fallback")

    timed_out_killer_parent = TimeoutProcess()
    timed_out_killer = TimeoutProcess()
    timed_out_killer.pid = 0
    with mock.patch.object(
        freeze_module.subprocess,
        "Popen",
        side_effect=[timed_out_killer_parent, timed_out_killer],
    ):
        expect_error(
            lambda: freeze_module.run_git_process(command, args),
            "Git operation timed out",
        )
    check(timed_out_killer.kill_calls == 1, "timed-out taskkill was not killed")
    check(timed_out_killer.wait_calls == 2, "timed-out taskkill was not reaped")
    check(
        timed_out_killer_parent.kill_calls == 1,
        "timed-out taskkill did not use root fallback",
    )

    lookup_failed = TimeoutProcess()
    real_inspect = freeze_module.inspect_path_components

    def fail_taskkill_lookup(path: Path, label: str) -> Path:
        if label == "taskkill executable":
            raise FreezeError("taskkill cannot be inspected", "git")
        return real_inspect(path, label)

    with mock.patch.object(
        freeze_module,
        "inspect_path_components",
        side_effect=fail_taskkill_lookup,
    ):
        with mock.patch.object(
            freeze_module.subprocess,
            "Popen",
            return_value=lookup_failed,
        ):
            expect_error(
                lambda: freeze_module.run_git_process(command, args),
                "Git operation timed out",
            )
    check(
        lookup_failed.kill_calls == 1,
        "taskkill lookup failure did not use root fallback",
    )


def size_limit_tests(repo: Path, commit: str) -> None:
    first_path = DEFAULT_PATHS[0]
    source_size = len((repo / first_path).read_bytes())
    with mock.patch.object(freeze_module, "MAX_FILE_BYTES", source_size - 1):
        expect_error(
            lambda: build_freeze(commit, repo_root=repo),
            "blob exceeds per-file safety limit",
        )
    with mock.patch.object(freeze_module, "MAX_TOTAL_BYTES", source_size - 1):
        expect_error(
            lambda: build_freeze(commit, repo_root=repo),
            "candidate inventory exceeds total byte safety limit",
        )


def executable_path_tests(workspace: Path) -> None:
    executable = freeze_module.trusted_git_executable()
    check(
        freeze_module.select_git_executable(executable) == executable,
        "explicit Git executable differs",
    )
    expect_error(
        lambda: freeze_module.trusted_git_executable(Path("git")),
        "absolute regular file",
    )
    expect_error(
        lambda: freeze_module.trusted_git_executable(workspace / "missing-git"),
        "does not exist",
    )
    expect_error(
        lambda: freeze_module.trusted_git_executable(workspace),
        "not a regular file",
    )
    link = workspace / "git-link"
    try:
        link.symlink_to(executable)
    except (OSError, NotImplementedError):
        pass
    else:
        expect_error(
            lambda: freeze_module.trusted_git_executable(link),
            "symlink or reparse point",
        )


def publication_failure_tests(workspace: Path) -> None:
    output = workspace / "publication.json"
    output.write_bytes(b"sentinel\n")
    before = output.read_bytes()

    def fail_replace(_source, _target):
        raise OSError("replace failed")

    expect_error(
        lambda: publish_output(output, b"new\n", replace_action=fail_replace),
        "replace failed",
        OSError,
    )
    check(output.read_bytes() == before, "replace failure changed destination")
    check(not list(workspace.glob(".publication.json.*")), "replace failure leaked temporary")

    real_named_temporary = tempfile.NamedTemporaryFile

    class FailingHandle:
        def __init__(self, handle):
            self.handle = handle
            self.name = handle.name

        def __enter__(self):
            self.handle.__enter__()
            return self

        def write(self, _data):
            raise OSError("write failed")

        def __exit__(self, exc_type, exc, traceback):
            return self.handle.__exit__(exc_type, exc, traceback)

    def failing_named_temporary(*args, **kwargs):
        return FailingHandle(real_named_temporary(*args, **kwargs))

    expect_error(
        lambda: publish_output(
            output,
            b"new\n",
            temporary_factory=failing_named_temporary,
        ),
        "write failed",
        OSError,
    )
    check(output.read_bytes() == before, "write failure changed destination")
    check(not list(workspace.glob(".publication.json.*")), "write failure leaked temporary")


def main() -> int:
    try:
        with tempfile.TemporaryDirectory(prefix="m8-s1-freeze-test-") as directory:
            workspace = Path(directory)
            capability_failure_tests()
            batch_blob_failure_tests()
            process_tree_failure_tests()
            executable_path_tests(workspace)
            repo = create_repo(workspace / "repo")
            commit = run_git(repo, "rev-parse", "HEAD").decode("ascii").strip()
            manifest_validation_tests(repo, commit)
            first = build_freeze(commit, repo_root=repo)
            second = build_freeze(commit, repo_root=repo)
            check(canonical(first) == canonical(second), "freeze is not deterministic")
            check(first["format"] == FREEZE_FORMAT, "wrong format")
            check(
                first["purpose"] == "S1_PREREQUISITE_RECORD_ONLY_NOT_AUTHORIZATION",
                "wrong purpose",
            )
            check(first["source_commit"] == commit, "wrong commit")
            check(first["closure_version"] == SUPPORTED_CLOSURE_VERSION, "wrong closure version")
            check(first["manifest"]["path"] == ORACLE_MANIFEST_PATH, "manifest is not bound")
            check(
                first["manifest"]["sha256"] == hashlib.sha256(MANIFEST_SOURCE).hexdigest(),
                "wrong manifest digest",
            )
            check(first["gating"]["entrypoint"] == "tools/m8_test_s1_prerequisites_v3.py", "wrong entrypoint")
            check(first["gating"]["default_mode"] == "gating-only", "wrong default mode")
            manifest_gating = MANIFEST["gating"]
            assert isinstance(manifest_gating, dict)
            expected_subprocesses = manifest_gating["allowed_subprocesses"]
            check(
                first["gating"]["allowed_subprocesses"]
                == expected_subprocesses,
                "gating subprocess declarations changed in freeze",
            )
            subprocess_paths = [
                item["path"]
                for item in first["gating"]["allowed_subprocesses"]
            ]
            check(
                "tools/m8_test_freeze_minimal_1k_v3_review.py"
                in subprocess_paths,
                "S0 freeze regression is not a gating subprocess",
            )
            check(
                "tools/m8_freeze_minimal_1k_v3_review.py" in first["gating"]["support_modules"],
                "S0 freeze implementation is not bound",
            )
            check(first["declared_templates"] == list(DECLARED_TEMPLATE_PATHS), "wrong templates")
            check(
                first["historical_replay"]["entrypoint"] == HISTORICAL_REPLAY_ENTRYPOINT
                and first["historical_replay"]["gating"] is False
                and first["historical_replay"]["object_count"] == 8,
                "historical replay boundary is wrong",
            )
            check(len(FIXTURE_GRAPHS) == 5, "wrong fixture graph count")
            check(len(FIXTURE_MEMBERS) == 18, "wrong fixture member count")
            check(len(FIXTURE_PATHS) == 90, "wrong fixture path count")
            check(set(CODE_FIXED_BOOTSTRAP_PATHS) <= set(DEFAULT_PATHS), "bootstrap omitted")
            check(first["aggregate"]["file_count"] == len(DEFAULT_PATHS), "wrong file count")
            check(
                first["aggregate"]["closure_digest"] == derive_closure_digest(first["frozen_files"]),
                "wrong closure digest",
            )
            paths = [item["path"] for item in first["frozen_files"]]
            check(paths == DEFAULT_PATHS, "wrong manifest-derived inventory")
            check(
                first["worktree_comparison"]["status"] == "NOT_REQUESTED",
                "wrong comparison state",
            )
            for item in first["frozen_files"]:
                data = run_git(repo, "show", f"{commit}:{item['path']}")
                check(item["byte_count"] == len(data), "wrong byte count")
                check(item["lf_count"] == data.count(b"\n"), "wrong LF count")
                check(
                    item["sha256"] == hashlib.sha256(data).hexdigest(),
                    "wrong SHA-256",
                )
                check(item["git_mode"] in {"100644", "100755"}, "wrong mode")

            unexpected_fixture = repo / FIXTURE_ROOT / "unexpected.json"
            unexpected_fixture.write_text("{}\n", encoding="utf-8")
            run_git(repo, "add", "--", str(unexpected_fixture.relative_to(repo)))
            unexpected_commit = make_tree_commit(repo, "unexpected fixture member")
            expect_error(
                lambda: build_freeze(unexpected_commit, repo_root=repo),
                "unexpected fixture members",
            )
            run_git(
                repo,
                "rm",
                "--cached",
                "--quiet",
                "--",
                str(unexpected_fixture.relative_to(repo)),
            )
            unexpected_fixture.unlink()

            missing_fixture = repo / FIXTURE_PATHS[0]
            missing_fixture.unlink()
            run_git(repo, "add", "--update", "--", FIXTURE_PATHS[0])
            missing_commit = make_tree_commit(repo, "missing fixture member")
            expect_error(
                lambda: build_freeze(missing_commit, repo_root=repo),
                "fixture members are missing",
            )
            original_fixture = run_git(
                repo,
                "show",
                f"HEAD:{FIXTURE_PATHS[0]}",
            )
            missing_fixture.parent.mkdir(parents=True, exist_ok=True)
            missing_fixture.write_bytes(original_fixture)
            run_git(repo, "add", "--", FIXTURE_PATHS[0])

            clone_replay_tests(repo, commit)
            size_limit_tests(repo, commit)
            publication_failure_tests(workspace)

            expect_error(
                lambda: build_freeze(commit[:12], repo_root=repo),
                "full lowercase 40-hex",
            )
            expect_error(
                lambda: build_freeze(commit.upper(), repo_root=repo),
                "full lowercase 40-hex",
            )
            expect_error(
                lambda: build_freeze("0" * 40, repo_root=repo),
                "commit object cannot be read",
            )
            blob = first["frozen_files"][0]["git_blob_oid"]
            expect_error(
                lambda: build_freeze(blob, repo_root=repo),
                "not commit",
            )
            expect_error(
                lambda: build_freeze(
                    commit,
                    paths=[DEFAULT_PATHS[0]],
                    repo_root=repo,
                ),
                "custom source inventory",
            )

            output = workspace / "freeze.json"
            payload = canonical(first)
            publish_output(output, payload)
            check(output.read_bytes() == payload, "publication read-back differs")
            check(payload.endswith(b"\n"), "canonical output lacks final LF")
            check(b"\r" not in payload, "canonical output contains CR")

            check(compare_worktree(first, repo) == [], "clean worktree diverges")
            changed = repo / DEFAULT_PATHS[0]
            original = changed.read_bytes()
            changed.write_bytes(original + b"changed\n")
            divergent = compare_worktree(first, repo)
            check(
                divergent
                == sorted(
                    ["<repository-status>", DEFAULT_PATHS[0]],
                    key=lambda item: item.encode("utf-8"),
                ),
                "modified source is not divergent",
            )
            check(
                canonical(build_freeze(commit, repo_root=repo)) == payload,
                "worktree bytes changed Git-object freeze",
            )
            changed.write_bytes(original)

            result = cli(repo, commit, "--output", str(workspace / "cli.json"))
            check(result.returncode == 0, f"CLI failed: {result.stderr!r}")
            check((workspace / "cli.json").read_bytes() == payload, "CLI output differs")
            check(cli(repo, "HEAD").returncode == 2, "CLI accepted ref")
            bad_output = cli(repo, commit, "--output", str(repo / "freeze.json"))
            check(bad_output.returncode == 2, "CLI accepted in-repository output")
            check(not (repo / "freeze.json").exists(), "CLI published inside repository")
        print("ALL PASS: M8 v3 S1 prerequisite freeze self-test")
        return 0
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
