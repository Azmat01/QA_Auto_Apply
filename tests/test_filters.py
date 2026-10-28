from __future__ import annotations

import unittest

from qa_auto_apply.filters import (
    compile_keyword_regex,
    is_junior_role,
    keep_listing,
    matches_location,
    rank_key,
    title_is_senior,
)
from qa_auto_apply.models import JobListing


def _job(
    role: str,
    location: str = "Remote",
    *,
    company: str = "Acme",
    description: str = "",
    url: str = "https://example.com/job",
) -> JobListing:
    return JobListing(
        company=company,
        role=role,
        location=location,
        application_url=url,
        source="greenhouse",
        description=description,
    )


class KeywordFilterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.regex = compile_keyword_regex(
            ["QA", "SDET", "Manual Tester", "QA Engineer", "Test Engineer"]
        )

    def test_matches_core_titles(self) -> None:
        titles = [
            "QA Engineer",
            "Senior SDET",
            "Automation QA",
            "Test Engineer - Platform",
            "Software Development Engineer in Test",
            "QA Automation Engineer",
            "Staff Web Automation Engineer, Quality Engineering",
            "Manual Tester",
            "Manual QA",
            "QA Tester",
            "Quality Analyst",
            "Test Analyst",
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


class ExperienceFilterTests(unittest.TestCase):
    def test_junior_titles(self) -> None:
        titles = [
            "Junior QA Engineer",
            "QA Engineer Intern",
            "Manual Tester - Fresher",
            "Associate QA Engineer",
            "Entry Level Test Engineer",
            "Graduate QA Tester",
        ]
        for title in titles:
            with self.subTest(title=title):
                self.assertTrue(is_junior_role(title), title)
                self.assertFalse(title_is_senior(title), title)

    def test_rejects_senior_titles(self) -> None:
        titles = [
            "Senior QA Engineer",
            "Staff SDET",
            "Principal Test Engineer",
            "QA Lead",
            "QA Manager",
            "SDET - 5+ years",
        ]
        for title in titles:
            with self.subTest(title=title):
                self.assertTrue(title_is_senior(title), title)
                self.assertFalse(is_junior_role(title, "Looking for a fresher intern"), title)

    def test_description_zero_to_one_year(self) -> None:
        self.assertTrue(
            is_junior_role(
                "QA Engineer",
                "We are hiring for 0-1 years of experience in manual testing.",
            )
        )
        self.assertTrue(
            is_junior_role(
                "Manual Tester",
                "Entry-level role. No prior experience required.",
            )
        )
        self.assertFalse(
            is_junior_role(
                "QA Engineer",
                "Build high quality software with our platform team.",
            )
        )


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

    def test_keep_listing_requires_role_location_and_junior(self) -> None:
        regex = compile_keyword_regex()
        junior_remote = _job("Junior QA Engineer", "Remote")
        mid_remote = _job("SDET", "Remote")
        senior_india = _job("Senior QA Engineer", "Bengaluru, India")
        junior_sf = _job("QA Intern", "San Francisco, CA")
        india_pm = _job("Product Manager", "Bengaluru, India")
        desc_junior = _job(
            "Manual Tester",
            "Hyderabad, India",
            description="0-1 years. Campus hiring for fresh graduates.",
        )

        self.assertTrue(keep_listing(junior_remote, regex))
        self.assertTrue(keep_listing(desc_junior, regex))
        self.assertFalse(keep_listing(mid_remote, regex))
        self.assertFalse(keep_listing(senior_india, regex))
        self.assertFalse(keep_listing(junior_sf, regex))
        self.assertFalse(keep_listing(india_pm, regex))

    def test_rank_prefers_title_junior_then_india(self) -> None:
        title_india = _job("Junior QA Engineer", "Bengaluru, India", company="Okta")
        desc_remote = _job(
            "QA Engineer",
            "Remote",
            company="Stripe",
            description="Entry-level, 0-1 years.",
        )
        title_remote = _job("QA Intern", "Remote", company="Postman")
        ranked = sorted(
            [desc_remote, title_remote, title_india],
            key=rank_key,
        )
        self.assertEqual(ranked[0].role, "Junior QA Engineer")
        self.assertEqual(ranked[1].role, "QA Intern")
        self.assertEqual(ranked[2].role, "QA Engineer")


if __name__ == "__main__":
    unittest.main()
