import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class VercelServesTheSameStaticSiteAsPages(unittest.TestCase):
    def setUp(self):
        self.vercel = json.loads((ROOT / "vercel.json").read_text())
        self.workflow = (ROOT / ".github" / "workflows" / "scrape.yml").read_text()

    def test_vercel_publishes_exactly_what_the_pages_job_publishes(self):
        pages = re.search(r"cp -r (.+?) _site/", self.workflow).group(1).split()
        vercel = re.search(r"cp -r (.+?) _site/", self.vercel["buildCommand"]).group(1).split()
        self.assertEqual(sorted(vercel), sorted(pages))
        self.assertEqual(sorted(vercel), ["data", "index.html", "static"])
        self.assertEqual(self.vercel["outputDirectory"], "_site")

    def test_vercel_does_not_try_to_run_the_live_server(self):
        self.assertIsNone(self.vercel["framework"])
        self.assertEqual(self.vercel["installCommand"], "")
        self.assertFalse((ROOT / "api").exists())


if __name__ == "__main__":
    unittest.main()
