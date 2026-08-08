import os
import subprocess
import tempfile
import unittest

# Path to the bundled scanner under test
SCRIPT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "scripts", "scan-aur-recipe.sh")
)

# Exit code contract of scan-aur-recipe.sh
EXIT_CLEAN = 0
EXIT_MEDIUM = 1
EXIT_HIGH = 2
EXIT_USAGE = 64

# A PKGBUILD with no findings: https source, real hash, no network/privilege/lifecycle verbs
CLEAN_PKGBUILD = """\
pkgname=example
pkgver=1.0.0
pkgrel=1
pkgdesc="Example package"
arch=('x86_64')
url="https://example.com/example"
license=('MIT')
source=("https://example.com/example-1.0.0.tar.gz")
sha256sums=('0000000000000000000000000000000000000000000000000000000000000000')

build() {
  cd "example-1.0.0"
  make
}
"""


def run_scanner(*directories):
    """Run the scanner over the given directories and return the CompletedProcess."""
    return subprocess.run(
        [SCRIPT, *directories],
        capture_output=True,
        text=True,
    )


def write_pkgbuild(directory, body):
    """Write a single PKGBUILD into an otherwise empty directory.

    The scanner walks every file under the directory, so fixtures must not
    contain anything besides the recipe under test.
    """
    path = os.path.join(directory, "PKGBUILD")
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    return path


class TestScannerInvocation(unittest.TestCase):

    def test_script_is_executable(self):
        self.assertTrue(os.path.isfile(SCRIPT), f"missing scanner at {SCRIPT}")
        self.assertTrue(os.access(SCRIPT, os.X_OK), "scanner is not executable")

    def test_no_arguments_is_usage_error(self):
        result = run_scanner()
        self.assertEqual(result.returncode, EXIT_USAGE)
        self.assertIn("usage:", result.stderr)

    def test_missing_directory_reports_error_on_stderr(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = os.path.join(tmp, "does-not-exist")
            result = run_scanner(missing)
        self.assertEqual(result.returncode, EXIT_HIGH)
        self.assertIn("ERROR", result.stderr)
        self.assertIn("not a directory", result.stderr)


class TestCleanRecipe(unittest.TestCase):

    def test_clean_recipe_has_no_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_pkgbuild(tmp, CLEAN_PKGBUILD)
            result = run_scanner(tmp)
        self.assertEqual(result.returncode, EXIT_CLEAN, f"unexpected findings:\n{result.stdout}")
        self.assertEqual(result.stdout, "")


class TestHighRiskPatterns(unittest.TestCase):

    HIGH_CASES = [
        (
            "piped remote script",
            'build() {\n  curl https://example.com/install.sh | bash\n}\n',
            "piped to an interpreter",
        ),
        (
            "privilege command",
            'package() {\n  sudo chown root:root "$pkgdir/usr/bin/example"\n}\n',
            "privilege command",
        ),
        (
            "credential access",
            'build() {\n  cp ~/.ssh/id_rsa "$srcdir/key"\n}\n',
            "credentials or secret stores",
        ),
        (
            "dynamic execution",
            'build() {\n  eval "$payload"\n}\n',
            "dynamic or encoded command execution",
        ),
    ]

    def test_high_risk_patterns_exit_two(self):
        for label, body, message in self.HIGH_CASES:
            with self.subTest(case=label):
                with tempfile.TemporaryDirectory() as tmp:
                    write_pkgbuild(tmp, body)
                    result = run_scanner(tmp)
                self.assertEqual(result.returncode, EXIT_HIGH)
                self.assertIn("HIGH", result.stdout)
                self.assertIn(message, result.stdout)


class TestMediumRiskPatterns(unittest.TestCase):

    MEDIUM_CASES = [
        (
            "skipped integrity check",
            'source=("https://example.com/example-1.0.0.tar.gz")\nsha256sums=(\'SKIP\')\n',
            "integrity check explicitly skipped",
        ),
        (
            "plaintext source url",
            'source=("http://example.com/example-1.0.0.tar.gz")\n',
            "unencrypted source URL",
        ),
        (
            "mutable vcs source",
            'source=("example::git+https://example.com/example.git")\n',
            "mutable VCS source",
        ),
        (
            "prebuilt artifact",
            'source=("https://example.com/example-1.0.0.AppImage")\n',
            "prebuilt package or executable artifact",
        ),
        (
            "md5 hash",
            'source=("https://example.com/example-1.0.0.tar.gz")\n'
            "md5sums=('a8f84171ee1796fc4899579d92df0e24')\n",
            "weak hash algorithm",
        ),
        (
            "sha1 hash",
            'source=("https://example.com/example-1.0.0.tar.gz")\n'
            "sha1sums=('da39a3ee5e6b4b0d3255bfef95601890afd80709')\n",
            "weak hash algorithm",
        ),
        (
            "md5 hash in .SRCINFO style declaration",
            "\tmd5sums = a8f84171ee1796fc4899579d92df0e24\n",
            "weak hash algorithm",
        ),
    ]

    def test_medium_risk_patterns_exit_one(self):
        for label, body, message in self.MEDIUM_CASES:
            with self.subTest(case=label):
                with tempfile.TemporaryDirectory() as tmp:
                    write_pkgbuild(tmp, body)
                    result = run_scanner(tmp)
                self.assertEqual(result.returncode, EXIT_MEDIUM)
                self.assertIn("MEDIUM", result.stdout)
                self.assertIn(message, result.stdout)


class TestWeakHashBoundaries(unittest.TestCase):
    """The weak-algorithm rule must not fire on strong hashes or duplicate the SKIP rule."""

    def test_strong_hash_algorithms_are_not_flagged(self):
        for algorithm, digest in [
            ("sha256sums", "0" * 64),
            ("sha512sums", "0" * 128),
            ("b2sums", "0" * 128),
        ]:
            with self.subTest(algorithm=algorithm):
                body = (
                    'source=("https://example.com/example-1.0.0.tar.gz")\n'
                    f"{algorithm}=('{digest}')\n"
                )
                with tempfile.TemporaryDirectory() as tmp:
                    write_pkgbuild(tmp, body)
                    result = run_scanner(tmp)
                self.assertEqual(result.returncode, EXIT_CLEAN, f"unexpected findings:\n{result.stdout}")
                self.assertNotIn("weak hash algorithm", result.stdout)

    def test_skipped_weak_hash_reports_skip_only(self):
        """md5sums=('SKIP') has no digest to weigh, so only the SKIP rule applies."""
        body = (
            'source=("https://example.com/example-1.0.0.tar.gz")\n'
            "md5sums=('SKIP')\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            write_pkgbuild(tmp, body)
            result = run_scanner(tmp)
        self.assertEqual(result.returncode, EXIT_MEDIUM)
        self.assertIn("integrity check explicitly skipped", result.stdout)
        self.assertNotIn("weak hash algorithm", result.stdout)


class TestSeverityPrecedence(unittest.TestCase):

    def test_high_outranks_medium_in_same_file(self):
        body = (
            'source=("https://example.com/example-1.0.0.tar.gz")\n'
            "sha256sums=('SKIP')\n"
            'package() {\n  sudo chown root:root "$pkgdir/usr/bin/example"\n}\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            write_pkgbuild(tmp, body)
            result = run_scanner(tmp)
        self.assertEqual(result.returncode, EXIT_HIGH)
        self.assertIn("HIGH", result.stdout)
        self.assertIn("MEDIUM", result.stdout)

    def test_high_in_any_of_several_directories(self):
        with tempfile.TemporaryDirectory() as clean, tempfile.TemporaryDirectory() as risky:
            write_pkgbuild(clean, CLEAN_PKGBUILD)
            write_pkgbuild(risky, 'build() {\n  eval "$payload"\n}\n')
            result = run_scanner(clean, risky)
        self.assertEqual(result.returncode, EXIT_HIGH)
        self.assertIn("HIGH", result.stdout)

    def test_findings_are_reported_for_non_pkgbuild_files(self):
        """A benign PKGBUILD does not make a malicious .install harmless."""
        with tempfile.TemporaryDirectory() as tmp:
            write_pkgbuild(tmp, CLEAN_PKGBUILD)
            hook = os.path.join(tmp, "example.install")
            with open(hook, "w", encoding="utf-8") as f:
                f.write('post_install() {\n  eval "$payload"\n}\n')
            result = run_scanner(tmp)
        self.assertEqual(result.returncode, EXIT_HIGH)
        self.assertIn("example.install", result.stdout)


if __name__ == "__main__":
    unittest.main()
