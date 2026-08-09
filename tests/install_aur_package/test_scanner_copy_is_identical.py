import glob
import hashlib
import os
import stat
import unittest

# scan-aur-recipe.sh is deliberately duplicated into every skill that needs it.
#
# The `skills` CLI installs each skills/<name>/ directory as a self-contained
# payload, so a skill cannot reference a script that lives inside a sibling
# skill: the path exists in this repository and not on a user's machine.
# Duplication is therefore the only workable option, and this test is what keeps
# the duplicates honest. `make lint-shared` performs the same check without
# pytest.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCANNER_GLOB = os.path.join(REPO_ROOT, "skills", "*", "scripts", "scan-aur-recipe.sh")
CANONICAL = os.path.join(
    REPO_ROOT, "skills", "update-arch-system", "scripts", "scan-aur-recipe.sh"
)


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class TestScannerCopiesAreIdentical(unittest.TestCase):

    def setUp(self):
        self.copies = sorted(glob.glob(SCANNER_GLOB))

    def test_canonical_scanner_exists(self):
        self.assertIn(CANONICAL, self.copies, f"canonical scanner missing at {CANONICAL}")

    def test_at_least_two_skills_bundle_the_scanner(self):
        """Guards the check itself: a glob matching one file can never fail."""
        self.assertGreaterEqual(
            len(self.copies), 2, f"expected several bundled scanners, found {self.copies}"
        )

    def test_every_copy_matches_the_canonical_one(self):
        expected = sha256(CANONICAL)
        for copy in self.copies:
            with self.subTest(copy=os.path.relpath(copy, REPO_ROOT)):
                self.assertEqual(
                    sha256(copy),
                    expected,
                    f"{os.path.relpath(copy, REPO_ROOT)} has drifted from "
                    f"{os.path.relpath(CANONICAL, REPO_ROOT)}; copy the canonical "
                    f"file over it rather than editing one side",
                )

    def test_every_copy_is_executable(self):
        for copy in self.copies:
            with self.subTest(copy=os.path.relpath(copy, REPO_ROOT)):
                mode = os.stat(copy).st_mode
                self.assertTrue(mode & stat.S_IXUSR, "copy is not executable")


if __name__ == "__main__":
    unittest.main()
