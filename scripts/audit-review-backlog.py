#!/usr/bin/env python3
"""Summarize pending-review materials and why each item is blocked."""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
MANIFEST = ROOT / "manifest.json"

ROLE_ALIASES = {
    "待复核课件PPT": "待复核资料",
}

REASON_LABELS = {
    "source_uncertain": "核对来源与公开边界",
    "year_uncertain": "核对年份/学年",
    "course_uncertain": "核对课程归属",
    "public_boundary_uncertain": "核对是否允许公开",
    "format_lossy": "核对转换/OCR格式损失",
}


def canonical_role(role):
    return ROLE_ALIASES.get(role, role)


def main():
    if not MANIFEST.exists():
        raise SystemExit(f"manifest.json not found under {ROOT}")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    items = []
    by_course = Counter()
    by_reason = Counter()
    by_source_type = Counter()

    for subject in manifest.get("subjects", []):
        subject_name = subject.get("name", "<unknown subject>")
        for asset in subject.get("assets", []):
            if canonical_role(asset.get("role")) != "待复核资料":
                continue

            uncertainty = asset.get("uncertainty") or "missing_uncertainty"
            source_type = asset.get("sourceType") or "missing_source_type"
            by_course[subject_name] += 1
            by_reason[uncertainty] += 1
            by_source_type[source_type] += 1
            items.append((subject_name, uncertainty, source_type, asset))

    print(f"Pending-review assets: {len(items)}")
    print()
    print("By course:")
    for course, count in by_course.most_common():
        print(f"  - {course}: {count}")

    print()
    print("By uncertainty:")
    for reason, count in by_reason.most_common():
        action = REASON_LABELS.get(reason, "补充明确的复核原因")
        print(f"  - {reason}: {count} ({action})")

    print()
    print("By sourceType:")
    for source_type, count in by_source_type.most_common():
        print(f"  - {source_type}: {count}")

    print()
    print("Items:")
    for subject_name, uncertainty, source_type, asset in sorted(
        items,
        key=lambda item: (item[0], item[1], item[3].get("title", "")),
    ):
        title = asset.get("title", "<untitled>")
        note = (asset.get("sourceNote") or "").replace("\n", " ").strip()
        action = REASON_LABELS.get(uncertainty, "补充明确的复核原因")
        print(f"- [{subject_name}] {title}")
        print(f"  uncertainty: {uncertainty}")
        print(f"  sourceType: {source_type}")
        print(f"  action: {action}")
        if note:
            print(f"  note: {note}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
