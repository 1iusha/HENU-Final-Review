# HENU Public Materials Upload Format

## Course Folder

Use the official Chinese course name as the top-level folder. Do not maintain a hard-coded course allowlist in this skill: the repository may add courses over time. The course folder, `manifest.json` subject name, and each asset's `subject` must agree.

Add a new course only when the uploaded material clearly belongs to that course.

## Canonical Material Types

New contributions use only these folders under each course:

- `复习讲义`
- `往年真题`
- `课件`
- `题库练习`
- `答案解析`
- `笔记总结`
- `电子版教材`
- `待复核资料`

The material type describes what the content is, not its file format. For example, PPT, PPTX, PDF, DOCX, and a justified ZIP may all be `课件`.

### Legacy aliases

The repository still contains historical folders that are supported during migration only:

- `课件PPT` → `课件`
- `课件资料` → `课件`
- `课件资料包` → `课件`
- `待复核课件PPT` → `待复核资料`

Do not create new files or new folders using these legacy names. Existing material can be migrated separately without blocking unrelated contributions.

Do not create `完整复习包`, `付费资料`, `会员资料`, or other paid-package directories in the public repository.

## Filename Pattern

Use:

```text
课程名_资料类型_关键信息[_年份或版本].扩展名
```

Examples:

```text
高等数学A（二）_课件_D8-1向量及其线性运算.ppt
离散数学_真题_软件学院23级.pdf
大学物理_课件_2023高斯定理.pdf
面向对象程序设计Java_课件_第1章Java概述.pptx
数据库系统_教材_数据库系统概论.pdf
```

## Character Rules

- Use the Chinese course name; do not use pinyin abbreviations for the course name.
- Use `、` for multiple section numbers, such as `D7-1、2、3`.
- High math section filenames use a `D` prefix, such as `D7-5`, `D8-1`, and `D10-3`; do not mix in bare `7-5` or `8-1` names.
- Use suffixes for meaningful versions, such as `_02`, `_精简版`, `_删减版`.
- Avoid ASCII commas, slashes, colons, question marks, asterisks, quotes, angle brackets, and backslashes in filenames.
- Avoid temporary names such as `副本`, `未命名`, `新建文件`, and `final_final`.

## Contributor Attribution and Thanks

Before finalizing a new material contribution, ask the material provider once whether they want to be publicly thanked:

```text
是否愿意在公开仓库中署名致谢？可填写姓名、昵称或 GitHub 账号；不愿意可留空。
```

- Attribution is optional and must not block submission.
- Only store a confirmed public display name, nickname, or GitHub handle.
- Never request or store email, phone, QQ, WeChat, student ID, or other contact details for attribution.
- Do not infer attribution from the Git committer, uploader, file metadata, or account email.
- If the person created the material, use `attribution.authors`.
- If the person found, collected, digitized, or provided existing material, use `attribution.collectors`.
- If the provider declines or does not answer, omit attribution rather than guessing.

Example:

```json
{
  "attribution": {
    "collectors": ["资料提供者公开昵称"]
  }
}
```

## Public/Private Boundary

Allowed when the source and redistribution boundary are clear:

- True exams and recall exams.
- Public courseware and lecture notes.
- Course exercise banks and answer notes.
- Community-maintained review notes.
- Electronic textbooks that are open, authorized, or otherwise permitted to be redistributed.

Not allowed:

- Paid final-review packages or membership bundles.
- Pirated or clearly unauthorized commercial textbooks.
- AI-generated PPTs presented as real courseware.
- Personal data, account information, scores, name lists, or credentials.
- Confirmed wrong-course files left in the wrong course.
- Unclear-source or unclear-public-boundary files in a formal type folder; use `待复核资料` while genuinely unresolved.

## Manifest and Validation

For every added, removed, moved, or renamed material, update `manifest.json`. See `docs/manifest.md` for the current schema.

After all material files are final, run:

```bash
node scripts/refresh-manifest-metadata.mjs --write
node scripts/update-readme.mjs
node scripts/validate-materials.mjs
node scripts/update-readme.mjs --check
```

Do not hand-write or guess `bytes` or `sha256`.

The optional supplemental audit is:

```bash
python3 skills/henu-public-materials/scripts/check_public_materials.py /path/to/HENU-Final-Review
```

The root Node validator is the authoritative validation contract. The Python script should only add audit checks and must not define a conflicting taxonomy.

After organizing materials, open a pull request and describe course, canonical type, year/scope, source, review notes, and any confirmed optional author/collector attribution.
