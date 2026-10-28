from __future__ import annotations

import unittest
from qa_auto_apply.models import JobListing
from qa_auto_apply.notifier import _email_bodies
from qa_auto_apply.textutil import html_to_text


class TextutilTests(unittest.TestCase):
    def test_strips_html(self) -> None:
        text = html_to_text("<p>0-1 years &amp; <b>fresher</b> role</p>")
        self.assertIn("0-1 years", text)
        self.assertIn("fresher", text)
        self.assertNotIn("<p>", text)


class EmailBodyTests(unittest.TestCase):
    def test_includes_clickable_apply_urls(self) -> None:
        jobs = [
            JobListing(
                company="Okta",
                role="Junior QA Engineer",
                location="Bengaluru, India",
                application_url="https://example.com/apply/1",
                source="greenhouse",
            )
        ]
        plain, html_body = _email_bodies(jobs, count=1, digest="")
        self.assertIn("https://example.com/apply/1", plain)
        self.assertIn('href="https://example.com/apply/1"', html_body)
        self.assertIn("Junior QA Engineer", html_body)


if __name__ == "__main__":
    unittest.main()
