from __future__ import annotations

import unittest

from qa_auto_apply.filters import compile_keyword_regex, keep_listing, matches_location
from qa_auto_apply.models import JobListing


class KeywordFilterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.regex = compile_keyword_regex(["QA", "SDET", "Automation QA", "Test Engineer"])

    def test_matches_core_titles(self) -> None:
        titles = [
            "QA Engineer",
            "Senior SDET",
            "Automation QA",
            "Test Engineer - Platform",
            "Software Development Engineer in Test",
            "QA Automation Engineer",
            "Staff Web Automation Engineer, Quality Engineering",
        ]
        for title in titles:
            with self.subTest(title=title):
                self.assertTrue(self.regex.search(title), title)

    def test_rejects_unrelated_titles(self) -> None:
        titles = [
            "Backend Engineer",
            "Product Manager",
            "Sales Executive",
            "EQUAL Opportunity Specialist",
            "Senior IT Automation Engineer",
        ]
        for title in titles:
            with self.subTest(title=title):
                self.assertFalse(self.regex.search(title), title)


class LocationFilterTests(unittest.TestCase):
    def test_india_and_remote(self) -> None:
        self.assertTrue(matches_location("Bengaluru, India"))
        self.assertTrue(matches_location("Remote - US"))
        self.assertTrue(matches_location("Pune", workplace_type="hybrid"))
        self.assertTrue(matches_location("San Francisco", workplace_type="remote"))
        self.assertTrue(matches_location("", country="IN", workplace_type="on-site"))
        self.assertTrue(matches_location("Hyderabad, IN"))
        self.assertFalse(matches_location("San Francisco, CA"))
        self.assertFalse(matches_location("London, United Kingdom"))

    def test_keep_listing_requires_both(self) -> None:
        regex = compile_keyword_regex()
        remote_qa = JobListing(
            company="Stripe",
            role="SDET",
            location="Remote",
            application_url="https://example.com/1",
            source="greenhouse",
        )
        sf_backend = JobListing(
            company="Stripe",
            role="Backend Engineer",
            location="San Francisco",
            application_url="https://example.com/2",
            source="greenhouse",
        )
        india_pm = JobListing(
            company="Postman",
            role="Product Manager",
            location="Bengaluru, India",
            application_url="https://example.com/3",
            source="greenhouse",
        )
        self.assertTrue(keep_listing(remote_qa, regex))
        self.assertFalse(keep_listing(sf_backend, regex))
        self.assertFalse(keep_listing(india_pm, regex))


if __name__ == "__main__":
    unittest.main()
