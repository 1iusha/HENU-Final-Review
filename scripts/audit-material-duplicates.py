#!/usr/bin/env python3
"""Find conservative duplicate/near-duplicate material candidates.

This script never mutates files. It uses:
1. exact SHA-256 values already stored in manifest.json;
2. normalized filename stems for all formats;
3. extracted text similarity for related .pptx/.docx pairs only.

PDFs are intentionally not content-parsed here; they are reported only from
hash/name evidence and require manual review before deletion.
"""

import json
import re
import sys
import zipfile
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
MANIFEST = ROOT / "manifest.json"
OFFICE_EXTENSIONS = {".pptx", ".docx"}

ROLE_ALIASES = {
    "课件PPT": "课件",
    "课件资料": "课件",
    "课件资料包": "课件",
    "待复核课件PPT": "待复核资料",
}

CHINESE_NUMBERS = {
    "二十": "20", "十九": "19", "十八": "18", "十七": "17", "十六": "16",
    "十五": "15", "十四": "14", "十三": "13", "十二": "12", "十一": "11",
    "十": "10", "九": "9", "八": "8", "七": "7", "六": "6", "五": "5",
    "四": "4", "三": "3", "二": "2", "一": "1",
}

VERSION_SUFFIXES = [
    r"[_-]?最新版$",
    r"[_-]?正式版?$",
    r"[_-]?精简版$",
    r"[_-]?删减版$",
    r"[_-]?文字版$",
    r"[_-]?V\d+$",
    r"_0?\d+$",
]


def canonical_role(value):
    return ROLE_ALIASES.get(value, value)


def iter_assets(manifest):
    for subject in manifest.get("subjects", []):
        name = subject.get("name", "<unknown subject>")
        for asset in subject.get("assets", []):
            if asset.get("publicPath") and asset.get("title"):
                yield name, asset


def semantic_stem(subject, title):
    stem = Path(title).stem
    if stem.startswith(subject + "_"):
        stem = stem[len(subject) + 1 :]

    for prefix in (
        "复习讲义_", "真题_", "课件_", "题库练习_", "答案解析_",
        "笔记总结_", "笔记_", "电子版教材_", "待复核_",
    ):
        if stem.startswith(prefix):
            stem = stem[len(prefix) :]
            break

    for chinese, arabic in CHINESE_NUMBERS.items():
        stem = stem.replace(f"第{chinese}章", f"第{arabic}章")

    changed = True
    while changed:
        changed = False
        for pattern in VERSION_SUFFIXES:
            next_stem = re.sub(pattern, "", stem, flags=re.I)
            if next_stem != stem:
                stem = next_stem
                changed = True

    return re.sub(r"[\s_\-—（）()【】\[\]、，,.]+", "", stem).lower()


def related_names(left, right):
    if not left or not right:
        return False
    if left == right:
        return True
    if min(len(left), len(right)) >= 4 and (left in right or right in left):
        return True
    return SequenceMatcher(None, left, right, autojunk=False).ratio() >= 0.72


def extract_office_text(path):
    suffix = path.suffix.lower()
    if suffix not in OFFICE_EXTENSIONS:
        return ""

    prefix = "ppt/slides/slide" if suffix == ".pptx" else "word/document.xml"
    chunks = []
    try:
        with zipfile.ZipFile(path) as archive:
            names = sorted(
                name for name in archive.namelist()
                if name.endswith(".xml") and name.startswith(prefix)
            )
            for name in names:
                try:
                    xml_root = ElementTree.fromstring(archive.read(name))
                except ElementTree.ParseError:
                    continue
                chunks.extend(node.text for node in xml_root.iter() if node.text)
    except (OSError, zipfile.BadZipFile):
        return ""

    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", "".join(chunks)).lower()


def main():
    if not MANIFEST.exists():
        raise SystemExit(f"manifest.json not found under {ROOT}")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assets = list(iter_assets(manifest))

    exact_hashes = defaultdict(list)
    name_groups = defaultdict(list)
    office_groups = defaultdict(list)

    for subject, asset in assets:
        role = canonical_role(asset.get("role"))
        path = asset["publicPath"]
        digest = asset.get("sha256")
        if digest:
            exact_hashes[digest].append(path)

        stem = semantic_stem(subject, asset["title"])
        if stem:
            name_groups[(subject, role, stem)].append(path)

        full_path = ROOT.joinpath(*path.split("/"))
        if role != "待复核资料" and full_path.suffix.lower() in OFFICE_EXTENSIONS and full_path.exists():
            office_groups[(subject, role)].append((full_path, stem))

    findings = []

    for digest, paths in exact_hashes.items():
        unique = sorted(set(paths))
        if len(unique) > 1:
            findings.append(("EXACT", 1.0, f"sha256={digest[:12]}…", unique))

    for (subject, role, stem), paths in sorted(name_groups.items()):
        unique = sorted(set(paths))
        if len(unique) > 1:
            findings.append(("NAME", None, f"{subject}/{role} stem={stem}", unique))

    text_cache = {}
    seen_pairs = set()
    for (subject, role), entries in sorted(office_groups.items()):
        for index, (left, left_stem) in enumerate(entries):
            for right, right_stem in entries[index + 1 :]:
                if not related_names(left_stem, right_stem):
                    continue

                pair_key = tuple(sorted((str(left), str(right))))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                left_size = left.stat().st_size
                right_size = right.stat().st_size
                if not left_size or not right_size:
                    continue
                if max(left_size, right_size) / min(left_size, right_size) > 3.0:
                    continue

                left_text = text_cache.setdefault(left, extract_office_text(left))
                right_text = text_cache.setdefault(right, extract_office_text(right))
                if min(len(left_text), len(right_text)) < 300:
                    continue

                ratio = SequenceMatcher(
                    None,
                    left_text[:25000],
                    right_text[:25000],
                    autojunk=False,
                ).ratio()
                if ratio >= 0.88:
                    findings.append((
                        "OFFICE_TEXT",
                        ratio,
                        f"{subject}/{role}",
                        [str(left.relative_to(ROOT)), str(right.relative_to(ROOT))],
                    ))

    order = {"EXACT": 0, "OFFICE_TEXT": 1, "NAME": 2}
    findings.sort(key=lambda item: (order[item[0]], -(item[1] or 0), item[2], item[3]))

    print(f"Scanned {len(assets)} manifest assets.")
    print(f"Found {len(findings)} conservative duplicate/near-duplicate candidate group(s).")
    print()

    for kind, score, label, paths in findings:
        score_text = f" similarity={score:.1%}" if score is not None and kind != "EXACT" else ""
        print(f"[{kind}]{score_text} {label}")
        for path in paths:
            print(f"  - {path}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
