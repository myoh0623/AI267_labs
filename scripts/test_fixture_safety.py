#!/usr/bin/env python3
"""Regression checks for destructive fixture cleanup guards."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "ai267_s3_fixture", ROOT / "tasks" / "common" / "s3_fixture.py"
)
assert SPEC and SPEC.loader
S3 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(S3)


class OwnedBucketCleanupTests(unittest.TestCase):
    def token_file(self, content: bytes = b"random-owner-token\n"):
        temporary = tempfile.TemporaryDirectory()
        path = Path(temporary.name) / "owner.token"
        path.write_bytes(content)
        return temporary, path

    def test_missing_bucket_is_already_clean(self) -> None:
        temporary, token = self.token_file()
        self.addCleanup(temporary.cleanup)
        with (
            mock.patch.object(S3, "bucket_exists", return_value=False),
            mock.patch.object(S3, "signed_request") as request,
        ):
            S3.delete_owned_bucket("fixture", ".owner", str(token))
        request.assert_not_called()

    def test_missing_or_wrong_owner_never_deletes(self) -> None:
        temporary, token = self.token_file()
        self.addCleanup(temporary.cleanup)
        for response in ((404, b"missing"), (200, b"different")):
            with self.subTest(response=response):
                with (
                    mock.patch.object(S3, "bucket_exists", return_value=True),
                    mock.patch.object(
                        S3, "signed_request", return_value=response
                    ) as request,
                    mock.patch.object(S3, "list_keys") as list_keys,
                ):
                    with self.assertRaises(SystemExit):
                        S3.delete_owned_bucket("fixture", ".owner", str(token))
                    list_keys.assert_not_called()
                    self.assertFalse(
                        any(
                            call.args[0] == "DELETE"
                            for call in request.call_args_list
                        )
                    )

    def test_matching_owner_deletes_objects_then_bucket(self) -> None:
        temporary, token = self.token_file()
        self.addCleanup(temporary.cleanup)
        expected = token.read_bytes()

        def request(method, bucket, key="", **_kwargs):
            if method == "GET":
                self.assertEqual((bucket, key), ("fixture", ".owner"))
                return 200, expected
            self.assertEqual(method, "DELETE")
            return 204, b""

        with (
            mock.patch.object(S3, "bucket_exists", return_value=True),
            mock.patch.object(S3, "list_keys", return_value=[".owner", "answer.bin"]),
            mock.patch.object(S3, "signed_request", side_effect=request) as signed,
        ):
            S3.delete_owned_bucket("fixture", ".owner", str(token))

        self.assertEqual(
            [call.args for call in signed.call_args_list],
            [
                ("GET", "fixture", ".owner"),
                ("DELETE", "fixture", ".owner"),
                ("DELETE", "fixture", "answer.bin"),
                ("DELETE", "fixture"),
            ],
        )


class ScriptGuardTests(unittest.TestCase):
    def test_task10_recursive_delete_has_exact_sentinel_guard(self) -> None:
        setup = (ROOT / "tasks/10-kubeflow-pipeline/setup.sh").read_text()
        cleanup = (ROOT / "tasks/10-kubeflow-pipeline/cleanup.sh").read_text()
        readme = (ROOT / "tasks/10-kubeflow-pipeline/README.md").read_text()
        self.assertIn('printf \'task-10\\n\' > "${VENV_OWNER_FILE}"', setup)
        self.assertIn("uv venv --allow-existing --python 3.13", readme)
        guard = cleanup.index('!= task-10')
        deletion = cleanup.index('rm -rf -- "${VENV_DIR}"')
        self.assertLess(guard, deletion)

    def test_task_created_s3_buckets_use_owned_delete(self) -> None:
        for task in (
            "08-s3-model",
            "09-openvino-serving",
            "11-pipeline-server",
        ):
            with self.subTest(task=task):
                setup = (ROOT / "tasks" / task / "setup.sh").read_text()
                cleanup = (ROOT / "tasks" / task / "cleanup.sh").read_text()
                self.assertIn("bucket-owner.token", setup)
                self.assertIn("delete-owned-bucket", cleanup)
                self.assertNotIn("purge-bucket", cleanup)


if __name__ == "__main__":
    unittest.main()
