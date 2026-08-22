import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';

const validatorPath = path.resolve('scripts/validate-materials.mjs');

function sha256(contents) {
  return createHash('sha256').update(contents).digest('hex');
}

function runValidator(assetOverrides = {}) {
  const fixtureRoot = mkdtempSync(path.join(os.tmpdir(), 'henu-material-validator-'));
  const contents = 'fixture material\n';
  const subject = assetOverrides.subject || '测试课程';
  const role = assetOverrides.role || '题库练习';
  const title = assetOverrides.title || `${subject}_题库_样例.txt`;
  const publicPath = assetOverrides.publicPath || `${subject}/${role}/${title}`;
  const fullPath = path.join(fixtureRoot, ...publicPath.split('/'));

  mkdirSync(path.dirname(fullPath), { recursive: true });
  writeFileSync(fullPath, contents);
  writeFileSync(
    path.join(fixtureRoot, 'manifest.json'),
    `${JSON.stringify({
      version: 1,
      subjects: [
        {
          name: subject,
          assets: [
            {
              subject,
              role,
              title,
              publicPath,
              bytes: Buffer.byteLength(contents),
              sha256: sha256(contents),
              sourceType: 'community-note',
              sourceNote: '同学整理的复习资料。',
              reviewStatus: 'basic-reviewed',
              containsPersonalInfo: false,
              licenseStatus: 'learning-reference',
              ...assetOverrides,
            },
          ],
        },
      ],
    }, null, 2)}\n`,
  );

  const result = spawnSync(process.execPath, [validatorPath], {
    cwd: fixtureRoot,
    encoding: 'utf8',
  });
  rmSync(fixtureRoot, { recursive: true, force: true });
  return result;
}

test('accepts canonical courseware role', () => {
  const result = runValidator({
    role: '课件',
    title: '测试课程_课件_第1章.pptx',
  });

  assert.equal(result.status, 0, result.stderr);
});

test('accepts canonical courseware role with a legacy physical folder during migration', () => {
  const result = runValidator({
    role: '课件',
    title: '测试课程_课件_第1章.pptx',
    publicPath: '测试课程/课件PPT/测试课程_课件_第1章.pptx',
  });

  assert.equal(result.status, 0, result.stderr);
});

test('accepts a legacy role temporarily and reports a migration warning', () => {
  const result = runValidator({
    role: '课件PPT',
    title: '测试课程_课件_第1章.pptx',
  });

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stderr, /Legacy material roles remain for migration compatibility/);
});

test('accepts electronic textbook role', () => {
  const result = runValidator({
    role: '电子版教材',
    title: '测试课程_教材_示例.pdf',
  });

  assert.equal(result.status, 0, result.stderr);
});

test('accepts verified author and collector attribution', () => {
  const result = runValidator({
    attribution: {
      authors: ['课程资料原作者'],
      collectors: ['资料收集者'],
    },
  });

  assert.equal(result.status, 0, result.stderr);
});

test('rejects attribution that is not a non-empty string list', () => {
  const result = runValidator({
    attribution: {
      authors: '课程资料原作者',
    },
  });

  assert.equal(result.status, 1);
  assert.match(result.stderr, /attribution\.authors must be a non-empty array of non-empty strings/);
});

test('rejects attribution values that expose contact details', () => {
  const result = runValidator({
    attribution: {
      collectors: ['collector@example.com'],
    },
  });

  assert.equal(result.status, 1);
  assert.match(result.stderr, /attribution must use a public display name or handle, not contact details/);
});

test('rejects manifest metadata that admits contact details', () => {
  const result = runValidator({
    sourceNote: '民间整理资料，含作者水印与联系方式。',
  });

  assert.equal(result.status, 1);
  assert.match(result.stderr, /sourceNote indicates personal or contact information/);
});

test('does not accept the historical exception status on a new path', () => {
  const result = runValidator({
    licenseStatus: 'teacher_shared_exception',
  });

  assert.equal(result.status, 1);
  assert.match(result.stderr, /teacher_shared_exception is restricted to the approved historical files/);
});

test('does not accept replacement content at an approved historical path', () => {
  const result = runValidator({
    subject: '思想道德与法治',
    role: '复习讲义',
    title: '思想道德与法治_复习讲义_2025年冬最新考试重点.pdf',
    publicPath: '思想道德与法治/复习讲义/思想道德与法治_复习讲义_2025年冬最新考试重点.pdf',
    licenseStatus: 'teacher_shared_exception',
  });

  assert.equal(result.status, 1);
  assert.match(result.stderr, /teacher_shared_exception is restricted to the approved historical files/);
});

test('requires year-uncertain material to stay in the canonical review role', () => {
  const result = runValidator({
    sourceType: 'student-recall',
    sourceNote: '同学回忆版，年份待复核。',
    reviewStatus: 'needs_review',
    uncertainty: 'year_uncertain',
  });

  assert.equal(result.status, 1);
  assert.match(result.stderr, /uncertainty 'year_uncertain' requires role '待复核资料'/);
});

test('accepts year-uncertain material in the legacy review folder during migration', () => {
  const result = runValidator({
    role: '待复核资料',
    title: '测试课程_待复核_样例.txt',
    publicPath: '测试课程/待复核课件PPT/测试课程_待复核_样例.txt',
    sourceType: 'student-recall',
    sourceNote: '同学回忆版，年份待复核。',
    reviewStatus: 'needs_review',
    uncertainty: 'year_uncertain',
  });

  assert.equal(result.status, 0, result.stderr);
});
