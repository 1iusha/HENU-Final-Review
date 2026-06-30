# HENU Public Materials Upload Format

## Allowed Top-Level Course Folders

Use the official Chinese course name:

- `高等数学A（二）`
- `离散数学`
- `大学物理`
- `面向对象程序设计Java`
- `Web编程基础`

Add new courses only when the uploaded files clearly belong to that course.

## Material Type Folders

Allowed folders under each course:

- `复习讲义`
- `往年真题`
- `课件PPT`
- `课件资料`
- `课件资料包`
- `题库练习`
- `答案解析`
- `笔记总结`
- `待复核课件PPT`
- `待复核资料`

Do not create `完整复习包` or any paid-package directory in the public repository.

## Filename Pattern

Use:

```text
课程名_资料类型_关键信息[_年份或版本].扩展名
```

Examples:

```text
离散数学_真题_软件学院23级.pdf
大学物理_课件_2023大学物理高斯定理.pdf
面向对象程序设计Java_课件_第1章Java概述.pptx
Web编程基础_压缩包_Web课件.zip
```

## Character Rules

- Use the Chinese course name; do not use pinyin abbreviations.
- Use `、` for multiple section numbers, such as `D7-1、2、3`.
- Use suffixes for versions, such as `_02`, `_精简版`, `_删减版`.
- Avoid ASCII commas, slashes, colons, question marks, asterisks, and temporary words like `副本`, `未命名`, `final_final`.

## Public/Private Boundary

Allowed:

- True exams and recall exams.
- Public courseware and lecture notes.
- Course exercise banks and answer notes.
- Community-maintained review notes.

Not allowed:

- Paid final-review packages or membership bundles.
- AI-generated PPTs presented as real courseware.
- Personal data, account information, scores, names lists, credentials.
- Unclear-source files unless placed under a `待复核...` folder with a note.

## Repository Docs

When changing public contents:

- Update `README.md` course listings.
- Update `manifest.json` with `subject`, `role`, `title`, `publicPath`, `bytes`, and `sha256`.
- Keep `docs/naming.md` and `docs/commit-format.md` consistent with this format.
