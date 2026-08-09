import os
import subprocess
import tempfile
import unittest

# Path to the bundled dependency lister under test.
#
# These tests live outside skills/ on purpose. Everything under skills/<name>/ is
# copied verbatim into the published skill and read by the skills.sh security
# auditors, and some fixtures below are deliberately hostile PKGBUILDs. Shipped
# inside the skill they were graded as the skill's own behaviour rather than as
# test data. See the "Security audits" section of the README.
SCRIPT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "skills",
        "install-aur-package",
        "scripts",
        "list-recipe-deps.sh",
    )
)

# Exit code contract of list-recipe-deps.sh
EXIT_OK = 0
EXIT_USAGE = 64
EXIT_NO_SRCINFO = 66


def run_lister(*directories):
    """Run the lister over the given directories and return the CompletedProcess."""
    return subprocess.run(
        [SCRIPT, *directories],
        capture_output=True,
        text=True,
    )


def write_srcinfo(directory, body):
    """Write a .SRCINFO into the given directory."""
    path = os.path.join(directory, ".SRCINFO")
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    return path


def lines(stdout):
    """Split scanner output into a list of non-empty lines."""
    return [line for line in stdout.splitlines() if line]


# A recipe exercising every dependency array the lister reports on.
FULL_SRCINFO = """\
pkgbase = example
\tpkgdesc = Example package
\tpkgver = 1.0.0
\tpkgrel = 1
\turl = https://example.com/example
\tarch = x86_64
\tlicense = MIT
\tmakedepends = go
\tcheckdepends = python-pytest
\tdepends = glibc
\tdepends = pacman>7.0.0
\toptdepends = sudo: privilege elevation
\tprovides = example
\tconflicts = example-git
\tsource = https://example.com/example-1.0.0.tar.gz
\tsha256sums = 0000000000000000000000000000000000000000000000000000000000000000

pkgname = example
"""


class TestListerInvocation(unittest.TestCase):

    def test_script_is_executable(self):
        self.assertTrue(os.path.isfile(SCRIPT), f"missing lister at {SCRIPT}")
        self.assertTrue(os.access(SCRIPT, os.X_OK), "lister is not executable")

    def test_no_arguments_is_usage_error(self):
        result = run_lister()
        self.assertEqual(result.returncode, EXIT_USAGE)
        self.assertIn("usage:", result.stderr)

    def test_missing_directory_is_a_no_srcinfo_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = os.path.join(tmp, "does-not-exist")
            result = run_lister(missing)
        self.assertEqual(result.returncode, EXIT_NO_SRCINFO)
        self.assertIn("ERROR", result.stderr)

    def test_directory_without_srcinfo_is_an_error(self):
        """A clone with only a PKGBUILD cannot be parsed without executing it."""
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "PKGBUILD"), "w", encoding="utf-8") as f:
                f.write("pkgname=example\ndepends=('glibc')\n")
            result = run_lister(tmp)
        self.assertEqual(result.returncode, EXIT_NO_SRCINFO)
        self.assertIn(".SRCINFO", result.stderr)


class TestDependencyExtraction(unittest.TestCase):

    def test_every_dependency_type_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_srcinfo(tmp, FULL_SRCINFO)
            result = run_lister(tmp)
        self.assertEqual(result.returncode, EXIT_OK, result.stderr)
        self.assertEqual(
            lines(result.stdout),
            [
                "checkdepends\tpython-pytest",
                "depends\tglibc",
                "depends\tpacman",
                "makedepends\tgo",
                "optdepends\tsudo",
            ],
        )

    def test_unrelated_arrays_are_not_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_srcinfo(tmp, FULL_SRCINFO)
            result = run_lister(tmp)
        for field in ("provides", "conflicts", "source", "sha256sums", "license"):
            self.assertNotIn(field, result.stdout)

    def test_recipe_without_dependencies_produces_no_output(self):
        body = "pkgbase = example\n\tpkgver = 1.0.0\n\n" "pkgname = example\n"
        with tempfile.TemporaryDirectory() as tmp:
            write_srcinfo(tmp, body)
            result = run_lister(tmp)
        self.assertEqual(result.returncode, EXIT_OK, result.stderr)
        self.assertEqual(result.stdout, "")


class TestNormalisation(unittest.TestCase):

    def test_version_constraints_are_stripped(self):
        body = (
            "pkgbase = example\n"
            "\tdepends = pacman>7.0.0\n"
            "\tdepends = glibc>=2.38\n"
            "\tdepends = openssl=3.0.0\n"
            "\tdepends = curl<9\n"
            "\tdepends = zlib<=1.3\n"
            "\n"
            "pkgname = example\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            write_srcinfo(tmp, body)
            result = run_lister(tmp)
        self.assertEqual(result.returncode, EXIT_OK, result.stderr)
        self.assertEqual(
            lines(result.stdout),
            [
                "depends\tcurl",
                "depends\tglibc",
                "depends\topenssl",
                "depends\tpacman",
                "depends\tzlib",
            ],
        )

    def test_optdepends_descriptions_are_stripped(self):
        body = (
            "pkgbase = example\n"
            "\toptdepends = sudo: privilege elevation, needed for X\n"
            "\toptdepends = git>=2.0: fetching sources\n"
            "\n"
            "pkgname = example\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            write_srcinfo(tmp, body)
            result = run_lister(tmp)
        self.assertEqual(result.returncode, EXIT_OK, result.stderr)
        self.assertEqual(
            lines(result.stdout),
            ["optdepends\tgit", "optdepends\tsudo"],
        )

    def test_architecture_suffixed_arrays_are_reported_under_the_base_type(self):
        body = (
            "pkgbase = example\n"
            "\tdepends_x86_64 = lib32-glibc\n"
            "\tmakedepends_aarch64 = clang\n"
            "\n"
            "pkgname = example\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            write_srcinfo(tmp, body)
            result = run_lister(tmp)
        self.assertEqual(result.returncode, EXIT_OK, result.stderr)
        self.assertEqual(
            lines(result.stdout),
            ["depends\tlib32-glibc", "makedepends\tclang"],
        )

    def test_duplicates_across_split_packages_collapse(self):
        body = (
            "pkgbase = example\n"
            "\tdepends = glibc\n"
            "\n"
            "pkgname = example\n"
            "\tdepends = glibc\n"
            "\n"
            "pkgname = example-extras\n"
            "\tdepends = glibc>=2.38\n"
            "\tdepends = qt6-base\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            write_srcinfo(tmp, body)
            result = run_lister(tmp)
        self.assertEqual(result.returncode, EXIT_OK, result.stderr)
        self.assertEqual(
            lines(result.stdout),
            ["depends\tglibc", "depends\tqt6-base"],
        )

    def test_field_names_are_matched_whole(self):
        """`depends` must not swallow arrays that merely end in it."""
        body = (
            "pkgbase = example\n"
            "\tdepends = glibc\n"
            "\tnotdepends = should-not-appear\n"
            "\n"
            "pkgname = example\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            write_srcinfo(tmp, body)
            result = run_lister(tmp)
        self.assertEqual(lines(result.stdout), ["depends\tglibc"])


class TestRecipeIsNeverExecuted(unittest.TestCase):

    def test_pkgbuild_top_level_code_does_not_run(self):
        """Sourcing a PKGBUILD executes top-level shell code; the lister must not."""
        with tempfile.TemporaryDirectory() as tmp:
            marker = os.path.join(tmp, "PKGBUILD-WAS-EXECUTED")
            write_srcinfo(tmp, FULL_SRCINFO)
            with open(os.path.join(tmp, "PKGBUILD"), "w", encoding="utf-8") as f:
                f.write(f"pkgname=example\ntouch '{marker}'\ndepends=('glibc')\n")
            result = run_lister(tmp)
            executed = os.path.exists(marker)
        self.assertEqual(result.returncode, EXIT_OK, result.stderr)
        self.assertFalse(executed, "the lister executed the PKGBUILD")

    def test_srcinfo_values_are_not_expanded_as_shell(self):
        """.SRCINFO is untrusted text; substitutions in it must stay literal."""
        body = (
            "pkgbase = example\n"
            "\tdepends = $(id -u)\n"
            "\tdepends = `id -u`\n"
            "\n"
            "pkgname = example\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            write_srcinfo(tmp, body)
            result = run_lister(tmp)
        self.assertEqual(result.returncode, EXIT_OK, result.stderr)
        self.assertIn("$(id -u)", result.stdout)
        self.assertIn("`id -u`", result.stdout)


if __name__ == "__main__":
    unittest.main()
