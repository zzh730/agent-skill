from __future__ import annotations

import argparse
import datetime as dt
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any


DEFAULT_HOMES = {
    "claude": Path.home() / ".claude",
    "codex": Path.home() / ".codex",
    "agents": Path.home() / ".agents",
}


@dataclass(frozen=True)
class AddResult:
    name: str
    resolved_ref: str
    skill_path: str
    dry_run: bool


class SkillRepoError(RuntimeError):
    pass


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def _run(args: list[str], cwd: Path | None = None) -> str:
    try:
        return subprocess.check_output(args, cwd=cwd, text=True, stderr=subprocess.STDOUT).strip()
    except subprocess.CalledProcessError as exc:
        raise SkillRepoError(exc.output.strip() or f"command failed: {' '.join(args)}") from exc


def _today() -> str:
    return dt.date.today().isoformat()


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [part.strip().strip('"').strip("'") for part in inner.split(",")]
    return value


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    data: dict[str, Any] = {}
    current_key: str | None = None
    current_item: dict[str, Any] | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if not raw_line.startswith(" "):
            key = raw_line.rstrip(":")
            current_key = key
            data.setdefault(key, [])
            current_item = None
            continue
        if current_key is None:
            continue

        stripped = raw_line.strip()
        if stripped.startswith("- "):
            value = stripped[2:]
            if ":" in value:
                field, scalar = value.split(":", 1)
                current_item = {field.strip(): _parse_scalar(scalar)}
                data[current_key].append(current_item)
            else:
                data[current_key].append(_parse_scalar(value))
                current_item = None
        elif current_item is not None and ":" in stripped:
            field, scalar = stripped.split(":", 1)
            current_item[field.strip()] = _parse_scalar(scalar)

    return data


def _dump_manifest(data: dict[str, Any]) -> str:
    lines: list[str] = []
    for key, values in data.items():
        lines.append(f"{key}:")
        for value in values:
            if isinstance(value, dict):
                items = list(value.items())
                first_key, first_value = items[0]
                lines.append(f"  - {first_key}: {_format_scalar(first_value)}")
                for field, scalar in items[1:]:
                    lines.append(f"    {field}: {_format_scalar(scalar)}")
            else:
                lines.append(f"  - {_format_scalar(value)}")
    return "\n".join(lines) + ("\n" if lines else "")


def _format_scalar(value: Any) -> str:
    if isinstance(value, list):
        return "[" + ", ".join(str(part) for part in value) + "]"
    text = str(value)
    if not text or any(ch in text for ch in [": ", "#", "[", "]"]):
        return '"' + text.replace('"', '\\"') + '"'
    return text


def save_manifest(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_dump_manifest(data), encoding="utf-8")


def _dependency_by_name(path: Path) -> dict[str, dict[str, Any]]:
    return {dep["name"]: dep for dep in load_manifest(path).get("dependencies", [])}


def _cache_dir(repo: Path, name: str, upstream: str | None = None) -> Path:
    if upstream is None:
        return repo / ".cache" / "third-party" / name
    safe = upstream.rstrip("/").replace("://", "_").replace("/", "_").replace(":", "_")
    if safe.endswith(".git"):
        safe = safe[:-4]
    return repo / ".cache" / "third-party" / safe


def _clone_or_fetch(upstream: str, checkout: Path) -> None:
    if checkout.exists():
        _run(["git", "fetch", "--quiet", "--tags", "origin"], cwd=checkout)
        return
    checkout.parent.mkdir(parents=True, exist_ok=True)
    _run(["git", "clone", "--quiet", upstream, str(checkout)])


def _resolve_ref(repo: Path, name: str, upstream: str, ref: str, *, dry_run: bool = False) -> tuple[str, Path, TemporaryDirectory[str] | None]:
    if dry_run:
        temp = TemporaryDirectory()
        checkout = Path(temp.name) / name
        _clone_or_fetch(upstream, checkout)
        commit = _run(["git", "rev-parse", ref], cwd=checkout)
        return commit, checkout, temp

    checkout = _cache_dir(repo, name, upstream)
    _clone_or_fetch(upstream, checkout)
    commit = _run(["git", "rev-parse", ref], cwd=checkout)
    return commit, checkout, None


def _checkout_ref(checkout: Path, ref: str) -> None:
    _run(["git", "checkout", "--quiet", ref], cwd=checkout)


def _validate_skill_path(checkout: Path, skill_path: str) -> None:
    if not (checkout / skill_path / "SKILL.md").exists():
        raise SkillRepoError(f"SKILL.md not found at upstream path: {skill_path}")


def add_third_party_skill(
    repo: Path,
    *,
    name: str,
    upstream: str,
    ref: str,
    skill_path: str,
    targets: list[str],
    dry_run: bool,
    install: bool,
    homes: dict[str, Path] | None = None,
) -> AddResult:
    commit, checkout, temp = _resolve_ref(repo, name, upstream, ref, dry_run=dry_run)
    try:
        _checkout_ref(checkout, commit)
        _validate_skill_path(checkout, skill_path)
    finally:
        if temp is not None:
            temp.cleanup()

    if dry_run:
        return AddResult(name=name, resolved_ref=commit, skill_path=skill_path, dry_run=True)

    manifest_path = repo / "sources" / "third-party-skills.yaml"
    lock_path = repo / "sources" / "third-party-skills.lock"
    manifest = load_manifest(manifest_path)
    deps = [dep for dep in manifest.get("dependencies", []) if dep.get("name") != name]
    deps.append(
        {
            "name": name,
            "upstream": upstream,
            "ref": ref,
            "skill_path": skill_path,
            "targets": targets,
        }
    )
    manifest["dependencies"] = sorted(deps, key=lambda dep: dep["name"])
    save_manifest(manifest_path, manifest)

    lock = load_manifest(lock_path)
    locked = [dep for dep in lock.get("dependencies", []) if dep.get("name") != name]
    locked.append(
        {
            "name": name,
            "upstream": upstream,
            "resolved_ref": commit,
            "resolved_at": _today(),
        }
    )
    lock["dependencies"] = sorted(locked, key=lambda dep: dep["name"])
    save_manifest(lock_path, lock)

    if install:
        bootstrap(repo, targets=targets, homes=homes, dry_run=False)

    return AddResult(name=name, resolved_ref=commit, skill_path=skill_path, dry_run=False)


def sync_third_party_skills(repo: Path, *, update_lock: bool, dry_run: bool) -> list[str]:
    manifest_path = repo / "sources" / "third-party-skills.yaml"
    lock_path = repo / "sources" / "third-party-skills.lock"
    deps = load_manifest(manifest_path).get("dependencies", [])
    lock_entries: list[dict[str, Any]] = []
    actions: list[str] = []

    for dep in deps:
        commit, checkout, temp = _resolve_ref(repo, dep["name"], dep["upstream"], dep.get("ref", "HEAD"), dry_run=dry_run)
        try:
            _checkout_ref(checkout, commit)
            _validate_skill_path(checkout, dep["skill_path"])
        finally:
            if temp is not None:
                temp.cleanup()
        actions.append(f"resolved {dep['name']} -> {commit}")
        lock_entries.append(
            {
                "name": dep["name"],
                "upstream": dep["upstream"],
                "resolved_ref": commit,
                "resolved_at": _today(),
            }
        )

    if update_lock and not dry_run:
        save_manifest(lock_path, {"dependencies": sorted(lock_entries, key=lambda dep: dep["name"])})

    return actions


def _target_skill_dir(homes: dict[str, Path], target: str) -> Path:
    return homes[target] / "skills"


def _copy_dir(src: Path, dest: Path) -> None:
    if dest.exists():
        if dest.is_symlink() or dest.is_file():
            dest.unlink()
        else:
            shutil.rmtree(dest)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns(".git", "__pycache__", ".DS_Store"))


def _owned_skill_dirs(repo: Path) -> list[Path]:
    skills_dir = repo / "skills"
    if not skills_dir.exists():
        return []
    return sorted(path for path in skills_dir.iterdir() if (path / "SKILL.md").exists())


def bootstrap(
    repo: Path,
    *,
    targets: list[str],
    homes: dict[str, Path] | None = None,
    dry_run: bool,
) -> list[str]:
    homes = {**DEFAULT_HOMES, **(homes or {})}
    actions: list[str] = []

    for skill_dir in _owned_skill_dirs(repo):
        for target in targets:
            if target not in homes:
                continue
            dest = _target_skill_dir(homes, target) / skill_dir.name
            actions.append(f"install owned skill {skill_dir.name} -> {target}")
            if not dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                _copy_dir(skill_dir, dest)

    if "claude" in targets:
        command_dir = repo / "commands" / "claude"
        if command_dir.exists():
            for command in sorted(command_dir.glob("*.md")):
                actions.append(f"install claude command {command.name}")
                if not dry_run:
                    dest = homes["claude"] / "commands" / command.name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(command, dest)

    manifest = load_manifest(repo / "sources" / "third-party-skills.yaml")
    locked = _dependency_by_name(repo / "sources" / "third-party-skills.lock")
    for dep in manifest.get("dependencies", []):
        dep_targets = [target for target in dep.get("targets", []) if target in targets]
        if not dep_targets:
            continue
        lock = locked.get(dep["name"])
        if lock is None:
            raise SkillRepoError(f"missing lock entry for third-party skill: {dep['name']}")
        for target in dep_targets:
            actions.append(f"install third-party skill {dep['name']} -> {target}")
        if dry_run:
            continue
        checkout = _cache_dir(repo, dep["name"], dep["upstream"])
        _clone_or_fetch(dep["upstream"], checkout)
        _checkout_ref(checkout, lock["resolved_ref"])
        source = checkout / dep["skill_path"]
        _validate_skill_path(checkout, dep["skill_path"])
        for target in dep_targets:
            dest = _target_skill_dir(homes, target) / dep["name"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            _copy_dir(source, dest)

    return actions


def import_local_skill(
    repo: Path,
    *,
    source: str,
    name: str,
    homes: dict[str, Path] | None = None,
    dry_run: bool,
    force: bool = False,
) -> list[str]:
    homes = {**DEFAULT_HOMES, **(homes or {})}
    if source not in homes:
        raise SkillRepoError(f"unknown source: {source}")
    src = _target_skill_dir(homes, source) / name
    if not (src / "SKILL.md").exists():
        raise SkillRepoError(f"local skill not found: {src}")
    dest = repo / "skills" / name
    if dest.exists() and not force:
        raise SkillRepoError(f"repo skill already exists: {name}; pass --force to replace")

    actions = [f"import {source}:{name} -> skills/{name}"]
    if dry_run:
        return actions

    dest.parent.mkdir(parents=True, exist_ok=True)
    _copy_dir(src, dest)
    personal_path = repo / "sources" / "personal-skills.yaml"
    personal = load_manifest(personal_path)
    skills = [item for item in personal.get("skills", []) if item.get("name") != name]
    skills.append({"name": name, "imported_from": source, "imported_at": _today()})
    personal["skills"] = sorted(skills, key=lambda item: item["name"])
    save_manifest(personal_path, personal)
    return actions


def _skill_names_in(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {item.name for item in path.iterdir() if (item / "SKILL.md").exists()}


def _excluded_names(repo: Path) -> set[str]:
    return set(load_manifest(repo / "sources" / "excluded-skills.yaml").get("excluded", []))


def doctor(repo: Path, *, homes: dict[str, Path] | None = None) -> dict[str, list[str]]:
    homes = {**DEFAULT_HOMES, **(homes or {})}
    owned = {path.name for path in _owned_skill_dirs(repo)}
    third_party = {dep["name"] for dep in load_manifest(repo / "sources" / "third-party-skills.yaml").get("dependencies", [])}
    excluded = _excluded_names(repo)

    local: set[str] = set()
    for target in ("claude", "codex", "agents"):
        if target in homes:
            local.update(_skill_names_in(_target_skill_dir(homes, target)))

    expected = owned | third_party
    report = {
        "local_only": sorted(local - expected - excluded),
        "repo_only": sorted(owned - local),
        "third_party_missing_lock": [],
    }
    locked = _dependency_by_name(repo / "sources" / "third-party-skills.lock")
    for dep in sorted(third_party):
        if dep not in locked:
            report["third_party_missing_lock"].append(dep)
    return report


def _parse_targets(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _print_actions(actions: list[str]) -> int:
    for action in actions:
        print(action)
    return 0


def main_add(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--upstream", required=True)
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--skill-path", required=True)
    parser.add_argument("--targets", default="claude,codex")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args(argv)
    result = add_third_party_skill(
        repo_root_from_script(),
        name=args.name,
        upstream=args.upstream,
        ref=args.ref,
        skill_path=args.skill_path,
        targets=_parse_targets(args.targets),
        dry_run=args.dry_run,
        install=args.install,
    )
    print(f"{'would add' if result.dry_run else 'added'} {result.name} -> {result.resolved_ref}")
    return 0


def main_sync(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--update-lock", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    return _print_actions(sync_third_party_skills(repo_root_from_script(), update_lock=args.update_lock, dry_run=args.dry_run))


def main_bootstrap(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--targets", default="claude,codex")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    return _print_actions(bootstrap(repo_root_from_script(), targets=_parse_targets(args.targets), dry_run=args.dry_run))


def main_import(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="source", required=True, choices=["claude", "codex", "agents"])
    parser.add_argument("--name", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    return _print_actions(import_local_skill(repo_root_from_script(), source=args.source, name=args.name, dry_run=args.dry_run, force=args.force))


def main_doctor(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args(argv)
    report = doctor(repo_root_from_script())
    for key, values in report.items():
        print(f"{key}:")
        for value in values:
            print(f"  - {value}")
    return 1 if report["third_party_missing_lock"] else 0


def run_cli(entrypoint: str) -> int:
    try:
        return {
            "add-third-party-skill": main_add,
            "sync-third-party-skills": main_sync,
            "bootstrap": main_bootstrap,
            "import-local-skill": main_import,
            "doctor": main_doctor,
        }[entrypoint]()
    except SkillRepoError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
