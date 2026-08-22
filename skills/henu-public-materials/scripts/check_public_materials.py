#!/usr/bin/env python3
"""Supplemental repository audit for HENU public materials.

The authoritative validation contract lives in scripts/validate-materials.mjs.
This helper intentionally checks things that are useful as an extra audit:
legacy folder usage, review backlog, material files missing from manifest,
private source-path fields, exact-hash duplicates recorded in manifest,
temporary names, ZIP integrity, and (with --deep) conservative near-duplicate
candidates based on normalized names and Office document text.
"""

import json
import re
import sys
import zipfile
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from xml.etree import ElementTree

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

CHINESE_NUMBERS = {
    "二十": "20",
    "十九": "19",
    "十八": "18",
    "十七": "17",
    "十六": "16",
    "十五": "15",
    "十四": "14",
    "十三": "13",
    "十二": "12",
    "十一": "11",
    "十": "10",
    "九": "9",
    "八": "8",
    "七": "7",
    "六": "6",
    "五": "5",
    "四": "4",
    "三": "3",
    "二": "2",
    "一": "1",
}

VERSION_SUFFIX_PATTERNS = [
    re.compile(r"(?:[_-]?最新版)$", re.I),
    re.compile(r"(?:[_-]?正式版?)$", re.I),
    re.compile(r"(?:[_-]?精简版)$", re.I),
    re.compile(r"(?:[_-]?删减版)$", re.I),
    re.compile(r"(?:[_-]?文字版)$", re.I),
    re.compile(r"(?:[_-]?V\d+)$", re.I),
    re.compile(r"(?:[_-]?0?\d+)$", re.I),
]

OFFICE_EXTENSIONS = {".pptx", ".docx"}


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


def iter_assets(manifest):
    for subject in manifest.get("subjects", []):
        subject_name = subject.get("name", "<unknown subject>")
        for asset in subject.get("assets", []):
            yield subject_name, asset


def audit_manifest(root, manifest, issues):
    manifest_paths = set()
    hashes = defaultdict(list)
    legacy_role_counts = defaultdict(int)
    review_counts = defaultdict(int)

    for subject_name, asset in iter_assets(manifest):
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


def strip_course_and_role(title, subject):
    stem = Path(title).stem
    if stem.startswith(f"{subject}_"):
        stem = stem[len(subject) + 1 :]

    for prefix in (
        "复习讲义_",
        "真题_",
        "课件_",
        "题库练习_",
        "答案解析_",
        "笔记总结_",
        "笔记_",
        "电子版教材_",
        "待复核_",
    ):
        if stem.startswith(prefix):
            stem = stem[len(prefix) :]
            break
    return stem


def normalize_candidate_stem(title, subject):
    stem = strip_course_and_role(title, subject)

    # Normalize chapter numbers such as 第一章 and 第十一章 to 第1章 / 第11章.
    for chinese, arabic in CHINESE_NUMBERS.items():
        stem = stem.replace(f"第{chinese}章", f"第{arabic}章")

    # Remove only explicit version/export suffixes. Do not erase semantic words.
    changed = True
    while changed:
        changed = False
        for pattern in VERSION_SUFFIX_PATTERNS:
            next_stem = pattern.sub("", stem)
            if next_stem != stem:
                stem = next_stem
                changed = True

    stem = re.sub(r"[\s_\-—（）()【】\[\]、，,.]+", "", stem).lower()
    return stem


def audit_name_candidates(root, manifest, issues):
    groups = defaultdict(list)
    for subject_name, asset in iter_assets(manifest):
        public_path = asset.get("publicPath")
        title = asset.get("title")
        if not public_path or not title:
            continue
        role = canonical_type(asset.get("role"))
        if role == "待复核资料":
            continue
        key = (subject_name, role, normalize_candidate_stem(title, subject_name))
        if key[2]:
            groups[key].append(public_path)

    for (subject_name, role, normalized), paths in sorted(groups.items()):
        unique_paths = sorted(set(paths))
        if len(unique_paths) < 2:
            continue
        add_issue(
            issues,
            "REVIEW",
            root / "manifest.json",
            f"near-duplicate name candidate [{subject_name}/{role}] '{normalized}': {', '.join(unique_paths)}",
        )


def extract_office_text(path):
    suffix = path.suffix.lower()
    if suffix not in OFFICE_EXTENSIONS:
        return ""

    prefixes = ("ppt/slides/slide",) if suffix == ".pptx" else ("word/document.xml",)
    chunks = []
    try:
        with zipfile.ZipFile(path) as archive:
            names = sorted(
                name
                for name in archive.namelist()
                if name.endswith(".xml") and any(name.startswith(prefix) for prefix in prefixes)
            )
            for name in names:
                try:
                    root = ElementTree.fromstring(archive.read(name))
                except ElementTree.ParseError:
                    continue
                for node in root.iter():
                    if node.text:
                        chunks.append(node.text)
    except (OSError, zipfile.BadZipFile):
        return ""

    text = "".join(chunks)
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", text).lower()


def audit_office_similarity(root, manifest, issues):
    groups = defaultdict(list)
    cache = {}

    for subject_name, asset in iter_assets(manifest):
        public_path = asset.get("publicPath")
        if not public_path:
            continue
        role = canonical_type(asset.get("role"))
        if role == "待复核资料":
            continue
        path = root.joinpath(*public_path.split("/"))
        if path.suffix.lower() not in OFFICE_EXTENSIONS or not path.exists():
            continue
        groups[(subject_name, role)].append(path)

    for (subject_name, role), paths in sorted(groups.items()):
        for index, left in enumerate(paths):
            for right in paths[index + 1 :]:
                # A wildly different byte size is unlikely to be a duplicate Office export.
                left_size = left.stat().st_size
                right_size = right.stat().st_size
                if min(left_size, right_size) == 0:
                    continue
                if max(left_size, right_size) / min(left_size, right_size) > 2.5:
                    continue

                left_text = cache.setdefault(left, extract_office_text(left))
                right_text = cache.setdefault(right, extract_office_text(right))
                if min(len(left_text), len(right_text)) < 300:
                    continue

                # Cap input so deep audit stays predictable on large decks.
                ratio = SequenceMatcher(
                    None,
                    left_text[:30000],
                    right_text[:30000],
                    autojunk=False,
                ).ratio()
                if ratio < 0.92:
                    continue

                add_issue(
                    issues,
                    "REVIEW",
                    root,
                    f"high Office-text similarity {ratio:.1%} [{subject_name}/{role}]: "
                    f"{left.relative_to(root)} <-> {right.relative_to(root)}",
                )


def check_repo(root, deep=False):
    issues = []
    manifest = load_manifest(root, issues)
    if manifest is None:
        return issues

    manifest_paths = audit_manifest(root, manifest, issues)
    audit_tree(root, manifest_paths, issues)
    if deep:
        audit_name_candidates(root, manifest, issues)
        audit_office_similarity(root, manifest, issues)
    return issues


def main():
    args = [arg for arg in sys.argv[1:] if arg != "--deep"]
    deep = "--deep" in sys.argv[1:]
    if len(args) != 1:
        print("usage: check_public_materials.py <repo-root> [--deep]", file=sys.stderr)
        return 2

    root = Path(args[0]).resolve()
    issues = check_repo(root, deep=deep)

    for issue in issues:
        print(f"{issue['level']}: {issue['path']}: {issue['message']}")

    return 1 if any(issue["level"] == "ERROR" for issue in issues) else 0


if __name__ == "__main__":
    raise SystemExit(main())
