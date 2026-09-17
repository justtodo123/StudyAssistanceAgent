#!/usr/bin/env python3
"""Hermetic tests for the v3 input generator.

Only explicit ``test-only`` tiny generation is exercised.  Formal generation is
never invoked; its exact-version preflight rejection is tested separately.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import stat
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest import mock

import m8_generate_minimal_1k_input_v3 as generator


class GeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _tree_bytes(self, path: Path) -> dict[str, bytes]:
        return {str(item.relative_to(path)): item.read_bytes() for item in sorted(path.rglob("*")) if item.is_file()}

    def _persisted_fixture(
        self,
        name: str,
        *,
        chunk_count: int = 8,
        dimension: int = 3,
    ) -> tuple[Path, Path, Path, int]:
        target = self.root / name
        generator.generate(
            target,
            "test-only",
            chunk_count=chunk_count,
            dimension=dimension,
        )
        input_dir = target / "input"
        return (
            input_dir / "chunks.jsonl",
            input_dir / "queries.jsonl",
            input_dir / "vectors.bin",
            dimension,
        )

    def _records(self, path: Path) -> list[dict]:
        return [json.loads(line) for line in path.read_bytes().splitlines()]

    def _write_records(self, path: Path, records: list[dict]) -> None:
        path.write_bytes(b"".join(generator.canonical_json(record) for record in records))

    def test_tiny_generation_is_deterministic_and_canonical(self) -> None:
        left = self.root / "left"
        right = self.root / "right"
        generator.generate(left, "test-only", chunk_count=12, dimension=7, seed=generator.FORMAL_SEED, perturb_seed=generator.FORMAL_PERTURBATION_SEED)
        generator.generate(right, "test-only", chunk_count=12, dimension=7, seed=generator.FORMAL_SEED, perturb_seed=generator.FORMAL_PERTURBATION_SEED)
        self.assertEqual(self._tree_bytes(left), self._tree_bytes(right))
        manifest = json.loads((left / "manifest.json").read_text(encoding="utf-8"))
        self.assertFalse(manifest["formal_identity"])
        self.assertEqual(manifest["seed"], generator.FORMAL_SEED)
        self.assertEqual(manifest["perturbation_seed"], generator.FORMAL_PERTURBATION_SEED)
        for name in ("chunks.jsonl", "queries.jsonl", "gold.jsonl"):
            data = (left / "input" / name).read_bytes()
            self.assertTrue(data.endswith(b"\n"))
            for line in data.splitlines(keepends=True):
                self.assertEqual(line, generator.canonical_json(json.loads(line)))
        vectors = (left / "input" / "vectors.bin").read_bytes()
        self.assertEqual(len(vectors), 12 * 7 * 4)

    def test_contract_records_filters_and_persisted_gold(self) -> None:
        target = self.root / "contract"
        generator.generate(target, "test-only", chunk_count=120, dimension=7)
        chunks = [json.loads(line) for line in (target / "input/chunks.jsonl").read_bytes().splitlines()]
        queries = [json.loads(line) for line in (target / "input/queries.jsonl").read_bytes().splitlines()]
        gold = [json.loads(line) for line in (target / "input/gold.jsonl").read_bytes().splitlines()]
        self.assertEqual(
            set(chunks[0]),
            {"chunk_id", "filter_label", "generation", "ordinal", "owner_id", "published", "snapshot", "source_id", "tombstone", "vector_byte_length", "vector_byte_offset"},
        )
        self.assertTrue(chunks[100]["tombstone"])
        self.assertFalse(chunks[101]["published"])
        self.assertEqual(chunks[102]["generation"], "generation-mismatch")
        self.assertEqual(chunks[103]["snapshot"], "snapshot-mismatch")
        self.assertEqual(set(queries[0]), {"filter", "query_id", "query_type", "target_chunk_id", "vector_f32_le_base64"})
        self.assertEqual(queries[25]["target_chunk_id"], "m8-s00-00025")
        self.assertEqual(len(base64.b64decode(queries[25]["vector_f32_le_base64"], validate=True)), 7 * 4)
        self.assertEqual(set(gold[0]), {"gold_by_k", "query_id"})
        self.assertEqual(set(gold[0]["gold_by_k"]), {"1", "3", "5"})
        self.assertEqual(gold[-1]["gold_by_k"], {"1": [], "3": [], "5": []})


    def test_persisted_gold_rejects_semantic_and_canonical_mutations(self) -> None:
        expected_codes = {
            "altered-entry": "GOLD_RECOMPUTATION_MISMATCH",
            "wrong-order": "GOLD_RECOMPUTATION_MISMATCH",
            "extra-key": "INVALID_GOLD_RECORD",
            "missing-key": "INVALID_GOLD_RECORD",
            "wrong-k-set": "INVALID_GOLD_RECORD",
            "noncanonical": "NONCANONICAL_JSONL",
        }
        for name, expected_code in expected_codes.items():
            with self.subTest(name=name):
                target = self.root / f"gold-{name}"
                generator.generate(
                    target,
                    "test-only",
                    chunk_count=8,
                    dimension=3,
                )
                gold_path = target / "input/gold.jsonl"
                records = self._records(gold_path)
                expected = json.loads(json.dumps(records))
                if name == "altered-entry":
                    records[0]["gold_by_k"]["1"] = []
                elif name == "wrong-order":
                    records[0], records[1] = records[1], records[0]
                elif name == "extra-key":
                    records[0]["unexpected"] = True
                elif name == "missing-key":
                    del records[0]["query_id"]
                elif name == "wrong-k-set":
                    records[0]["gold_by_k"]["2"] = records[0]["gold_by_k"].pop("3")
                else:
                    gold_path.write_bytes(
                        gold_path.read_bytes().replace(b'{"gold_by_k"', b'{ "gold_by_k"', 1)
                    )
                if name != "noncanonical":
                    self._write_records(gold_path, records)
                with self.assertRaises(generator.GeneratorError) as caught:
                    generator._load_persisted_gold(gold_path, expected)
                self.assertEqual(caught.exception.code, expected_code)

    def test_persisted_jsonl_rejects_invalid_framing_and_json(self) -> None:
        cases = (
            ("missing-final-lf", lambda data: data[:-1], "NONCANONICAL_JSONL"),
            ("crlf", lambda data: data.replace(b"\n", b"\r\n", 1), "NONCANONICAL_JSONL"),
            ("noncanonical", lambda data: data.replace(b'{"chunk_id"', b'{ "chunk_id"', 1), "NONCANONICAL_JSONL"),
            ("duplicate-key", lambda data: data.replace(b'{"chunk_id":', b'{"chunk_id":"duplicate","chunk_id":', 1), "INVALID_JSONL"),
            ("nonfinite", lambda data: data.replace(b'"ordinal":0', b'"ordinal":NaN', 1), "INVALID_JSONL"),
        )
        for name, mutate, expected_code in cases:
            with self.subTest(name=name):
                chunks_path, queries_path, vectors_path, dimension = self._persisted_fixture(name)
                chunks_path.write_bytes(mutate(chunks_path.read_bytes()))
                with self.assertRaises(generator.GeneratorError) as caught:
                    generator._gold_from_persisted(chunks_path, queries_path, vectors_path, dimension)
                self.assertEqual(caught.exception.code, expected_code)

    def test_persisted_records_reject_closed_shape_duplicates_and_layout(self) -> None:
        cases = ("unexpected-key", "INVALID_CHUNK_RECORD", "duplicate-id", "DUPLICATE_CHUNK_ID", "wrong-offset", "INVALID_CHUNK_LAYOUT")
        for name, expected_code in zip(cases[::2], cases[1::2]):
            with self.subTest(name=name):
                chunks_path, queries_path, vectors_path, dimension = self._persisted_fixture(name)
                chunks = self._records(chunks_path)
                if name == "unexpected-key":
                    chunks[0]["unexpected"] = True
                elif name == "duplicate-id":
                    chunks[1]["chunk_id"] = chunks[0]["chunk_id"]
                else:
                    chunks[1]["vector_byte_offset"] += 4
                self._write_records(chunks_path, chunks)
                with self.assertRaises(generator.GeneratorError) as caught:
                    generator._gold_from_persisted(chunks_path, queries_path, vectors_path, dimension)
                self.assertEqual(caught.exception.code, expected_code)

    def test_persisted_queries_reject_ids_targets_and_vector_encodings(self) -> None:
        cases = (
            "unexpected-key",
            "INVALID_QUERY_RECORD",
            "duplicate-id",
            "DUPLICATE_QUERY_ID",
            "unknown-target",
            "UNKNOWN_TARGET_CHUNK",
            "malformed-base64",
            "INVALID_QUERY_VECTOR",
            "noncanonical-base64",
            "INVALID_QUERY_VECTOR",
            "wrong-byte-length",
            "INVALID_QUERY_VECTOR",
            "nonfinite-vector",
            "INVALID_QUERY_VECTOR",
        )
        for name, expected_code in zip(cases[::2], cases[1::2]):
            with self.subTest(name=name):
                chunks_path, queries_path, vectors_path, dimension = self._persisted_fixture(name)
                queries = self._records(queries_path)
                if name == "unexpected-key":
                    queries[0]["unexpected"] = True
                elif name == "duplicate-id":
                    queries[1]["query_id"] = queries[0]["query_id"]
                elif name == "unknown-target":
                    queries[0]["target_chunk_id"] = "missing-chunk"
                elif name == "malformed-base64":
                    queries[0]["vector_f32_le_base64"] = "!not-base64!"
                elif name == "noncanonical-base64":
                    encoded = queries[0]["vector_f32_le_base64"]
                    queries[0]["vector_f32_le_base64"] = encoded + "="
                elif name == "wrong-byte-length":
                    queries[0]["vector_f32_le_base64"] = base64.b64encode(b"\x00" * 4).decode("ascii")
                else:
                    queries[0]["vector_f32_le_base64"] = base64.b64encode(
                        generator.np.full(dimension, generator.np.nan, dtype="<f4").tobytes()
                    ).decode("ascii")
                self._write_records(queries_path, queries)
                with self.assertRaises(generator.GeneratorError) as caught:
                    generator._gold_from_persisted(chunks_path, queries_path, vectors_path, dimension)
                self.assertEqual(caught.exception.code, expected_code)

    def test_persisted_vectors_reject_wrong_length_and_nonfinite_values(self) -> None:
        for name, mutation, expected_code in (
            ("wrong-vector-length", lambda data: data[:-4], "VECTOR_BYTE_COUNT_MISMATCH"),
            (
                "nonfinite-vector",
                lambda data: generator.np.asarray([generator.np.inf], dtype="<f4").tobytes() + data[4:],
                "INVALID_VECTOR",
            ),
        ):
            with self.subTest(name=name):
                chunks_path, queries_path, vectors_path, dimension = self._persisted_fixture(name)
                vectors_path.write_bytes(mutation(vectors_path.read_bytes()))
                with self.assertRaises(generator.GeneratorError) as caught:
                    generator._gold_from_persisted(chunks_path, queries_path, vectors_path, dimension)
                self.assertEqual(caught.exception.code, expected_code)

    def test_persisted_vectors_and_queries_reject_norm_drift(self) -> None:
        chunks_path, queries_path, vectors_path, dimension = self._persisted_fixture(
            "vector-norm-drift"
        )
        vectors = generator.np.frombuffer(
            vectors_path.read_bytes(), dtype="<f4"
        ).copy()
        vectors[:dimension] *= generator.np.float32(0.5)
        vectors_path.write_bytes(vectors.tobytes())
        with self.assertRaises(generator.GeneratorError) as caught:
            generator._gold_from_persisted(
                chunks_path,
                queries_path,
                vectors_path,
                dimension,
            )
        self.assertEqual(caught.exception.code, "VECTOR_NORMALIZATION_ERROR")

        chunks_path, queries_path, vectors_path, dimension = self._persisted_fixture(
            "query-norm-drift"
        )
        queries = self._records(queries_path)
        raw = bytearray(
            base64.b64decode(
                queries[0]["vector_f32_le_base64"],
                validate=True,
            )
        )
        values = generator.np.frombuffer(raw, dtype="<f4").copy()
        values *= generator.np.float32(0.5)
        queries[0]["vector_f32_le_base64"] = base64.b64encode(
            values.tobytes()
        ).decode("ascii")
        self._write_records(queries_path, queries)
        with self.assertRaises(generator.GeneratorError) as caught:
            generator._gold_from_persisted(
                chunks_path,
                queries_path,
                vectors_path,
                dimension,
            )
        self.assertEqual(caught.exception.code, "QUERY_NORMALIZATION_ERROR")

    def test_formal_semantic_closure_rejects_persisted_mutations(self) -> None:
        root = self.root / "formal-semantic"
        root.mkdir()
        input_dir = root / "input"
        input_dir.mkdir()
        vectors, perturbed = generator._make_vectors(
            generator.FORMAL_CHUNK_COUNT,
            generator.FORMAL_DIMENSION,
            generator.FORMAL_SEED,
            generator.FORMAL_PERTURBATION_SEED,
        )
        chunks_path = input_dir / "chunks.jsonl"
        queries_path = input_dir / "queries.jsonl"
        vectors_path = input_dir / "vectors.bin"
        generator._write_jsonl(
            chunks_path,
            generator._chunk_records(
                generator.FORMAL_CHUNK_COUNT,
                generator.FORMAL_DIMENSION,
            ),
        )
        generator._write_jsonl(
            queries_path,
            generator._query_records(
                vectors,
                perturbed,
                generator.FORMAL_CHUNK_COUNT,
                generator.FORMAL_DIMENSION,
            ),
        )
        vectors_path.write_bytes(vectors.tobytes(order="C"))
        gold = generator._gold_from_persisted(
            chunks_path,
            queries_path,
            vectors_path,
            generator.FORMAL_DIMENSION,
            formal_contract=True,
        )
        self.assertEqual(len(gold), generator.FORMAL_QUERY_COUNT)

        chunks = self._records(chunks_path)
        chunks[100]["tombstone"] = False
        self._write_records(chunks_path, chunks)
        with self.assertRaises(generator.GeneratorError) as caught:
            generator._gold_from_persisted(
                chunks_path,
                queries_path,
                vectors_path,
                generator.FORMAL_DIMENSION,
                formal_contract=True,
            )
        self.assertEqual(caught.exception.code, "INVALID_FORMAL_CHUNK")

        generator._write_jsonl(
            chunks_path,
            generator._chunk_records(
                generator.FORMAL_CHUNK_COUNT,
                generator.FORMAL_DIMENSION,
            ),
        )
        queries = self._records(queries_path)
        queries[75]["filter"]["owner_id"] = "owner-00"
        self._write_records(queries_path, queries)
        with self.assertRaises(generator.GeneratorError) as caught:
            generator._gold_from_persisted(
                chunks_path,
                queries_path,
                vectors_path,
                generator.FORMAL_DIMENSION,
                formal_contract=True,
            )
        self.assertEqual(caught.exception.code, "INVALID_FORMAL_QUERY")

        generator._write_jsonl(
            queries_path,
            generator._query_records(
                vectors,
                perturbed,
                generator.FORMAL_CHUNK_COUNT,
                generator.FORMAL_DIMENSION,
            ),
        )
        mutated_vectors = vectors.copy()
        mutated_vectors[[0, 1]] = mutated_vectors[[1, 0]]
        vectors_path.write_bytes(mutated_vectors.tobytes(order="C"))
        with self.assertRaises(generator.GeneratorError) as caught:
            generator._gold_from_persisted(
                chunks_path,
                queries_path,
                vectors_path,
                generator.FORMAL_DIMENSION,
                formal_contract=True,
            )
        self.assertEqual(caught.exception.code, "INVALID_FORMAL_VECTOR")

    def test_persisted_gold_breaks_equal_scores_by_utf8_chunk_id(self) -> None:
        chunks_path, queries_path, vectors_path, dimension = self._persisted_fixture(
            "tie-break",
            chunk_count=3,
            dimension=2,
        )
        chunks = self._records(chunks_path)
        chunks[0]["chunk_id"] = "z-chunk"
        chunks[1]["chunk_id"] = "ä-chunk"
        chunks[2]["chunk_id"] = "a-chunk"
        self._write_records(chunks_path, chunks)
        queries = self._records(queries_path)
        queries = [queries[0]]
        queries[0]["target_chunk_id"] = "z-chunk"
        self._write_records(queries_path, queries)
        tied = generator.np.asarray([[1.0, 0.0]] * 3, dtype="<f4")
        vectors_path.write_bytes(tied.tobytes(order="C"))
        query_raw = tied[0].tobytes(order="C")
        queries[0]["vector_f32_le_base64"] = base64.b64encode(query_raw).decode("ascii")
        self._write_records(queries_path, queries)
        gold = generator._gold_from_persisted(chunks_path, queries_path, vectors_path, dimension)
        self.assertEqual(gold[0]["gold_by_k"]["3"], ["a-chunk", "z-chunk", "ä-chunk"])

    def test_normalization_rejects_non_contiguous_working_matrix(self) -> None:
        rows = generator.np.ones((3, 4), dtype=generator.np.float64)[:, ::2]
        self.assertFalse(rows.flags.c_contiguous)
        with self.assertRaises(generator.GeneratorError) as caught:
            generator._normalize(rows)
        self.assertEqual(caught.exception.code, "INVALID_VECTOR_LAYOUT")

    def test_exact_numpy_version_is_required_before_formal_work(self) -> None:
        target = self.root / "formal"
        with mock.patch.object(
            generator,
            "_validate_formal_authorization",
            return_value={
                "normalization_tolerance": generator.NORMALIZATION_TOLERANCE,
                "numpy_version": generator.FORMAL_NUMPY_VERSION,
                "parent_identity": {
                    "canonical_path": str(self.root).replace("\\", "/"),
                    "st_dev": self.root.stat().st_dev,
                    "st_ino": self.root.stat().st_ino,
                },
            },
        ):
            with self.assertRaises(generator.GeneratorError) as caught:
                generator.preflight(
                    target,
                    "formal",
                    numpy_version="0.0.0",
                    authorization=generator.FormalAuthorization(
                        s0_path=self.root / "s0.json",
                        s1_path=self.root / "s1.json",
                        environment_path=self.root / "environment.json",
                        config_path=self.root / "config.json",
                        observer_config_path=self.root / "observer-config.json",
                        redaction_registry_path=self.root / "redaction-registry.json",
                        preflight_path=self.root / "preflight.json",
                        preflight_result_path=self.root / "preflight-result.json",
                    ),
                )
        self.assertEqual(caught.exception.code, "NUMPY_VERSION_MISMATCH")
        self.assertFalse(target.exists())

    def test_formal_preflight_rejects_live_parent_identity_mismatch(self) -> None:
        target = self.root / "formal-parent-mismatch"
        authorization = generator.FormalAuthorization(
            s0_path=self.root / "s0.json",
            s1_path=self.root / "s1.json",
            environment_path=self.root / "environment.json",
            config_path=self.root / "config.json",
            observer_config_path=self.root / "observer-config.json",
            redaction_registry_path=self.root / "redaction-registry.json",
            preflight_path=self.root / "preflight.json",
            preflight_result_path=self.root / "preflight-result.json",
        )
        with mock.patch.object(
            generator,
            "_validate_formal_authorization",
            return_value={
                "normalization_tolerance": generator.NORMALIZATION_TOLERANCE,
                "numpy_version": generator.FORMAL_NUMPY_VERSION,
                "parent_identity": {
                    "canonical_path": str(self.root).replace("\\", "/"),
                    "st_dev": self.root.stat().st_dev,
                    "st_ino": self.root.stat().st_ino + 1,
                },
            },
        ):
            with self.assertRaises(generator.GeneratorError) as caught:
                generator.preflight(
                    target,
                    "formal",
                    numpy_version=generator.FORMAL_NUMPY_VERSION,
                    authorization=authorization,
                )
        self.assertEqual(
            caught.exception.code,
            "FORMAL_OUTPUT_PARENT_MISMATCH",
        )
        self.assertFalse(target.exists())

    def test_formal_mode_requires_authorization_before_filesystem_inspection(self) -> None:
        target = self.root / "missing-parent" / "formal"
        with mock.patch.object(
            generator,
            "_inspect_output_path",
        ) as inspect_output, mock.patch.object(
            generator.tempfile,
            "mkdtemp",
        ) as make_staging:
            with self.assertRaises(generator.GeneratorError) as caught:
                generator.generate(target, "formal")
        self.assertEqual(caught.exception.code, "FORMAL_AUTHORIZATION_REQUIRED")
        inspect_output.assert_not_called()
        make_staging.assert_not_called()
        self.assertFalse(target.exists())

    def test_defaults_are_non_authoritative_test_only(self) -> None:
        args = generator.parse_args(["--output-root", str(self.root / "default")])
        self.assertEqual(args.mode, "test-only")
        with self.assertRaises(generator.GeneratorError) as caught:
            generator.generate(self.root / "implicit")
        self.assertEqual(caught.exception.code, "TEST_SIZE_REQUIRED")
        self.assertFalse((self.root / "implicit").exists())


    def test_cli_formal_authorization_requires_all_artifacts(self) -> None:
        args = generator.parse_args(
            [
                "--output-root",
                str(self.root / "formal"),
                "--mode",
                "formal",
                "--s0",
                str(self.root / "s0.json"),
            ]
        )
        with self.assertRaises(generator.GeneratorError) as caught:
            generator._authorization_from_args(args)
        self.assertEqual(caught.exception.code, "FORMAL_AUTHORIZATION_INCOMPLETE")

    def test_test_only_rejects_authorization_material(self) -> None:
        authorization = generator.FormalAuthorization(
            s0_path=self.root / "s0.json",
            s1_path=self.root / "s1.json",
            environment_path=self.root / "environment.json",
            config_path=self.root / "config.json",
            observer_config_path=self.root / "observer-config.json",
            redaction_registry_path=self.root / "redaction-registry.json",
            preflight_path=self.root / "preflight.json",
            preflight_result_path=self.root / "preflight-result.json",
        )
        with self.assertRaises(generator.GeneratorError) as caught:
            generator.preflight(
                self.root / "tiny",
                "test-only",
                authorization=authorization,
            )
        self.assertEqual(caught.exception.code, "TEST_AUTHORIZATION_FORBIDDEN")
        self.assertFalse((self.root / "tiny").exists())

    def test_publication_revalidates_parent_identity(self) -> None:
        target = self.root / "changed-parent"
        with mock.patch.object(
            generator,
            "_revalidate_publication",
            side_effect=generator.GeneratorError(
                "OUTPUT_PARENT_CHANGED",
                "changed",
            ),
        ):
            with self.assertRaises(generator.GeneratorError) as caught:
                generator.generate(
                    target,
                    "test-only",
                    chunk_count=2,
                    dimension=2,
                )
        self.assertEqual(caught.exception.code, "OUTPUT_PARENT_CHANGED")
        self.assertFalse(target.exists())
        self.assertEqual(list(self.root.glob(".changed-parent.staging-*")), [])

    def test_test_only_cannot_claim_formal_identity(self) -> None:
        target = self.root / "tiny"
        result = generator.generate(target, "test-only", chunk_count=3, dimension=4)
        self.assertFalse(result["formal_identity"])
        manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
        self.assertFalse(manifest["formal_identity"])
        self.assertEqual(manifest["chunk_count"], 3)
        self.assertNotEqual(manifest["chunk_count"], generator.FORMAL_CHUNK_COUNT)

    def test_seed_changes_output_and_same_seed_replays(self) -> None:
        one = self.root / "one"
        two = self.root / "two"
        three = self.root / "three"
        generator.generate(one, "test-only", chunk_count=8, dimension=5, seed=1, perturb_seed=2)
        generator.generate(two, "test-only", chunk_count=8, dimension=5, seed=1, perturb_seed=2)
        generator.generate(three, "test-only", chunk_count=8, dimension=5, seed=3, perturb_seed=4)
        self.assertEqual(self._tree_bytes(one), self._tree_bytes(two))
        self.assertNotEqual((one / "input/vectors.bin").read_bytes(), (three / "input/vectors.bin").read_bytes())

    def test_manifest_members_match_actual_bytes_and_counts(self) -> None:
        target = self.root / "tiny"
        generator.generate(target, "test-only", chunk_count=5, dimension=3)
        manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
        for member in manifest["members"]:
            data = (target / member["path"]).read_bytes()
            self.assertEqual(member["byte_count"], len(data))
            self.assertEqual(member["sha256"], hashlib.sha256(data).hexdigest())
            expected = {
                "input/chunks.jsonl": 5,
                "input/queries.jsonl": 20,
                "input/gold.jsonl": 20,
                "input/vectors.bin": 5,
            }[member["path"]]
            self.assertEqual(member["record_count"], expected)

    def test_preflight_rejects_relative_root_and_existing_roots(self) -> None:
        with self.assertRaises(generator.GeneratorError) as relative:
            generator.preflight(Path("relative-root"), "test-only")
        self.assertEqual(relative.exception.code, "OUTPUT_ROOT_NOT_ABSOLUTE")

        empty = self.root / "existing-empty"
        empty.mkdir()
        with self.assertRaises(generator.GeneratorError) as existing_empty:
            generator.preflight(empty, "test-only")
        self.assertEqual(existing_empty.exception.code, "OUTPUT_ROOT_EXISTS")
        self.assertEqual(list(empty.iterdir()), [])

        nonempty = self.root / "existing-nonempty"
        nonempty.mkdir()
        (nonempty / "sentinel").write_text("keep", encoding="utf-8")
        with self.assertRaises(generator.GeneratorError) as existing_nonempty:
            generator.preflight(nonempty, "test-only")
        self.assertEqual(existing_nonempty.exception.code, "OUTPUT_ROOT_EXISTS")
        self.assertEqual(
            (nonempty / "sentinel").read_text(encoding="utf-8"),
            "keep",
        )

    def test_invalid_test_size_fails_without_publish(self) -> None:
        target = self.root / "invalid"
        with self.assertRaises(generator.GeneratorError) as caught:
            generator.generate(target, "test-only", chunk_count=0, dimension=3)
        self.assertEqual(caught.exception.code, "TEST_SIZE_REQUIRED")
        self.assertFalse(target.exists())

    def test_atomic_failure_removes_staging_and_publishes_nothing(self) -> None:
        target = self.root / "failure"
        with mock.patch.object(generator, "_build_tree", side_effect=generator.GeneratorError("MOCK_FAILURE", "mocked")):
            with self.assertRaises(generator.GeneratorError) as caught:
                generator.generate(target, "test-only", chunk_count=2, dimension=2)
        self.assertEqual(caught.exception.code, "MOCK_FAILURE")
        self.assertFalse(target.exists())
        self.assertEqual(list(self.root.glob(".failure.staging-*")), [])

    def test_unwritable_or_missing_parent_is_rejected(self) -> None:
        missing_parent = self.root / "missing" / "out"
        with self.assertRaises(generator.GeneratorError) as caught:
            generator.preflight(missing_parent, "test-only")
        self.assertEqual(caught.exception.code, "OUTPUT_PARENT_MISSING")

    def test_no_network_or_external_material_access(self) -> None:
        target = self.root / "offline"
        with mock.patch("socket.socket", side_effect=AssertionError("network access")):
            generator.generate(target, "test-only", chunk_count=2, dimension=2)
        self.assertTrue((target / "manifest.json").exists())
        source = Path(generator.__file__).read_text(encoding="utf-8")
        self.assertNotIn("111_Others_Subjects", source)
        self.assertNotIn("requests", source)
        self.assertNotIn("urllib", source)

    def test_cli_error_is_machine_readable(self) -> None:
        target = self.root / "formal"
        stderr = StringIO()
        with mock.patch.object(
            generator, "generate", side_effect=generator.GeneratorError("TEST_CODE", "controlled", detail="x")
        ):
            with redirect_stderr(stderr):
                with mock.patch(
                    "sys.argv", ["generator", "--output-root", str(target), "--mode", "test-only"]
                ):
                    self.assertEqual(generator.main(), 2)
        payload = json.loads(stderr.getvalue())
        self.assertEqual(payload["error"]["code"], "TEST_CODE")
        self.assertEqual(payload["error"]["message"], "controlled")
        self.assertEqual(payload["error"]["detail"], "x")
        self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
