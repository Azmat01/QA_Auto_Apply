from __future__ import annotations

import unittest

from qa_auto_apply.filters import (
    classify_location_bucket,
    compile_keyword_regex,
    is_internship,
    is_junior_role,
    keep_listing,
    matches_location,
    select_by_quotas,
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
        for title in [
            "Junior QA Engineer",
            "QA Engineer Intern",
            "Manual Tester - Fresher",
            "Associate QA Engineer",
            "Entry Level Test Engineer",
            "Graduate QA Tester",
        ]:
            with self.subTest(title=title):
                self.assertTrue(is_junior_role(title), title)
                self.assertFalse(title_is_senior(title), title)

    def test_internship_detection(self) -> None:
        self.assertTrue(is_internship("QA Intern"))
        self.assertTrue(is_internship("Test Engineer", "This is a 6-month internship."))
        self.assertFalse(is_internship("QA Engineer", "Full-time role in quality."))

    def test_rejects_senior_titles(self) -> None:
        for title in [
            "Senior QA Engineer",
            "Staff SDET",
            "Principal Test Engineer",
            "QA Lead",
            "QA Manager",
            "SDET - 5+ years",
        ]:
            with self.subTest(title=title):
                self.assertTrue(title_is_senior(title), title)
                self.assertFalse(is_junior_role(title, "Looking for a fresher intern"), title)


class LocationFilterTests(unittest.TestCase):
    def test_buckets(self) -> None:
        self.assertEqual(classify_location_bucket("Noida, India"), "india_office")
        self.assertEqual(classify_location_bucket("Gurugram"), "india_office")
        self.assertEqual(classify_location_bucket("Zirakpur, Punjab"), "india_office")
        self.assertEqual(classify_location_bucket("Remote - India"), "india_wfh")
        self.assertEqual(classify_location_bucket("WFH Bengaluru"), "india_wfh")
        self.assertEqual(classify_location_bucket("Remote - USA"), "intl_wfh")
        self.assertEqual(classify_location_bucket("Remote Europe"), "intl_wfh")
        self.assertEqual(classify_location_bucket("Remote - Dubai"), "intl_wfh")
        self.assertIsNone(classify_location_bucket("Remote - Pakistan"))
        self.assertIsNone(classify_location_bucket("Cairo, Egypt"))
        self.assertIsNone(classify_location_bucket("Chennai, India"))  # not in preferred office list

    def test_matches_location_allows_office_and_wfh(self) -> None:
        self.assertTrue(matches_location("Pune, India"))
        self.assertTrue(matches_location("Remote - India"))
        self.assertTrue(matches_location("Remote - Germany"))
        self.assertFalse(matches_location("Remote - Argentina"))
        self.assertFalse(matches_location("Chennai, India"))

    def test_select_by_quotas(self) -> None:
        regex = compile_keyword_regex()
        jobs = [
            _job("QA Intern", "Noida", url="https://x/1", description="intern"),
            _job("QA Intern", "Gurgaon", url="https://x/2", description="intern"),
            _job("QA Intern", "Jaipur", url="https://x/3", description="intern"),
            _job("QA Intern", "Lucknow", url="https://x/4", description="intern"),
            _job("QA Intern", "Remote - India", url="https://x/5", description="intern"),
            _job("QA Intern", "WFH India", url="https://x/6", description="intern"),
            _job("QA Intern", "Remote - India 2", url="https://x/7", description="intern"),
            _job("QA Intern", "Remote - USA", url="https://x/8", description="intern"),
            _job("QA Intern", "Remote - UK", url="https://x/9", description="intern"),
            _job("QA Intern", "Remote - Singapore", url="https://x/10", description="intern"),
            _job("QA Intern", "Remote - UAE", url="https://x/11", description="intern"),
            _job("QA Intern", "Remote - Australia", url="https://x/12", description="intern"),
            _job("QA Intern", "Remote - Canada", url="https://x/13", description="intern"),
        ]
        kept = [job for job in jobs if keep_listing(job, regex)]
        selected = select_by_quotas(kept)
        self.assertEqual(len(selected), 10)
        office = [j for j in selected if classify_location_bucket(j.location) == "india_office"]
        india_wfh = [j for j in selected if classify_location_bucket(j.location) == "india_wfh"]
        intl = [j for j in selected if classify_location_bucket(j.location) == "intl_wfh"]
        self.assertEqual(len(office), 3)
        self.assertEqual(len(india_wfh), 2)
        self.assertEqual(len(intl), 5)


if __name__ == "__main__":
    unittest.main()
