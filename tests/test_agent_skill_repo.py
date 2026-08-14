import os
import shutil
import subprocess
import sys
from pathlib import Path

import unittest
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from agent_skill_repo import (
    add_third_party_skill,
    bootstrap,
    doctor,
    import_local_skill,
    load_manifest,
    sync_third_party_skills,
)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_git_skill_repo(root: Path, skill_path: str = "skills/example") -> str:
    write(root / skill_path / "SKILL.md", "---\nname: example\n---\n\n# Example\n")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial"], cwd=root, check=True)
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


class AgentSkillRepoTests(unittest.TestCase):
    def test_add_third_party_skill_validates_skill_and_updates_manifest_and_lock(self) -> None:
        with TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            upstream = Path(tmp) / "upstream"
            repo.mkdir()
            upstream.mkdir()
            commit = make_git_skill_repo(upstream, "nested/example")

            result = add_third_party_skill(
                repo,
                name="example",
                upstream=str(upstream),
                ref="HEAD",
                skill_path="nested/example",
                targets=["claude", "codex"],
                dry_run=False,
                install=False,
            )

            manifest = load_manifest(repo / "sources" / "third-party-skills.yaml")
            self.assertEqual(result.resolved_ref, commit)
            self.assertEqual(manifest["dependencies"][0]["name"], "example")
            self.assertEqual(manifest["dependencies"][0]["skill_path"], "nested/example")
            self.assertIn(commit, (repo / "sources" / "third-party-skills.lock").read_text())

    def test_add_third_party_skill_dry_run_does_not_write(self) -> None:
        with TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            upstream = Path(tmp) / "upstream"
            repo.mkdir()
            upstream.mkdir()
            make_git_skill_repo(upstream, "skills/example")

            add_third_party_skill(
                repo,
                name="example",
                upstream=str(upstream),
                ref="HEAD",
                skill_path="skills/example",
                targets=["claude"],
                dry_run=True,
                install=False,
            )

            self.assertFalse((repo / "sources" / "third-party-skills.yaml").exists())
            self.assertFalse((repo / "sources" / "third-party-skills.lock").exists())

    def test_bootstrap_installs_owned_and_locked_third_party_skills(self) -> None:
        with TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            upstream = Path(tmp) / "upstream"
            claude_home = Path(tmp) / "claude"
            codex_home = Path(tmp) / "codex"
            grok_home = Path(tmp) / "grok"
            repo.mkdir()
            upstream.mkdir()
            commit = make_git_skill_repo(upstream, "remote/example")
            write(repo / "skills" / "mine" / "SKILL.md", "---\nname: mine\n---\n")
            write(repo / "commands" / "claude" / "focus.md", "# Focus\n")
            write(
                repo / "sources" / "third-party-skills.yaml",
                f"""dependencies:
  - name: example
    upstream: {upstream}
    ref: HEAD
    skill_path: remote/example
    targets: [claude, codex, grok]
""",
            )
            write(
                repo / "sources" / "third-party-skills.lock",
                f"""dependencies:
  - name: example
    upstream: {upstream}
    resolved_ref: {commit}
    resolved_at: "2026-05-24"
""",
            )

            actions = bootstrap(
                repo,
                targets=["claude", "codex", "grok"],
                homes={"claude": claude_home, "codex": codex_home, "grok": grok_home},
                dry_run=False,
            )

            self.assertIn("install owned skill mine -> claude", "\n".join(actions))
            self.assertTrue((claude_home / "skills" / "mine" / "SKILL.md").exists())
            self.assertTrue((claude_home / "skills" / "example" / "SKILL.md").exists())
            self.assertTrue((codex_home / "skills" / "example" / "SKILL.md").exists())
            self.assertTrue((grok_home / "skills" / "mine" / "SKILL.md").exists())
            self.assertTrue((grok_home / "skills" / "example" / "SKILL.md").exists())
            self.assertTrue((claude_home / "commands" / "focus.md").exists())

    def test_bootstrap_replaces_existing_skill_symlink(self) -> None:
        with TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            claude_home = Path(tmp) / "claude"
            linked_target = Path(tmp) / "linked-target"
            repo.mkdir()
            write(repo / "skills" / "mine" / "SKILL.md", "---\nname: mine\n---\n")
            write(linked_target / "SKILL.md", "---\nname: old\n---\n")
            (claude_home / "skills").mkdir(parents=True)
            os.symlink(linked_target, claude_home / "skills" / "mine")

            bootstrap(repo, targets=["claude"], homes={"claude": claude_home}, dry_run=False)

            installed = claude_home / "skills" / "mine"
            self.assertFalse(installed.is_symlink())
            self.assertEqual((installed / "SKILL.md").read_text(encoding="utf-8"), "---\nname: mine\n---\n")

    def test_sync_third_party_updates_lock_to_new_commit(self) -> None:
        with TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            upstream = Path(tmp) / "upstream"
            repo.mkdir()
            upstream.mkdir()
            make_git_skill_repo(upstream, "skills/example")
            write(
                repo / "sources" / "third-party-skills.yaml",
                f"""dependencies:
  - name: example
    upstream: {upstream}
    ref: HEAD
    skill_path: skills/example
    targets: [claude]
""",
            )
            write(upstream / "skills" / "example" / "extra.txt", "new\n")
            subprocess.run(["git", "add", "."], cwd=upstream, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "second"], cwd=upstream, check=True)
            new_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=upstream, text=True).strip()

            sync_third_party_skills(repo, update_lock=True, dry_run=False)

            self.assertIn(new_commit, (repo / "sources" / "third-party-skills.lock").read_text())

    def test_import_local_skill_copies_skill_and_updates_metadata(self) -> None:
        with TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            claude_home = Path(tmp) / "claude"
            repo.mkdir()
            write(claude_home / "skills" / "new-skill" / "SKILL.md", "---\nname: new-skill\n---\n")

            import_local_skill(
                repo,
                source="claude",
                name="new-skill",
                homes={"claude": claude_home},
                dry_run=False,
            )

            self.assertTrue((repo / "skills" / "new-skill" / "SKILL.md").exists())
            self.assertIn("new-skill", (repo / "sources" / "personal-skills.yaml").read_text())

    def test_import_local_skill_supports_grok_and_grok_bundled(self) -> None:
        with TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            grok_home = Path(tmp) / "grok"
            grok_bundled_home = Path(tmp) / "grok" / "bundled"
            repo.mkdir()
            write(grok_home / "skills" / "custom" / "SKILL.md", "---\nname: custom\n---\n")
            write(grok_bundled_home / "skills" / "vendor" / "SKILL.md", "---\nname: vendor\n---\n")

            import_local_skill(
                repo,
                source="grok",
                name="custom",
                homes={"grok": grok_home, "grok-bundled": grok_bundled_home},
                dry_run=False,
            )
            import_local_skill(
                repo,
                source="grok-bundled",
                name="vendor",
                homes={"grok": grok_home, "grok-bundled": grok_bundled_home},
                dry_run=False,
            )

            self.assertTrue((repo / "skills" / "custom" / "SKILL.md").exists())
            self.assertTrue((repo / "skills" / "vendor" / "SKILL.md").exists())
            manifest = (repo / "sources" / "personal-skills.yaml").read_text()
            self.assertIn("imported_from: grok", manifest)
            self.assertIn("imported_from: grok-bundled", manifest)

    def test_target_variant_overrides_canonical_owned_skill(self) -> None:
        with TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            agents_home = Path(tmp) / "agents"
            claude_home = Path(tmp) / "claude"
            grok_home = Path(tmp) / "grok"
            repo.mkdir()
            write(agents_home / "skills" / "shared" / "SKILL.md", "canonical\n")
            write(claude_home / "skills" / "shared" / "SKILL.md", "claude variant\n")

            homes = {"agents": agents_home, "claude": claude_home, "grok": grok_home}
            import_local_skill(repo, source="agents", name="shared", homes=homes, dry_run=False)
            import_local_skill(
                repo,
                source="claude",
                name="shared",
                homes=homes,
                dry_run=False,
                variant_for="claude",
            )
            bootstrap(repo, targets=["claude", "grok"], homes=homes, dry_run=False)

            self.assertEqual((claude_home / "skills" / "shared" / "SKILL.md").read_text(), "claude variant\n")
            self.assertEqual((grok_home / "skills" / "shared" / "SKILL.md").read_text(), "canonical\n")
            self.assertIn("variants: [claude]", (repo / "sources" / "personal-skills.yaml").read_text())

    def test_doctor_reports_local_only_and_ignores_exclusions(self) -> None:
        with TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            claude_home = Path(tmp) / "claude"
            codex_home = Path(tmp) / "codex"
            repo.mkdir()
            write(repo / "skills" / "owned" / "SKILL.md", "---\nname: owned\n---\n")
            write(repo / "sources" / "excluded-skills.yaml", "excluded:\n  - internal-skill\n")
            write(claude_home / "skills" / "owned" / "SKILL.md", "---\nname: owned\n---\n")
            write(claude_home / "skills" / "local-only" / "SKILL.md", "---\nname: local-only\n---\n")
            write(claude_home / "skills" / "internal-skill" / "SKILL.md", "---\nname: internal-skill\n---\n")

            report = doctor(repo, homes={"claude": claude_home, "codex": codex_home})

            self.assertIn("local-only", report["local_only"])
            self.assertNotIn("internal-skill", report["local_only"])
            self.assertEqual(report["repo_only"], [])

    def test_doctor_scans_grok_skills(self) -> None:
        with TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            grok_home = Path(tmp) / "grok"
            repo.mkdir()
            write(grok_home / "skills" / "grok-only" / "SKILL.md", "---\nname: grok-only\n---\n")

            report = doctor(repo, homes={"grok": grok_home})

            self.assertIn("grok-only", report["local_only"])


if __name__ == "__main__":
    unittest.main()
