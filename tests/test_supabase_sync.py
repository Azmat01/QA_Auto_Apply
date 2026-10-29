from __future__ import annotations

import unittest
from unittest.mock import patch

from qa_auto_apply.models import JobListing
from qa_auto_apply.supabase_sync import SupabaseSyncError, sync_jobs_to_supabase


class SupabaseSyncTests(unittest.TestCase):
    def test_skips_without_credentials(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            count = sync_jobs_to_supabase(
                [
                    JobListing(
                        company="Okta",
                        role="Junior QA",
                        location="India",
                        application_url="https://example.com/1",
                        source="greenhouse",
                    )
                ],
                url="",
                api_key="",
            )
        self.assertEqual(count, 0)

    def test_rejects_broken_url(self) -> None:
        with self.assertRaises(SupabaseSyncError):
            sync_jobs_to_supabase(
                [
                    JobListing(
                        company="Okta",
                        role="Junior QA",
                        location="India",
                        application_url="https://example.com/1",
                        source="greenhouse",
                    )
                ],
                url="https//:broken.supabase.co",
                api_key="test-key",
            )


if __name__ == "__main__":
    unittest.main()
