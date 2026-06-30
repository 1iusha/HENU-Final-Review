#!/usr/bin/env python3
import json
import sys
import zipfile
from pathlib import Path

ALLOWED_TYPE_DIRS = {
    "复习讲义",
    "往年真题",
    "课件PPT",
    "课件资料",
    "课件资料包",
    "题库练习",
    "答案解析",
    "笔记总结",
    "待复核课件PPT",
    "待复核资料",
}

ILLEGAL_NAME_PARTS = {
    "__MACOSX",
    ".DS_Store",
    "完整复习包",
    "期末复习包.zip",
    "final_final",
    "未命名",
}

MAINTENANCE_DIRS = {
    ".github",
    "docs",
    "skills",
}


def add_issue(issues, level, path, message):
    issues.append({"level": level, "path": str(path), "message": message})


def check_repo(root):
    issues = []
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        add_issue(issues, "ERROR", manifest_path, "missing manifest.json")
    else:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        for subject in data.get("subjects", []):
            for asset in subject.get("assets", []):
                if "sourcePath" in asset or "sourceRepo" in asset:
                    add_issue(issues, "ERROR", manifest_path, "manifest must not expose private source paths")
                public_path = root / asset.get("publicPath", "")
                if not public_path.exists():
                    add_issue(issues, "ERROR", public_path, "manifest publicPath does not exist")

    for path in root.rglob("*"):
        if ".git" in path.parts:
            continue
        rel = path.relative_to(root)
        if rel.parts and rel.parts[0] in MAINTENANCE_DIRS:
            continue
        if path.is_dir() and len(rel.parts) == 2 and rel.parts[1] not in ALLOWED_TYPE_DIRS:
            add_issue(issues, "ERROR", rel, "unknown material type directory")
        for part in rel.parts:
            if part in ILLEGAL_NAME_PARTS or any(token in part for token in ILLEGAL_NAME_PARTS):
                add_issue(issues, "ERROR", rel, f"disallowed public material name token: {part}")
        if path.is_file() and path.suffix.lower() == ".zip":
            try:
                with zipfile.ZipFile(path) as zf:
                    bad = zf.testzip()
                    if bad is not None:
                        add_issue(issues, "ERROR", rel, f"corrupt zip member: {bad}")
                    for name in zf.namelist():
                        if "__MACOSX" in name or "/._" in name or name.startswith("._"):
                            add_issue(issues, "ERROR", rel, "zip contains macOS resource-fork metadata")
            except zipfile.BadZipFile:
                add_issue(issues, "ERROR", rel, "invalid zip file")

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
