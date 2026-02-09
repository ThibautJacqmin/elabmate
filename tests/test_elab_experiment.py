# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import time
import urllib3
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ElabClient import ElabClient
from Exceptions import InvalidCategory, InvalidStatus


path_to_conf_file = 'C:/Users/ThibautJacqmin/Documents/Lkb/Elab API key'
CONFIG_PATH = path_to_conf_file + '/elab_server.conf'


class TestElabExperimentIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        print("[setup] Initializing Elab client...")
        cls.client = ElabClient(CONFIG_PATH)
        token = uuid.uuid4().hex[:8]
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        cls.token = f"{timestamp}-{token}"
        print(f"[setup] Test token: {cls.token}")

        categories = cls.client.category_dict
        statuses = cls.client.status_dict
        if not categories:
            raise AssertionError("No category available on server to run integration test.")
        if not statuses:
            raise AssertionError("No status available on server to run integration test.")

        requested_category = os.getenv("ELAB_TEST_CATEGORY")
        requested_status = os.getenv("ELAB_TEST_STATUS")

        if requested_category:
            if requested_category not in categories:
                raise AssertionError(f"ELAB_TEST_CATEGORY '{requested_category}' does not exist.")
            cls.category_name = requested_category
            print(f"[setup] Using requested category: {cls.category_name}")
        else:
            cls.category_name = next(iter(categories))
            print(f"[setup] Using first available category: {cls.category_name}")

        if requested_status:
            if requested_status not in statuses:
                raise AssertionError(f"ELAB_TEST_STATUS '{requested_status}' does not exist.")
            cls.status_name = requested_status
            print(f"[setup] Using requested status: {cls.status_name}")
        else:
            cls.status_name = next(iter(statuses))
            print(f"[setup] Using first available status: {cls.status_name}")

        print("[setup] Creating experiment...")
        cls.exp = cls.client.create_experiment(
            title=f"ELABMATE TEST {cls.token}",
            category=cls.category_name,
        )
        print(f"[setup] Experiment created with ID: {cls.exp.ID}")

    @staticmethod
    def _wait_for(predicate, message: str, retries: int = 10, delay: float = 0.5):
        last_error: Exception | None = None
        for _ in range(retries):
            try:
                if predicate():
                    return
            except Exception as exc:  # pragma: no cover - best-effort diagnostics
                last_error = exc
            time.sleep(delay)
        if last_error:
            raise AssertionError(f"{message} (last error: {last_error})")
        raise AssertionError(message)

    def _get_file_with_retry(self, filename: str, retries: int = 10, delay: float = 0.5):
        for _ in range(retries):
            meta = self.exp.get_file(filename)
            if meta is not None:
                return meta
            time.sleep(delay)
        self.fail(f"Upload '{filename}' not found after {retries} retries.")

    def test_end_to_end(self) -> None:
        exp = self.exp
        token = self.token

        # Title
        print("[test] Updating title...")
        new_title = f"ELABMATE TEST {token} UPDATED"
        exp.title = new_title
        self.assertEqual(exp.title, new_title)
        print("[test] Title updated.")

        # Main text
        print("[test] Updating main text...")
        body_text = f"Integration body {token}"
        exp.main_text = body_text
        self.assertEqual(exp.main_text, body_text)
        print("[test] Main text updated.")

        # Tags
        print("[test] Adding tag...")
        tag = f"elabmate-{token}"
        exp.add_tag(tag)
        self._wait_for(lambda: tag in exp.tags, "Tag not visible after add.")
        self.assertTrue(exp.has_tag(tag))
        print("[test] Tag added.")
        print("[test] Removing tag...")
        exp.remove_tag(tag)
        self._wait_for(lambda: tag not in exp.tags, "Tag still visible after remove.")
        print("[test] Tag removed.")

        # Steps
        print("[test] Adding step...")
        step_text = f"Step {token}"
        exp.add_step(step_text)
        self._wait_for(lambda: step_text in exp.steps, "Step not visible after add.")
        print("[test] Step added.")

        # Comments
        print("[test] Adding comment...")
        comment_text = f"Comment {token}"
        exp.add_comment(comment_text)
        self._wait_for(lambda: comment_text in exp.comments, "Comment not visible after add.")
        print("[test] Comment added.")

        # Category and status
        print("[test] Validating category getter/setter...")
        self.assertEqual(exp.category, self.category_name)
        exp.category = self.category_name
        self.assertEqual(exp.category, self.category_name)
        with self.assertRaises(InvalidCategory):
            exp.category = f"DOES_NOT_EXIST_{token}"
        print("[test] Category validation complete.")
        # A newly created experiment may have no status on some servers.
        if exp.status is not None:
            self.assertIn(exp.status, self.client.status_dict)
        print("[test] Updating status...")
        exp.status = self.status_name
        self._wait_for(lambda: exp.status == self.status_name, "Status not visible after update.")
        with self.assertRaises(InvalidStatus):
            exp.status = f"DOES_NOT_EXIST_{token}"
        print("[test] Status validation complete.")

        # File upload -> replace -> download
        print("[test] Uploading file...")
        current_dir = Path.cwd()
        filename = f"elabmate_{token}.txt"
        source_path = current_dir / filename
        original_text = f"original {token}"
        source_path.write_text(original_text, encoding="utf-8")
        exp.add_file(str(source_path), comment="integration test upload")
        print("[test] File uploaded.")

        meta = self._get_file_with_retry(filename)
        file_id = meta["id"]
        self.assertIsNotNone(file_id)

        print("[test] Replacing file content...")
        updated_text = f"updated {token}"
        source_path.write_text(updated_text, encoding="utf-8")
        exp.upsert_file(str(source_path))
        print("[test] File replaced.")

        meta = self._get_file_with_retry(filename)
        file_id = meta["id"]

        print("[test] Downloading file...")
        download_path = current_dir / f"elabmate_{token}_download.txt"
        exp.download_file(file_id=file_id, destination=download_path)
        downloaded = download_path.read_text(encoding="utf-8")
        self.assertEqual(downloaded, updated_text)
        print("[test] File downloaded and verified.")
        self.assertEqual(exp.main_text, body_text)
        self.assertEqual(exp.body, body_text)
        print("[test] main_text/body getters verified.")

        # Local cleanup (leave server data as-is for manual inspection).
        print("[test] Cleaning local files...")
        for path in (source_path, download_path):
            try:
                path.unlink()
            except OSError:
                pass
        print("[test] Local cleanup done.")


if __name__ == "__main__":
    unittest.main()
