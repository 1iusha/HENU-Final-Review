#!/usr/bin/env python3
"""Supplemental repository audit for HENU public materials.

The authoritative validation contract lives in scripts/validate-materials.mjs.
This helper intentionally checks only things that are useful as an extra audit:
legacy folder usage, review backlog, material files missing from manifest,
private source-path fields, exact-hash duplicates recorded in manifest,
temporary names, and ZIP integrity.

For targeted near-duplicate analysis, run scripts/audit-material-duplicates.py.
"""

import json
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

LEGACY_TYPE_ALIASES = {
    "课件PPT": "课件",
    "课件资料": "课件",
    "课件资料包": "课件",
    "待复核课件PPT": "待复核资料",
}

MAINTENANCE_DIRS = {
    ".git",
    ".github",
    "docs",
    "scripts",
    "skills",
    "tests",
    ".public-materials-export",
}

TEMP_NAME_TOKENS = {
    "副本",
    "final_final",
    "未命名",
    "新建文件",
}


def add_issue(issues, level, path, message):
    issues.append({"level": level, "path": str(path), "message": message})


def canonical_type(role):
    return LEGACY_TYPE_ALIASES.get(role, role)


def load_manifest(root, issues):
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        add_issue(issues, "ERROR", manifest_path, "missing manifest.json")
        return None

    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        add_issue(issues, "ERROR", manifest_path, f"cannot read manifest.json: {exc}")
        return None


def audit_manifest(root, manifest, issues):
    manifest_paths = set()
    hashes = defaultdict(list)
    legacy_role_counts = defaultdict(int)
    review_counts = defaultdict(int)

    for subject in manifest.get("subjects", []):
        subject_name = subject.get("name", "<unknown subject>")
        for asset in subject.get("assets", []):
            public_path = asset.get("publicPath")
            if public_path:
                manifest_paths.add(public_path)

            digest = asset.get("sha256")
            if digest and public_path:
                hashes[digest].append(public_path)

            if "sourcePath" in asset or "sourceRepo" in asset:
                add_issue(
                    issues,
                    "ERROR",
                    root / "manifest.json",
                    f"{public_path or '<unknown asset>'}: manifest must not expose private source paths",
                )

            role = asset.get("role")
            if role in LEGACY_TYPE_ALIASES:
                legacy_role_counts[role] += 1
            if canonical_type(role) == "待复核资料":
                review_counts[subject_name] += 1

    if legacy_role_counts:
        summary = ", ".join(
            f"{role}→{LEGACY_TYPE_ALIASES[role]}: {count}"
            for role, count in sorted(legacy_role_counts.items())
        )
        add_issue(
            issues,
            "WARNING",
            root / "manifest.json",
            f"legacy manifest roles remain for migration: {summary}",
        )

    if review_counts:
        total = sum(review_counts.values())
        summary = ", ".join(
            f"{subject}: {count}"
            for subject, count in sorted(review_counts.items(), key=lambda item: (-item[1], item[0]))
        )
        add_issue(
            issues,
            "WARNING",
            root / "manifest.json",
            f"pending-review backlog: total {total}; {summary}",
        )

    for digest, paths in hashes.items():
        unique_paths = sorted(set(paths))
        if len(unique_paths) > 1:
            add_issue(
                issues,
                "WARNING",
                root / "manifest.json",
                f"exact duplicate SHA-256 {digest[:12]}… is referenced by: {', '.join(unique_paths)}",
            )

    return manifest_paths


def audit_tree(root, manifest_paths, issues):
    legacy_folder_counts = defaultdict(int)

    for course_dir in root.iterdir():
        if not course_dir.is_dir() or course_dir.name in MAINTENANCE_DIRS:
            continue

        for type_dir in course_dir.iterdir():
            if not type_dir.is_dir():
                continue

            if type_dir.name in LEGACY_TYPE_ALIASES:
                legacy_folder_counts[type_dir.name] += 1

            for path in type_dir.rglob("*"):
                if not path.is_file():
                    continue

                rel = path.relative_to(root)

                if any(token in path.name for token in TEMP_NAME_TOKENS):
                    add_issue(issues, "WARNING", rel, "filename looks temporary or unnormalized")

                # Supporting assets may legitimately live below a nested assets/ folder.
                # Only require direct material files (course/type/file) to appear in manifest.
                if len(rel.parts) == 3 and str(rel).replace("\\", "/") not in manifest_paths:
                    add_issue(issues, "WARNING", rel, "material file is not listed in manifest.json")

                if path.suffix.lower() != ".zip":
                    continue

                try:
                    with zipfile.ZipFile(path) as archive:
                        bad = archive.testzip()
                        if bad is not None:
                            add_issue(issues, "ERROR", rel, f"corrupt zip member: {bad}")
                        if any(
                            "__MACOSX" in name or "/._" in name or name.startswith("._")
                            for name in archive.namelist()
                        ):
                            add_issue(issues, "WARNING", rel, "zip contains macOS resource-fork metadata")
                except zipfile.BadZipFile:
                    add_issue(issues, "ERROR", rel, "invalid zip file")

    if legacy_folder_counts:
        summary = ", ".join(
            f"{role}→{LEGACY_TYPE_ALIASES[role]}: {count} folders"
            for role, count in sorted(legacy_folder_counts.items())
        )
        add_issue(
            issues,
            "WARNING",
            root,
            f"legacy type folders remain for migration: {summary}",
        )


def check_repo(root):
    issues = []
    manifest = load_manifest(root, issues)
    if manifest is None:
        return issues

    manifest_paths = audit_manifest(root, manifest, issues)
    audit_tree(root, manifest_paths, issues)
    return issues


def main():
    if len(sys.argv) != 2:
        print("usage: check_public_materials.py <repo-root>", file=sys.stderr)
        return 2
    root = Path(sys.argv[1]).resolve()
    issues = check_repo(root)

    for issue in issues:
        print(f"{issue['level']}: {issue['path']}: {issue['message']}")

    return 1 if any(issue["level"] == "ERROR" for issue in issues) else 0


if __name__ == "__main__":
    raise SystemExit(main())
