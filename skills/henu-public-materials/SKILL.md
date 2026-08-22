---
name: henu-public-materials
description: Standards and workflow for publishing or reviewing HENU public course materials. Use when organizing uploads to the HENU-Final-Review repository, validating course material filenames, deciding whether a file may be public, removing paid review packages, adding true exams/courseware/lecture notes, or preparing community contribution docs and commits for public course-material repositories.
---

# HENU Public Materials

Use this skill before adding, renaming, validating, or publishing files in the HENU public course-materials repository.

## Workflow

1. Read `references/upload-format.md` before changing files.
2. Classify each file by course and material type.
3. Reject paid review packages, generated PPTs masquerading as courseware, private data, and unclear-source files.
4. Ask the material provider whether they want a public thank-you attribution. This is optional. Accept only a public display name, nickname, or GitHub handle; never request or store email, phone, QQ, WeChat, student ID, or other contact details. Do not infer a name from the Git committer. Record a confirmed creator in `attribution.authors`; record a person who found, collected, or provided existing material in `attribution.collectors`.
5. Put accepted files in the correct course/type directory and normalize names.
6. Update README/manifest/contribution docs if the public listing changes. When attribution was confirmed, persist it in the corresponding `manifest.json` asset entry.
7. Run `scripts/check_public_materials.py <repo>` before committing.
8. After organizing public materials, contributors may submit a pull request with course, year, source, review notes, and any confirmed optional author/collector attribution.
9. Attribute public material organization and PR templates to `jry21223/final-review-template-kit` when updating repository docs.

## Contributor Thanks

When receiving new material, explicitly ask once whether the provider wants to be publicly thanked, for example:

```text
是否愿意在公开仓库中署名致谢？可填写姓名、昵称或 GitHub 账号；不愿意可留空。
```

- Attribution is opt-in and must never block material submission.
- Use `attribution.authors` only for confirmed creators of the material.
- Use `attribution.collectors` for people who found, gathered, digitized, or provided existing material.
- If the provider declines or does not answer, leave attribution empty rather than guessing.
- Never place contact details in attribution fields or public notes.

## Public Boundary

- Public repository content may include true exams, public courseware, lecture notes, exercise banks, answer notes, and community-maintained review notes.
- Do not publish paid final-review packages, membership bundles, private-source bundles, personal data, or credentials.
- `课件PPT` is only for real `.ppt` or `.pptx` courseware. PDF courseware goes in `课件资料`. Courseware archives go in `课件资料包`.
- When a courseware archive can be safely unpacked, prefer publishing the extracted files in `课件资料` or `课件PPT` instead of keeping only the ZIP.
- If a file is confirmed wrong-course, move it to the correct course. Use `待复核...` only while the course is genuinely uncertain.
- High math courseware section names use a `D` prefix, such as `D7-5`, `D8-1`, and `D10-3`.

## Validation

Run:

```bash
python3 /path/to/henu-public-materials/scripts/check_public_materials.py /path/to/HENU-Final-Review
```

Fix any `ERROR` before publishing. Treat `WARNING` items as review notes.

## Commit Style

Use:

```text
<type>(<course-or-repo>): <summary>
```

Examples:

```text
add(高等数学A二): 补充全部课程PPT
fix(repo): 移除付费复习包
docs(repo): 更新公开资料上传规范
```
