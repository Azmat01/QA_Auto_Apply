from __future__ import annotations

import unittest

from qa_auto_apply.filters import (
    compile_keyword_regex,
    is_internship,
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
            ["QA", "SDET", "Manual Tester", "QA Engineer", "Test Engineer", "QA Intern"]
        )

    def test_matches_core_and_intern_titles(self) -> None:
        titles = [
            "QA Engineer",
            "QA Intern",
            "Software Testing Intern",
            "SDET Internship",
            "Manual Tester",
            "Test Engineer - Platform",
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
            "Marketing Intern",
        ]
        for title in titles:
            with self.subTest(title=title):
                self.assertFalse(self.regex.search(title), title)


class ExperienceFilterTests(unittest.TestCase):
    def test_junior_and_intern_titles(self) -> None:
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

    def test_internship_detection(self) -> None:
        self.assertTrue(is_internship("QA Intern"))
        self.assertTrue(is_internship("Test Engineer", "This is a 6-month internship."))
        self.assertFalse(is_internship("QA Engineer", "Full-time role in quality."))

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
    def test_requires_remote_wfh(self) -> None:
        self.assertTrue(matches_location("Remote - US", require_remote=True))
        self.assertTrue(matches_location("Work from home - India", require_remote=True))
        self.assertTrue(matches_location("Remote Europe", require_remote=True))
        self.assertTrue(matches_location("Remote - Dubai, UAE", require_remote=True))
        self.assertTrue(matches_location("Remote - Singapore", require_remote=True))
        self.assertTrue(matches_location("Remote - Sydney, Australia", require_remote=True))
        self.assertFalse(matches_location("Bengaluru, India", require_remote=True))
        self.assertFalse(matches_location("London, United Kingdom", require_remote=True))
        self.assertFalse(matches_location("San Francisco, CA", require_remote=True))

    def test_blocks_pakistan_egypt_argentina(self) -> None:
        self.assertFalse(matches_location("Remote - Pakistan", require_remote=True))
        self.assertFalse(matches_location("WFH Cairo, Egypt", require_remote=True))
        self.assertFalse(matches_location("Remote Argentina", require_remote=True))
        self.assertFalse(matches_location("Remote - Buenos Aires", require_remote=True))

    def test_keep_listing_remote_junior_intern(self) -> None:
        regex = compile_keyword_regex()
        remote_intern = _job("QA Intern", "Remote - Germany")
        remote_junior = _job(
            "QA Engineer",
            "Remote - USA",
            description="0-1 years experience. Entry-level.",
        )
        onsite_india = _job("QA Intern", "Bengaluru, India")
        remote_pakistan = _job("QA Intern", "Remote - Pakistan")
        senior_remote = _job("Senior QA Engineer", "Remote")
        mid_remote = _job("SDET", "Remote")

        self.assertTrue(keep_listing(remote_intern, regex, experience_mode="junior_only"))
        self.assertTrue(keep_listing(remote_junior, regex, experience_mode="junior_only"))
        self.assertFalse(keep_listing(onsite_india, regex, experience_mode="junior_only"))
        self.assertFalse(keep_listing(remote_pakistan, regex, experience_mode="junior_only"))
        self.assertFalse(keep_listing(senior_remote, regex, experience_mode="junior_only"))
        self.assertFalse(keep_listing(mid_remote, regex, experience_mode="junior_only"))

    def test_rank_prefers_internships(self) -> None:
        intern = _job("QA Intern", "Remote", company="Stripe")
        junior = _job("Junior QA Engineer", "Remote", company="Okta")
        ranked = sorted([junior, intern], key=rank_key)
        self.assertEqual(ranked[0].role, "QA Intern")


if __name__ == "__main__":
    unittest.main()
