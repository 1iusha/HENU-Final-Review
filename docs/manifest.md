# Manifest 规范

`manifest.json` 是公开资料仓库的机器可读索引。README 面向读者，manifest 面向网站、脚本、搜索、校验和后续导入流程。

本文档描述当前约定。不要把历史数据中出现过的自由文本值当作新的标准枚举。

## 基本结构

```json
{
  "version": 1,
  "generatedAt": "2026-08-22T00:00:00.000Z",
  "subjects": [
    {
      "name": "离散数学",
      "note": "包含真题、复习讲义等公开资料。",
      "assets": []
    }
  ]
}
```

## Canonical material types

新资料统一使用以下 8 个 `role`：

- `复习讲义`
- `往年真题`
- `课件`
- `题库练习`
- `答案解析`
- `笔记总结`
- `电子版教材`
- `待复核资料`

资料类型表达“内容是什么”，不表达文件格式。`.ppt`、`.pptx`、`.pdf`、`.docx` 或合理保留的 `.zip` 只要本质上是课程课件，都属于 `课件`。

### Legacy aliases

仓库历史数据中仍可能存在以下旧类型：

| 旧类型 | Canonical role |
| --- | --- |
| `课件PPT` | `课件` |
| `课件资料` | `课件` |
| `课件资料包` | `课件` |
| `待复核课件PPT` | `待复核资料` |

这些名称只作为迁移兼容项，不用于新资料。旧文件可以继续保留原路径，直到单独执行目录迁移；校验器应按上述映射判断其逻辑类型。

## 必填字段

每个 `asset` 必须包含：

| 字段 | 说明 |
| --- | --- |
| `subject` | 课程名，必须与所在 subject 的 `name` 一致。 |
| `role` | 资料逻辑类型；新条目使用上面的 canonical role。 |
| `title` | 展示标题，通常等于文件名。 |
| `publicPath` | 仓库内相对路径。新资料使用 `课程名/Canonical类型/文件名`；历史路径可暂时使用 legacy alias。 |
| `bytes` | 文件字节数，由脚本从最终文件计算。 |
| `sha256` | 文件 SHA-256，用于完整性校验，并可用于识别完全相同的重复文件。 |

不要手写或猜测 `bytes` / `sha256`。资料文件最终写入后运行：

```bash
node scripts/refresh-manifest-metadata.mjs --write
```

## 来源与复核字段

这些字段用于可追溯性、审核和后续搜索。当前仓库存在部分历史自由文本，因此除布尔字段和校验器明确约束的值外，不应假装存在尚未落地的严格枚举。

| 字段 | 示例 | 说明 |
| --- | --- | --- |
| `year` | `2023-2024` | 年份、学年、届别或适用时间。 |
| `college` | `软件学院` | 适用学院。 |
| `major` | `网络工程` | 适用专业，可省略。 |
| `sourceType` | `teacher-courseware` | 来源类别。 |
| `sourceNote` | `同学提供的课程公开课件。` | 人类可读来源说明，不得包含联系方式。 |
| `reviewStatus` | `basic-reviewed` | 当前复核状态。 |
| `uncertainty` | `year_uncertain` | 仍存在的不确定性原因，可省略。 |
| `containsPersonalInfo` | `false` | 是否含个人信息；公开仓库不得为 `true`。 |
| `licenseStatus` | `learning-reference` | 公开/授权边界说明。 |
| `attribution` | 见下文 | 可选公开署名。 |

`node scripts/validate-materials.mjs --strict-metadata` 会要求校验器定义的来源字段全部存在；普通 CI 暂未把所有历史资料强制提升到严格 metadata 模式。

## sourceType 推荐值

为了减少新的 schema drift，新条目优先使用以下值：

- `teacher-courseware`：老师公开课件。
- `teacher-handout`：老师公开讲义或课程资料。
- `course-group`：课程群中可公开传播的资料。
- `student-recall`：同学回忆版真题或试卷。
- `community-note`：同学整理的讲义、题解、笔记或练习资料。
- `personal-note`：贡献者本人原创学习笔记。
- `doc-converted`：从旧格式转换得到的文字版/兼容版。
- `unknown-reviewing`：来源尚未确认，只能用于 `待复核资料`。
- `other`：以上无法准确表达且已有明确说明的来源。

历史记录中已有中文或其他旧值时，不要为了格式统一而无依据改写来源事实；可在确认来源后逐步迁移。

## reviewStatus 推荐值

- `verified`：课程、来源、公开边界等关键信息已充分确认。
- `basic-reviewed`：完成基本检查，可公开使用，但未做强真实性背书。
- `needs_review`：仍需人工复核。
- `deprecated`：已不推荐使用，等待替换、迁移或移除。

不要把“不确定原因”塞进 `reviewStatus`。例如年份不确定应写：

```json
{
  "reviewStatus": "needs_review",
  "uncertainty": "year_uncertain"
}
```

常见 `uncertainty`：

- `source_uncertain`
- `year_uncertain`
- `course_uncertain`
- `public_boundary_uncertain`
- `format_lossy`
- `content_uncertain`

其中来源、年份、课程归属或公开边界不确定时，资料必须处于 `待复核资料` 逻辑类型。`format_lossy` 等不确定性可以用于已确认课程归属但格式有损的资料。

## licenseStatus

常见值包括：

- `learning-reference`
- `public-review-only`
- `authorized-redistribution`：资料维护者已经核实该文件具有公开再分发授权。
- `teacher_shared_exception`

`teacher_shared_exception` 仅用于仓库中已经按 `publicPath` 与 SHA256 白名单锁定的历史教师公开分享材料，不是新资料可选的通用状态。

如果授权边界无法确认，使用 `待复核资料`，并通过 `sourceNote` / `uncertainty` 写清楚问题，而不是伪造一个“已授权”状态。

## attribution 署名

`attribution` 是可选对象，可包含：

- `authors`：资料正文的原始作者，仅在来源明确或本人确认时填写。
- `collectors`：发现、汇集、数字化或向仓库提供既有资料的人。

两个字段均为非空字符串数组，至少填写一个。上传流程应主动询问资料提供者一次是否愿意公开署名致谢；不愿意或没有回应时直接省略。

只使用经确认的公开姓名、昵称或账号。不写邮箱、手机号、QQ、微信、二维码、学号等信息，也不要从 Git 提交者、账号邮箱或文件元数据自动推断署名。

```json
"attribution": {
  "authors": ["资料原作者公开昵称"],
  "collectors": ["资料提供者公开昵称"]
}
```

## 待复核资料

`待复核资料` 是统一的隔离类型，不再按 PPT、PDF、DOCX 等格式拆分类别。适用于：

- 来源不确定。
- 年份不确定且年份会影响资料判断。
- 课程归属不确定。
- 是否适合公开存在疑问。
- 文件究竟是真题、课件、题库还是其他类型尚无法判断。

复核完成后应移动到正式 canonical type，并同步更新 `role`、`publicPath` 和文件元数据。

## 示例

```json
{
  "subject": "离散数学",
  "role": "往年真题",
  "title": "离散数学_真题_软件学院23级.pdf",
  "publicPath": "离散数学/往年真题/离散数学_真题_软件学院23级.pdf",
  "year": "2023",
  "college": "软件学院",
  "major": "网络工程",
  "sourceType": "student-recall",
  "sourceNote": "软件学院23级同学回忆版，内容已做基本检查。",
  "reviewStatus": "basic-reviewed",
  "containsPersonalInfo": false,
  "licenseStatus": "learning-reference",
  "attribution": {
    "collectors": ["资料提供者公开昵称"]
  },
  "bytes": 240532,
  "sha256": "20122cc28de5c25d5df70f6b37b8e73db87748acc34bd6bfbc1ed6958a72b40a"
}
```

## 校验

默认校验 manifest 结构、路径安全、资料类型、文件存在性、字节数、SHA-256、署名字段、敏感元数据和待复核约束：

```bash
node scripts/validate-materials.mjs
```

检查文件元数据是否需要刷新：

```bash
node scripts/refresh-manifest-metadata.mjs --check
```

严格来源字段校验：

```bash
node scripts/validate-materials.mjs --strict-metadata
```
