#!/usr/bin/env python3
"""Hermetic self-tests for the Git-object-only M8 v3 review freeze."""
from __future__ import annotations

import hashlib
import os
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

import m8_freeze_minimal_1k_v3_review as freeze_module
from m8_freeze_minimal_1k_v3_review import (
    DEFAULT_PATHS,
    EXPECTED_FIXTURE_PATHS,
    FIXTURE_ROOT,
    FreezeError,
    build_freeze,
    canonical,
    compare_worktree,
    publish_output,
)

SCRIPT = Path(__file__).with_name("m8_freeze_minimal_1k_v3_review.py")


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


def clone_replay_tests(workspace: Path, repo: Path, commit: str, expected: dict) -> None:
    clone = workspace / "full-clone"
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
    check(not alternates.exists() or not alternates.read_bytes().strip(), "clone uses alternates")
    explicit_git(clone, "checkout", "--detach", "--quiet", commit)
    check(explicit_git(clone, "rev-parse", "HEAD").decode("ascii").strip() == commit, "clone checkout differs")
    explicit_git(clone, "fsck", "--full")
    check(explicit_git(clone, "status", "--porcelain=v1") == b"", "clone is dirty")
    replay = build_freeze(commit, repo_root=clone, git_executable=executable)
    check(canonical(replay) == canonical(expected), "clone freeze differs from source")
    check(compare_worktree(replay, clone) == [], "clone worktree differs")
    for item in replay["candidate_files"]:
        object_type = explicit_git(clone, "cat-file", "-t", item["git_blob_oid"])
        check(object_type == b"blob\n", f"clone lacks blob: {item['path']}")


def write_inventory(repo: Path) -> None:
    for index, path in enumerate(DEFAULT_PATHS):
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(f"source:{index}:{path}\n".encode("utf-8"))
    for index, path in enumerate(
        sorted(EXPECTED_FIXTURE_PATHS, key=lambda value: value.encode("utf-8"))
    ):
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(f"fixture:{index}:{path}\n".encode("utf-8"))


def create_repo(root: Path) -> tuple[Path, str]:
    repo = root / "repo"
    repo.mkdir()
    run_git(repo, "init", "--quiet")
    run_git(repo, "config", "core.autocrlf", "false")
    run_git(repo, "config", "core.filemode", "false" if os.name == "nt" else "true")
    write_inventory(repo)
    run_git(repo, "add", "--all")
    if os.name != "nt":
        (repo / ".gitattributes").chmod(0o755)
        run_git(repo, "add", ".gitattributes")
    run_git(repo, "update-index", "--chmod=+x", ".gitattributes")
    run_git(repo, "commit", "--quiet", "-m", "test inventory")
    commit = run_git(repo, "rev-parse", "HEAD").decode("ascii").strip()
    return repo, commit


def independent_fixture_summary(repo: Path) -> dict:
    digest = hashlib.sha256()
    total = 0
    paths = sorted(EXPECTED_FIXTURE_PATHS, key=lambda value: value.encode("utf-8"))
    for path in paths:
        data = (repo / path).read_bytes()
        relative = path.removeprefix(FIXTURE_ROOT + "/").encode("utf-8")
        digest.update(struct.pack(">I", len(relative)))
        digest.update(relative)
        digest.update(struct.pack(">Q", len(data)))
        digest.update(data)
        total += len(data)
    return {
        "algorithm": "fixture-tree-v1",
        "file_count": len(paths),
        "sha256": digest.hexdigest(),
        "total_byte_count": total,
    }


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

        def read(self, _size: int) -> bytes:
            if self.read_once:
                return b""
            self.read_once = True
            return self.data

        def close(self) -> None:
            return None

    class FakeProcess:
        def __init__(self, stdout: bytes, stderr: bytes = b""):
            self.stdout = FakeStream(stdout)
            self.stderr = FakeStream(stderr)
            self.returncode = 0

        def wait(self, timeout: float | None = None) -> int:
            return self.returncode

        def terminate(self) -> None:
            return None

        def kill(self) -> None:
            return None

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
            return self.returncode

        def kill(self) -> None:
            self.kill_calls += 1

    timed_out = TimeoutProcess()
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


def size_limit_tests(repo: Path, commit: str) -> None:
    executable = freeze_module.validate_git_capability()
    prior_identity = freeze_module._GIT_EXECUTABLE_IDENTITY
    freeze_module._GIT_EXECUTABLE_IDENTITY = None
    for stream in ("stdout", "stderr"):
        code = (
            "import sys; "
            f"sys.{stream}.buffer.write(b'x' * 65536); "
            f"sys.{stream}.buffer.flush()"
        )
        with mock.patch.object(freeze_module, "MAX_GIT_OUTPUT_BYTES", 1024):
            expect_error(
                lambda value=code: freeze_module.run_git_process(
                    [sys.executable, "-c", value],
                    ("bounded-output-test",),
                ),
                "Git output exceeds safety limit",
            )
    combined_code = (
        "import sys; "
        "sys.stdout.buffer.write(b'o' * 768); "
        "sys.stdout.buffer.flush(); "
        "sys.stderr.buffer.write(b'e' * 768); "
        "sys.stderr.buffer.flush()"
    )
    with mock.patch.object(freeze_module, "MAX_GIT_OUTPUT_BYTES", 1024):
        expect_error(
            lambda: freeze_module.run_git_process(
                [sys.executable, "-c", combined_code],
                ("combined-output-bound-test",),
            ),
            "Git output exceeds safety limit",
        )
    freeze_module._GIT_EXECUTABLE_IDENTITY = prior_identity

    rewrite_target = repo / DEFAULT_PATHS[0]
    rewrite_original = rewrite_target.read_bytes()
    rewrite_stat = rewrite_target.stat()

    class SameSizeRewriteHandle:
        def __init__(self, handle):
            self.handle = handle

        def __enter__(self):
            self.handle.__enter__()
            return self

        def read(self, size: int) -> bytes:
            chunk = self.handle.read(size)
            if chunk:
                rewrite_target.write_bytes(b"x" * len(rewrite_original))
                os.utime(
                    rewrite_target,
                    ns=(rewrite_stat.st_atime_ns, rewrite_stat.st_mtime_ns),
                )
            return chunk

        def fileno(self) -> int:
            return self.handle.fileno()

        def __exit__(self, exc_type, exc, traceback):
            return self.handle.__exit__(exc_type, exc, traceback)

    real_path_open = Path.open

    def rewriting_open(path: Path, *args, **kwargs):
        handle = real_path_open(path, *args, **kwargs)
        if path == rewrite_target and args and args[0] == "rb":
            return SameSizeRewriteHandle(handle)
        return handle

    try:
        with mock.patch.object(Path, "open", rewriting_open):
            expect_error(
                lambda: freeze_module.read_bounded_worktree_file(
                    rewrite_target,
                    DEFAULT_PATHS[0],
                ),
                "worktree path changed while inspected",
            )
    finally:
        rewrite_target.write_bytes(rewrite_original)
        os.utime(
            rewrite_target,
            ns=(rewrite_stat.st_atime_ns, rewrite_stat.st_mtime_ns),
        )

    with mock.patch.object(freeze_module, "MAX_FILE_BYTES", 0):
        expect_error(
            lambda: freeze_module.read_blob(commit, DEFAULT_PATHS[0], repo),
            "blob exceeds per-file safety limit",
        )
        expect_error(
            lambda: freeze_module.fixture_blobs(commit, repo),
            "blob exceeds per-file safety limit",
        )
        expect_error(
            lambda: freeze_module.read_bounded_worktree_file(
                repo / DEFAULT_PATHS[0],
                DEFAULT_PATHS[0],
            ),
            "worktree file exceeds safety limit",
        )

    first_source_size = (repo / DEFAULT_PATHS[0]).stat().st_size
    first_fixture_size = next(
        (repo / path).stat().st_size
        for path in sorted(freeze_module.EXPECTED_FIXTURE_PATHS)
    )
    aggregate_limit = first_source_size + first_fixture_size - 1
    with mock.patch.object(freeze_module, "MAX_TOTAL_BYTES", aggregate_limit):
        with mock.patch.object(
            freeze_module,
            "verify_blob_oid",
            wraps=freeze_module.verify_blob_oid,
        ) as verify:
            expect_error(
                lambda: build_freeze(commit, repo_root=repo),
                "candidate inventory exceeds total byte safety limit",
            )
            check(
                verify.call_count < freeze_module.EXPECTED_CANDIDATE_FILE_COUNT,
                "aggregate bound was checked only after retaining all blobs",
            )

    with mock.patch.object(freeze_module, "MAX_FIXTURE_TRAVERSAL_ENTRIES", 0):
        expect_error(
            lambda: freeze_module.walk_fixture_files(repo),
            "fixture worktree traversal exceeds entry limit",
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
    with tempfile.TemporaryDirectory(prefix="m8-freeze-test-") as temp:
        workspace = Path(temp)
        capability_failure_tests()
        executable_path_tests(workspace)
        repo, commit = create_repo(workspace)
        size_limit_tests(repo, commit)
        first = build_freeze(commit, repo_root=repo)
        second = build_freeze(commit, repo_root=repo)
        check(canonical(first) == canonical(second), "freeze is not deterministic")
        check(first["source_commit"] == commit, "source commit changed")
        check(first["aggregate"]["file_count"] == 99, "candidate inventory is not 99 files")
        check(len(first["candidate_files"]) == 99, "candidate file list is not 99 files")
        check(
            [item["path"] for item in first["frozen_files"]]
            == sorted(DEFAULT_PATHS, key=lambda value: value.encode("utf-8")),
            "default source inventory differs",
        )
        check(len(first["fixture_files"]) == 90, "fixture inventory is not 90 files")
        check(
            first["fixture_tree"] == independent_fixture_summary(repo),
            "fixture-tree-v1 differs from independent calculation",
        )
        inventory = [*first["frozen_files"], *first["fixture_files"]]
        check(all(len(item["sha256"]) == 64 for item in inventory), "bad SHA-256")
        check(all(len(item["git_blob_oid"]) == 40 for item in inventory), "bad blob OID")
        check(
            {item["git_mode"] for item in inventory} == {"100644", "100755"},
            "Git modes are not frozen",
        )
        check(compare_worktree(first, repo) == [], "clean worktree differs")

        missing_worktree = repo / DEFAULT_PATHS[0]
        missing_worktree_bytes = missing_worktree.read_bytes()
        missing_worktree.unlink()
        check(
            compare_worktree(first, repo)
            == sorted(
                ["<repository-status>", DEFAULT_PATHS[0]],
                key=lambda value: value.encode("utf-8"),
            ),
            "missing worktree file was not reported as divergent",
        )
        missing_worktree.write_bytes(missing_worktree_bytes)

        fsmonitor_marker = workspace / "fsmonitor-invoked"
        fsmonitor_hook = workspace / (
            "fsmonitor.cmd" if os.name == "nt" else "fsmonitor.sh"
        )
        if os.name == "nt":
            fsmonitor_hook.write_text(
                f"@echo off\r\n>\"{fsmonitor_marker}\" echo invoked\r\nexit /b 0\r\n",
                encoding="utf-8",
            )
        else:
            fsmonitor_hook.write_text(
                f"#!/bin/sh\ntouch '{fsmonitor_marker}'\nexit 0\n",
                encoding="utf-8",
            )
            fsmonitor_hook.chmod(0o755)
        run_git(repo, "config", "core.fsmonitor", str(fsmonitor_hook))
        check(compare_worktree(first, repo) == [], "local fsmonitor changed comparison")
        check(not fsmonitor_marker.exists(), "repository core.fsmonitor was executed")
        run_git(repo, "config", "--unset", "core.fsmonitor")

        dirty = repo / DEFAULT_PATHS[1]
        original = dirty.read_bytes()
        dirty.write_bytes(b"dirty worktree\n")
        check(
            canonical(build_freeze(commit, repo_root=repo)) == canonical(first),
            "working-tree bytes affected Git-object freeze",
        )
        check(
            compare_worktree(first, repo)
            == sorted(
                ["<repository-status>", DEFAULT_PATHS[1]],
                key=lambda value: value.encode("utf-8"),
            ),
            "dirty file not found",
        )
        dirty.write_bytes(original)

        fixture = repo / first["fixture_files"][0]["path"]
        fixture_original = fixture.read_bytes()
        fixture.write_bytes(fixture_original + b"changed\n")
        check(
            compare_worktree(first, repo)
            == sorted(
                [
                    "<repository-status>",
                    first["fixture_files"][0]["path"],
                    FIXTURE_ROOT,
                ],
                key=lambda value: value.encode("utf-8"),
            ),
            "fixture divergence or tree digest not found",
        )
        fixture.write_bytes(fixture_original)

        replacement_source = repo / DEFAULT_PATHS[0]
        replacement_original = replacement_source.read_bytes()
        replacement_source.write_bytes(b"replacement content\n")
        run_git(repo, "add", DEFAULT_PATHS[0])
        run_git(repo, "commit", "--quiet", "-m", "replacement target")
        replacement = run_git(repo, "rev-parse", "HEAD").decode("ascii").strip()
        run_git(repo, "replace", commit, replacement)
        check(
            canonical(build_freeze(commit, repo_root=repo)) == canonical(first),
            "replacement ref changed reviewed bytes",
        )
        run_git(repo, "replace", "-d", commit)
        run_git(repo, "reset", "--hard", "--quiet", commit)
        check(replacement_source.read_bytes() == replacement_original, "reset failed")

        empty_repo = workspace / "empty"
        empty_repo.mkdir()
        run_git(empty_repo, "init", "--quiet")
        object_dir = (repo / ".git/objects").resolve()
        prior = os.environ.get("GIT_ALTERNATE_OBJECT_DIRECTORIES")
        os.environ["GIT_ALTERNATE_OBJECT_DIRECTORIES"] = str(object_dir)
        try:
            expect_error(
                lambda: build_freeze(commit, repo_root=empty_repo),
                "commit object cannot be read",
            )
        finally:
            if prior is None:
                os.environ.pop("GIT_ALTERNATE_OBJECT_DIRECTORIES", None)
            else:
                os.environ["GIT_ALTERNATE_OBJECT_DIRECTORIES"] = prior
        alternates = empty_repo / ".git/objects/info/alternates"
        alternates.parent.mkdir(parents=True, exist_ok=True)
        alternates.write_text(str(object_dir) + "\n", encoding="utf-8")
        expect_error(
            lambda: build_freeze(commit, repo_root=empty_repo),
            "object alternates are not allowed",
        )

        expect_error(
            lambda: build_freeze(commit, repo_root=repo / "tools"),
            "exact worktree top level",
        )
        expect_error(
            lambda: build_freeze(commit, repo_root=workspace / "absent"),
            "does not exist",
        )
        non_repo = workspace / "not-repo"
        non_repo.mkdir()
        expect_error(
            lambda: build_freeze(commit, repo_root=non_repo),
            "repository cannot be read",
        )
        expect_error(
            lambda: build_freeze("e397d4d", repo_root=repo),
            "full lowercase 40-hex",
        )
        expect_error(
            lambda: build_freeze("E" * 40, repo_root=repo),
            "full lowercase 40-hex",
        )
        expect_error(
            lambda: build_freeze("0" * 40, repo_root=repo),
            "commit object cannot be read",
        )
        blob = run_git(repo, "rev-parse", f"{commit}:.gitattributes").decode().strip()
        expect_error(
            lambda: build_freeze(blob, repo_root=repo),
            "not commit",
        )
        for custom_paths in (
            ["missing-file.txt"],
            ["docs"],
            [DEFAULT_PATHS[0]] * 2,
            ["../escape"],
            ["C:/escape"],
            [":(glob)x"],
            ["a*b"],
            ["a\\b"],
            [FIXTURE_ROOT],
        ):
            expect_error(
                lambda value=custom_paths: build_freeze(commit, value, repo),
                "custom source inventory is not allowed",
            )

        run_git(repo, "reset", "--hard", "--quiet", commit)
        run_git(repo, "rm", "--quiet", first["fixture_files"][0]["path"])
        missing_commit = make_tree_commit(repo, "missing fixture")
        expect_error(
            lambda: build_freeze(missing_commit, repo_root=repo),
            "fixture members are missing",
        )
        run_git(repo, "reset", "--hard", "--quiet", commit)
        extra = repo / FIXTURE_ROOT / "extra.json"
        extra.write_bytes(b"extra\n")
        run_git(repo, "add", extra.relative_to(repo).as_posix())
        extra_commit = make_tree_commit(repo, "extra fixture")
        expect_error(
            lambda: build_freeze(extra_commit, repo_root=repo),
            "unexpected fixture members",
        )
        run_git(repo, "reset", "--hard", "--quiet", commit)

        symlink_oid = run_git(repo, "hash-object", "-w", "--stdin", stdin=b"target")
        run_git(
            repo,
            "update-index",
            "--add",
            "--cacheinfo",
            f"120000,{symlink_oid.decode('ascii').strip()},{DEFAULT_PATHS[-1]}",
        )
        symlink_commit = make_tree_commit(repo, "symlink source")
        expect_error(
            lambda: build_freeze(symlink_commit, repo_root=repo),
            "not a regular file",
        )
        run_git(repo, "reset", "--hard", "--quiet", commit)

        gitlink_commit_oid = run_git(repo, "rev-parse", "HEAD").decode("ascii").strip()
        run_git(
            repo,
            "update-index",
            "--add",
            "--cacheinfo",
            f"160000,{gitlink_commit_oid},{DEFAULT_PATHS[-1]}",
        )
        gitlink_tree_commit = make_tree_commit(repo, "gitlink source")
        expect_error(
            lambda: build_freeze(gitlink_tree_commit, repo_root=repo),
            "not blob",
        )
        run_git(repo, "reset", "--hard", "--quiet", commit)

        linked = workspace / "linked"
        run_git(repo, "worktree", "add", "--quiet", "--detach", str(linked), commit)
        linked_freeze = build_freeze(commit, repo_root=linked)
        check(canonical(linked_freeze) == canonical(first), "linked worktree freeze differs")
        check(compare_worktree(linked_freeze, linked) == [], "linked worktree comparison differs")

        clone_replay_tests(workspace, repo, commit, first)

        success = cli(repo, commit)
        check(success.returncode == 0, f"CLI success exited {success.returncode}")
        check(success.stdout == canonical(first), "CLI stdout differs")
        check(success.stderr == b"", "CLI success wrote stderr")
        clean = cli(repo, commit, "--compare-worktree")
        check(clean.returncode == 0, "clean comparison did not exit 0")
        clean_freeze = dict(first)
        clean_freeze["worktree_comparison"] = {
            "divergent_paths": [],
            "status": "MATCH",
        }
        check(clean.stdout == canonical(clean_freeze), "comparison stdout differs")
        check(clean.stderr == b"", "comparison wrote stderr")
        bad = cli(repo, "bad")
        check_cli_error(bad, b"full lowercase 40-hex")
        missing_commit_arg = subprocess.run(
            [sys.executable, str(SCRIPT), "--repo", str(repo)],
            cwd=repo.parent,
            env=test_env(),
            capture_output=True,
            check=False,
            timeout=30,
        )
        check_cli_error(missing_commit_arg, b"--commit")
        relative_repo = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--commit",
                commit,
                "--repo",
                repo.name,
            ],
            cwd=repo.parent,
            env=test_env(),
            capture_output=True,
            check=False,
            timeout=30,
        )
        check_cli_error(relative_repo, b"repository path must be absolute")
        relative_git = cli(repo, commit, "--git-executable", "git")
        check_cli_error(relative_git, b"Git executable path must be absolute")
        explicit_success = cli(
            repo,
            commit,
            "--git-executable",
            str(freeze_module.select_git_executable()),
        )
        check(explicit_success.returncode == 0, "explicit Git CLI failed")
        check(explicit_success.stdout == canonical(first), "explicit Git freeze differs")

        fake_path = workspace / "fake-path"
        fake_path.mkdir()
        marker = workspace / "path-git-invoked"
        if os.name == "nt":
            write_git_shim(fake_path, f">\"{marker}\" echo invoked\r\nexit /b 99")
        else:
            write_git_shim(fake_path, f"touch '{marker}'\nexit 99")
        hostile_env = test_env()
        hostile_env["PATH"] = str(fake_path) + os.pathsep + hostile_env.get("PATH", "")
        hostile = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--commit",
                commit,
                "--repo",
                str(repo),
            ],
            cwd=repo.parent,
            env=hostile_env,
            capture_output=True,
            check=False,
            timeout=30,
        )
        check(hostile.returncode == 0, "PATH shim affected trusted Git selection")
        check(not marker.exists(), "PATH Git shim was invoked")

        publication_failure_tests(workspace)

        dirty.write_bytes(b"dirty again\n")
        divergent = cli(repo, commit, "--compare-worktree")
        check(divergent.returncode == 3, "divergence did not exit 3")
        divergent_freeze = dict(first)
        divergent_freeze["worktree_comparison"] = {
            "divergent_paths": sorted(
                ["<repository-status>", DEFAULT_PATHS[1]],
                key=lambda value: value.encode("utf-8"),
            ),
            "status": "DIVERGENT",
        }
        check(
            divergent.stdout == canonical(divergent_freeze),
            "divergence omitted freeze bytes",
        )
        output = workspace / "freeze.json"
        output.write_bytes(b"sentinel\n")
        divergent_output = cli(
            repo,
            commit,
            "--compare-worktree",
            "--output",
            str(output),
        )
        check(divergent_output.returncode == 3, "output divergence did not exit 3")
        check(
            output.read_bytes() == b"sentinel\n",
            "divergent comparison changed output",
        )
        dirty.write_bytes(original)

        in_repo_output = repo / "freeze.json"
        in_repo = cli(repo, commit, "--output", str(in_repo_output))
        check(in_repo.returncode == 2, "in-repository output did not exit 2")
        check(b"output path must be outside repository" in in_repo.stderr, "wrong in-repository output error")
        check(not in_repo_output.exists(), "in-repository output was published")

        collision_before = (repo / DEFAULT_PATHS[0]).read_bytes()
        collision = cli(repo, commit, "--output", str(repo / DEFAULT_PATHS[0]))
        check(collision.returncode == 2, "inventory output collision did not exit 2")
        check(
            (repo / DEFAULT_PATHS[0]).read_bytes() == collision_before,
            "inventory output collision changed source",
        )
        check(
            not list(workspace.glob(".freeze.json.*")),
            "temporary output file leaked",
        )

    print("ALL PASS: hermetic Git-object freeze and CLI checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
