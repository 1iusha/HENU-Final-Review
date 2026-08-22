---
name: henu-public-materials
description: Standards and workflow for publishing or reviewing HENU public course materials. Use when organizing uploads to the HENU-Final-Review repository, validating course material filenames, deciding whether a file may be public, removing paid review packages, adding true exams/courseware/lecture notes/textbooks, or preparing community contribution docs and commits for public course-material repositories.
---

# HENU Public Materials

Use this skill before adding, renaming, validating, reviewing, or publishing files in the HENU public course-materials repository.

## Canonical Material Types

New contributions use only these material types:

- `复习讲义`
- `往年真题`
- `课件`
- `题库练习`
- `答案解析`
- `笔记总结`
- `电子版教材`
- `待复核资料`

Do not create format-specific types. A PPT, PPTX, PDF, DOCX, or ZIP that is genuinely courseware is still `课件`; the extension describes the file format, not the material type.

Legacy aliases may remain while the repository is migrated:

- `课件PPT` → `课件`
- `课件资料` → `课件`
- `课件资料包` → `课件`
- `待复核课件PPT` → `待复核资料`

Do not add new files to legacy type folders.

## Workflow

1. Read `references/upload-format.md` and `docs/manifest.md` before changing files.
2. Identify the course and classify every file using one canonical material type.
3. Check the public boundary. Reject paid/member-only packages, generated PPTs masquerading as courseware, credentials, personal data, confirmed wrong-course files, and material that cannot legally or appropriately be redistributed.
4. Ask the material provider once whether they want a public thank-you attribution. Attribution is optional. Accept only a public display name, nickname, or GitHub handle; never request or store email, phone, QQ, WeChat, student ID, or other contact details. Do not infer a name from the Git committer or account metadata.
5. Distinguish attribution roles correctly: a confirmed creator goes in `attribution.authors`; a person who found, collected, digitized, or provided existing material goes in `attribution.collectors`.
6. Put new files in the canonical course/type directory and normalize filenames. If an existing file is under a legacy type directory, do not rename it merely to satisfy this skill unless the task explicitly includes migration.
7. Update `manifest.json` for every added, removed, moved, or renamed material. Keep `role` aligned with the canonical type for new entries and preserve confirmed attribution.
8. After all material bytes are final, run `node scripts/refresh-manifest-metadata.mjs --write`; never hand-write or guess `bytes` or `sha256`.
9. Regenerate and validate repository metadata with `node scripts/update-readme.mjs`, `node scripts/validate-materials.mjs`, and `node scripts/update-readme.mjs --check`.
10. Optionally run `python3 skills/henu-public-materials/scripts/check_public_materials.py <repo>` for supplemental audit checks such as legacy folders, exact-hash duplicates, unlisted top-level material files, and ZIP integrity. The root Node validator is the authoritative validation contract.
11. Open a pull request describing course, canonical type, year/scope, source, review notes, and any confirmed optional author/collector attribution.
12. Attribute public material organization and PR templates to `jry21223/final-review-template-kit` when updating repository docs.

## Contributor Thanks

When receiving new material, explicitly ask once:

```text
是否愿意在公开仓库中署名致谢？可填写姓名、昵称或 GitHub 账号；不愿意可留空。
```

- Attribution is opt-in and must never block material submission.
- Use `attribution.authors` only for confirmed creators of the material.
- Use `attribution.collectors` for people who found, gathered, digitized, or provided existing material.
- If the provider declines or does not answer, omit attribution rather than guessing.
- Never place contact details in attribution fields or public notes.

## Public Boundary

- Public repository content may include true exams, recall exams, publicly distributable courseware, lecture notes, exercise banks, answer notes, community-maintained review notes, and electronic textbooks that are permitted to be redistributed.
- Do not publish paid final-review packages, membership bundles, private-source bundles, pirated commercial textbooks, personal data, or credentials.
- `课件` covers courseware regardless of whether it is `.ppt`, `.pptx`, `.pdf`, `.docx`, or a justified archive. If an archive can be safely unpacked, prefer the useful individual files.
- If a file is confirmed wrong-course, move it to the correct course. Use `待复核资料` only while source, year, course ownership, public boundary, or material identity is genuinely uncertain.
- High math courseware section names use a `D` prefix, such as `D7-5`, `D8-1`, and `D10-3`.

## Validation

Primary repository validation:

```bash
node scripts/refresh-manifest-metadata.mjs --check
node scripts/validate-materials.mjs
node scripts/update-readme.mjs --check
```

Supplemental audit when useful:

```bash
python3 skills/henu-public-materials/scripts/check_public_materials.py /path/to/HENU-Final-Review
```

Fix all `ERROR` results before publishing. Treat `WARNING` results as explicit review items rather than silently ignoring them.

## Commit Style

Use:

```text
<type>(<course-or-repo>): <summary>
```

Examples:

```text
add(高等数学A二): 补充课程课件
fix(repo): 移除重复资料
docs(repo): 收敛资料类型规范
```
