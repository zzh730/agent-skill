import json
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

PUBLISH = Path(__file__).resolve().parents[1] / "skills" / "pele-diagram" / "scripts" / "pele-publish"
GITHUB_URL = "https://github.com/acme/widgets.git"


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


class PelePublishTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        root = Path(self.tmp.name)
        self.remote = root / "remote.git"
        self.checkout = root / "checkout"
        subprocess.run(["git", "init", "-q", "--bare", str(self.remote)], check=True)
        subprocess.run(["git", "init", "-q", "-b", "feature", str(self.checkout)], check=True)
        git(self.checkout, "config", "user.email", "test@example.com")
        git(self.checkout, "config", "user.name", "Test")
        git(self.checkout, "remote", "add", "origin", GITHUB_URL)
        git(self.checkout, "config", f"url.{self.remote}.insteadOf", GITHUB_URL)
        (self.checkout / "app.txt").write_text("app\n")
        git(self.checkout, "add", "app.txt")
        git(self.checkout, "commit", "-q", "-m", "app")
        (self.checkout / "staged.txt").write_text("staged\n")
        git(self.checkout, "add", "staged.txt")
        (self.checkout / "dirty.txt").write_text("dirty\n")
        self.images = root / "images"
        self.images.mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def image(self, name: str, width: int) -> Path:
        path = self.images / name
        path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="40"></svg>')
        return path

    def publish(self, *files: Path) -> dict:
        result = subprocess.run(
            [str(PUBLISH), "--json", "--branch", "diagrams", *map(str, files)],
            cwd=self.checkout,
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout)

    def checkout_state(self) -> tuple[str, str, str]:
        return (
            git(self.checkout, "rev-parse", "HEAD"),
            git(self.checkout, "status", "--porcelain"),
            git(self.checkout, "diff", "--cached", "--name-only"),
        )

    def test_publish_leaves_checkout_untouched_and_chains_commits(self) -> None:
        before_state = self.checkout_state()

        first = self.publish(self.image("before.svg", 300), self.image("after.svg", 500))
        self.assertEqual(self.checkout_state(), before_state)
        self.assertEqual(first["repo"], "acme/widgets")
        self.assertEqual(
            first["images"][0]["url"],
            f"https://github.com/acme/widgets/raw/{first['commit']}/feature/before.svg",
        )
        self.assertEqual(first["images"][1]["width"], 500)
        self.assertEqual(git(self.remote, "rev-parse", "refs/heads/diagrams"), first["commit"])
        self.assertEqual(git(self.remote, "rev-list", "--count", first["commit"]), "1")

        second = self.publish(self.image("extra.svg", 100))
        self.assertEqual(git(self.remote, "rev-parse", f"{second['commit']}^"), first["commit"])
        self.assertEqual(
            git(self.remote, "ls-tree", "-r", "--name-only", second["commit"]).splitlines(),
            ["feature/after.svg", "feature/before.svg", "feature/extra.svg"],
        )

        third = self.publish(self.images / "extra.svg")
        self.assertEqual(third["commit"], second["commit"])
        self.assertEqual(self.checkout_state(), before_state)

    def test_rejects_non_github_remote(self) -> None:
        git(self.checkout, "remote", "set-url", "origin", "https://gitlab.com/acme/widgets.git")
        result = subprocess.run(
            [str(PUBLISH), str(self.image("a.svg", 10))], cwd=self.checkout, capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("not a github.com repository", result.stderr)


if __name__ == "__main__":
    unittest.main()
