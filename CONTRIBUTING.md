# 贡献指南

感谢你愿意一起维护这份公开复习资料。这个仓库优先收录来源清楚、可复核、对复习直接有帮助的文件。

## 可以贡献什么

- 往年真题、回忆版真题、样卷、练习题。
- 老师公开课件、课程讲义、实验资料。
- 自己整理的复习讲义、知识点索引、错题整理。
- 允许公开再分发的电子版教材。
- 对已有资料的勘误、重命名、分类调整。

## Canonical 资料类型

新资料只使用以下 8 个类型：

- `复习讲义`
- `往年真题`
- `课件`
- `题库练习`
- `答案解析`
- `笔记总结`
- `电子版教材`
- `待复核资料`

`课件PPT`、`课件资料`、`课件资料包`、`待复核课件PPT` 是历史目录，仅为迁移兼容保留。新贡献不要再创建这些目录。文件格式由扩展名表达，不需要为 PPT、PDF、DOCX、ZIP 单独创建资料 type。

## 不建议提交什么

- 来源不清、明显错科、无法确认课程归属的资料直接进入正式类型目录。
- 用 AI 生成的 PPT 或伪装成真实课件的内容。
- 带有个人隐私、账号信息、学生名单、成绩信息的文件。
- 付费复习包、会员资料包、盗版商业教材或其他不应公开分发的内容。
- 与课程复习无关的大文件、重复文件或临时文件。

## 公开边界

提交前请阅读 [PUBLICATION_POLICY.md](PUBLICATION_POLICY.md)。来源、年份、课程归属、资料类型或公开边界存在真实疑问时，统一先放入 `待复核资料`，并在 PR 描述中说明具体风险点。

## 署名与致谢

资料提供者可以选择是否公开署名致谢。提交资料时应主动询问一次，但署名完全自愿，不影响资料是否被收录。

- 原创资料作者：`attribution.authors`
- 发现、收集、数字化或提供既有资料的人：`attribution.collectors`

只填写本人确认的公开姓名、昵称或 GitHub 账号。不要填写邮箱、手机号、QQ、微信、学号等联系方式，也不要从 Git 提交者、账号邮箱或文件元数据自动推断署名。

## 提交流程

1. Fork 仓库或在新分支工作。
2. 按 [docs/naming.md](docs/naming.md) 使用 canonical 类型放置和命名资料。
3. 更新 `manifest.json`。字段与兼容规则以 [docs/manifest.md](docs/manifest.md) 为准。
4. 在所有资料文件最终写入后刷新 manifest 文件元数据：

```bash
node scripts/refresh-manifest-metadata.mjs --write
```

不要手写 `bytes` 或 `sha256`；任何资料文件内容改动后，都要重新运行这一步。

5. 重新生成 README 科目目录并运行校验：

```bash
node scripts/update-readme.mjs
node scripts/validate-materials.mjs
node scripts/update-readme.mjs --check
```

6. 需要做额外仓库体检时，可运行：

```bash
python3 skills/henu-public-materials/scripts/check_public_materials.py .
```

该脚本只做补充巡检，根目录 Node 校验链是权威校验标准。

7. 按 [docs/commit-format.md](docs/commit-format.md) 写 commit message 和 PR 标题。
8. 在 PR 描述里写清楚资料来源、课程、canonical 类型、年份/适用范围、是否需要复核，以及任何经确认的可选署名。

## 提交前检查

- 文件放在正确课程目录和 canonical 资料类型目录下。
- 没有为文件格式单独创建新的资料 type。
- 文件名符合 [docs/naming.md](docs/naming.md)。
- Commit message 符合 [docs/commit-format.md](docs/commit-format.md)。
- PR 描述写清楚资料来源、课程、年份和是否需要人工复核。
- `manifest.json` 与实际文件一致。
- 作者或收集者署名已经本人确认，且角色没有混淆；未知或未授权时保持省略。
- 不手写或猜测 `bytes` / `sha256`。
- `README.md` 的科目目录已由脚本重新生成。
- `node scripts/validate-materials.mjs` 可以通过。
- `node scripts/update-readme.mjs --check` 可以通过。
- 没有个人隐私、账号信息、学生名单、成绩信息。
- 没有付费资料、会员资料、盗版教材或内部资料。
- 没有重复提交已有资料。

## 资料质量原则

- 真实优先：真实课件和真题比重新包装的摘要更有价值。
- 可追溯优先：文件名、PR 描述和 manifest 要能看出资料来源与适用范围。
- 少而准优先：不要为了凑数量加入低质量、重复或错科资料。
- 类型稳定优先：资料类型表达内容语义，不表达文件格式。
- 可下架优先：发现不适合公开的资料，应及时提交下架 Issue 或移除 PR。
