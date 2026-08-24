#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { existsSync, lstatSync, readdirSync, readFileSync, realpathSync, statSync } from 'node:fs';
import path from 'node:path';

const root = process.cwd();
// Resolved once so the repository boundary check below compares real path to
// real path (on macOS the temp dir used by tests is itself a symlink).
const realRoot = realpathSync(root);
const manifestPath = path.join(root, 'manifest.json');
const strictMetadata = process.argv.includes('--strict-metadata');

const SYSTEM_DIRS = new Set([
  '.git',
  '.github',
  'docs',
  'scripts',
  'skills',
  'tests',
  '.public-materials-export'
]);

const CANONICAL_TYPE_DIRS = new Set([
  '复习讲义',
  '往年真题',
  '课件',
  '题库练习',
  '答案解析',
  '笔记总结',
  '电子版教材',
  '待复核资料'
]);

const LEGACY_TYPE_ALIASES = new Map([
  ['课件PPT', '课件'],
  ['课件资料', '课件'],
  ['课件资料包', '课件'],
  ['待复核课件PPT', '待复核资料']
]);

const ALLOWED_TYPE_DIRS = new Set([
  ...CANONICAL_TYPE_DIRS,
  ...LEGACY_TYPE_ALIASES.keys()
]);

const ALLOWED_EXTENSIONS = new Set([
  '.pdf',
  '.ppt',
  '.pptx',
  '.docx',
  '.md',
  '.txt',
  '.zip'
]);

const FORBIDDEN_BASENAME_PATTERNS = [
  /副本/i,
  /final_final/i,
  /未命名/i,
  /新建文件/i,
  /^~\$/,
  /\.tmp$/i,
  /\.crdownload$/i,
  /\.download$/i
];

const OPTIONAL_METADATA_FIELDS = [
  'year',
  'college',
  'sourceType',
  'sourceNote',
  'reviewStatus',
  'containsPersonalInfo',
  'licenseStatus'
];

const REVIEW_ONLY_UNCERTAINTIES = new Set([
  'source_uncertain',
  'year_uncertain',
  'course_uncertain',
  'public_boundary_uncertain'
]);

const CONTACT_DETAIL_PATTERNS = [
  /[A-Z0-9._%+-]+\s*@\s*[A-Z0-9.-]+\.[A-Z]{2,}/i,
  /(?<!\d)1[3-9]\d{9}(?!\d)/,
  /QQ\s*[:：]?\s*[1-9]\d{4,11}/i,
  /联系方式|联系邮箱|联系电话|手机号|二维码/
];

const APPROVED_CONTACT_EXCEPTIONS = new Map([
  ['思想道德与法治/复习讲义/思想道德与法治_复习讲义_2025年冬最新考试重点.pdf', 'bfda62a15cfefb53c1413a244a4ff9f95e11a9fc959032f4ebff83adc1b8530c'],
  ['思想道德与法治/复习讲义/思想道德与法治_复习讲义_2026年夏最新考试重点.pdf', '62605c70458a8da91a90e38f88fb9a628ba4283233262e3554b9085ab0acee73'],
  ['思想道德与法治/题库练习/思想道德与法治_题库练习_2025年冬最新考试习题库.pdf', '863593807fb03560c9fd351faa33176fbe38e5063897d1efe0d2df657bb65aeb'],
  ['思想道德与法治/题库练习/思想道德与法治_题库练习_2026年夏最新考试习题库.pdf', '2202c6481c4e20484d2dee269d40203b3ce297903d81ccfa3b9e30d17ad1df2c'],
  ['习近平新时代中国特色社会主义思想概论/复习讲义/习近平新时代中国特色社会主义思想概论_复习讲义_2025年冬最新教材重点.pdf', '9a9b0b52a35fbee614b33e0fb231ef5df982e9cb460d7ece0d09faaf4c266bd7'],
  ['习近平新时代中国特色社会主义思想概论/题库练习/习近平新时代中国特色社会主义思想概论_题库练习_2025年冬最新教材习题库.pdf', 'b53770144dc0db848f00036d593689ef12339002cc1ab24df856213fe03944ca']
]);

const errors = [];
const warnings = [];
const metadataGaps = new Map();
const legacyRoleCounts = new Map();

function fail(message) {
  errors.push(message);
}

function warn(message) {
  warnings.push(message);
}

function canonicalType(value) {
  return LEGACY_TYPE_ALIASES.get(value) || value;
}

function recordLegacyRole(role) {
  legacyRoleCounts.set(role, (legacyRoleCounts.get(role) || 0) + 1);
}

function recordMetadataGap(field) {
  metadataGaps.set(field, (metadataGaps.get(field) || 0) + 1);
}

function sha256(filePath) {
  return createHash('sha256').update(readFileSync(filePath)).digest('hex');
}

function isSafeRelativePath(value) {
  if (!value || typeof value !== 'string') return false;
  if (value.startsWith('/') || value.startsWith('\\')) return false;
  const normalized = path.posix.normalize(value);
  return normalized === value && !normalized.startsWith('../') && normalized !== '..';
}

function escapesRepository(fullPath) {
  let realPath;
  try {
    realPath = realpathSync(fullPath);
  } catch {
    // A path we cannot resolve (broken link, vanished target) is not provably inside.
    return true;
  }

  const relative = path.relative(realRoot, realPath);
  return relative === '' || relative.startsWith('..') || path.isAbsolute(relative);
}

function containsContactDetails(value) {
  return typeof value === 'string' && CONTACT_DETAIL_PATTERNS.some((pattern) => pattern.test(value));
}

function validateAttribution(asset, label) {
  if (!('attribution' in asset)) return;

  const attribution = asset.attribution;
  if (!attribution || typeof attribution !== 'object' || Array.isArray(attribution)) {
    fail(`${label}: attribution must be an object.`);
    return;
  }

  const supportedFields = new Set(['authors', 'collectors']);
  for (const field of Object.keys(attribution)) {
    if (!supportedFields.has(field)) {
      fail(`${label}: unsupported attribution field '${field}'.`);
    }
  }

  const presentFields = [...supportedFields].filter((field) => field in attribution);
  if (presentFields.length === 0) {
    fail(`${label}: attribution must include authors or collectors.`);
    return;
  }

  for (const field of presentFields) {
    const values = attribution[field];
    const validList = Array.isArray(values)
      && values.length > 0
      && values.every((value) => typeof value === 'string' && value.trim() === value && value.length > 0);
    if (!validList) {
      fail(`${label}: attribution.${field} must be a non-empty array of non-empty strings.`);
      continue;
    }

    if (new Set(values).size !== values.length) {
      fail(`${label}: attribution.${field} must not contain duplicates.`);
    }

    if (values.some(containsContactDetails)) {
      fail(`${label}: attribution must use a public display name or handle, not contact details.`);
    }
  }
}

function readManifest() {
  if (!existsSync(manifestPath)) {
    fail('manifest.json is missing.');
    return null;
  }

  try {
    return JSON.parse(readFileSync(manifestPath, 'utf8'));
  } catch (error) {
    fail(`manifest.json is not valid JSON: ${error.message}`);
    return null;
  }
}

function validateTopLevelFolders(manifest) {
  const subjectNames = new Set((manifest.subjects || []).map((subject) => subject.name));
  for (const entry of readdirSync(root, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    if (SYSTEM_DIRS.has(entry.name)) continue;
    if (!subjectNames.has(entry.name)) {
      warn(`Top-level folder '${entry.name}' is not listed as a manifest subject.`);
    }
  }
}

function validateCourseFolders() {
  for (const entry of readdirSync(root, { withFileTypes: true })) {
    if (!entry.isDirectory() || SYSTEM_DIRS.has(entry.name)) continue;
    const courseDir = path.join(root, entry.name);
    for (const child of readdirSync(courseDir, { withFileTypes: true })) {
      if (!child.isDirectory()) continue;
      if (!ALLOWED_TYPE_DIRS.has(child.name)) {
        fail(`Unsupported material type folder: ${entry.name}/${child.name}`);
      }
    }
  }
}

function validateAsset(subject, asset, seenPaths, seenHashes) {
  const label = `${subject.name || '<unknown subject>'} / ${asset.title || '<untitled>'}`;

  for (const field of ['subject', 'role', 'title', 'publicPath', 'bytes', 'sha256']) {
    if (!(field in asset)) fail(`${label}: missing required field '${field}'.`);
  }

  if (asset.subject !== subject.name) {
    fail(`${label}: asset.subject '${asset.subject}' does not match subject.name '${subject.name}'.`);
  }

  if (!ALLOWED_TYPE_DIRS.has(asset.role)) {
    fail(`${label}: unsupported role '${asset.role}'.`);
  } else if (LEGACY_TYPE_ALIASES.has(asset.role)) {
    recordLegacyRole(asset.role);
  }

  const logicalRole = canonicalType(asset.role);

  if (!isSafeRelativePath(asset.publicPath)) {
    fail(`${label}: unsafe publicPath '${asset.publicPath}'.`);
    return;
  }

  const parts = asset.publicPath.split('/');
  if (parts.length < 3) {
    fail(`${label}: publicPath must be '课程名/资料类型/文件名'.`);
  } else {
    const [courseName, roleDir] = parts;
    if (courseName !== subject.name) {
      fail(`${label}: publicPath course '${courseName}' does not match subject '${subject.name}'.`);
    }
    if (!ALLOWED_TYPE_DIRS.has(roleDir)) {
      fail(`${label}: publicPath uses unsupported material type folder '${roleDir}'.`);
    } else if (canonicalType(roleDir) !== logicalRole) {
      fail(`${label}: publicPath role folder '${roleDir}' does not match logical role '${logicalRole}'.`);
    }
  }

  const basename = path.posix.basename(asset.publicPath);
  const ext = path.posix.extname(basename).toLowerCase();

  if (!ALLOWED_EXTENSIONS.has(ext)) {
    fail(`${label}: unsupported file extension '${ext}'.`);
  }

  if (/[,:?*<>|"\\]/.test(basename)) {
    fail(`${label}: filename contains forbidden characters: '${basename}'.`);
  }

  for (const pattern of FORBIDDEN_BASENAME_PATTERNS) {
    if (pattern.test(basename)) {
      fail(`${label}: filename looks temporary or unnormalized: '${basename}'.`);
      break;
    }
  }

  if (!basename.startsWith(`${subject.name}_`)) {
    warn(`${label}: filename does not start with '${subject.name}_'.`);
  }

  if (seenPaths.has(asset.publicPath)) {
    fail(`${label}: duplicate publicPath '${asset.publicPath}'.`);
  }
  seenPaths.add(asset.publicPath);

  const fullPath = path.join(root, ...asset.publicPath.split('/'));
  if (!existsSync(fullPath)) {
    fail(`${label}: file does not exist at '${asset.publicPath}'.`);
    return;
  }

  // isSafeRelativePath only inspects the manifest string. Every filesystem call
  // below follows symlinks, so without these two checks a submitted symlink
  // lets the manifest publish, hash, and vouch for a file outside the repo.
  if (lstatSync(fullPath).isSymbolicLink()) {
    fail(`${label}: publicPath is a symbolic link; material files must be regular files committed to the repository.`);
    return;
  }

  if (escapesRepository(fullPath)) {
    fail(`${label}: publicPath resolves outside the repository.`);
    return;
  }

  const stats = statSync(fullPath);
  if (!stats.isFile()) {
    fail(`${label}: publicPath is not a regular file.`);
    return;
  }

  if (asset.bytes !== stats.size) {
    fail(`${label}: bytes mismatch, manifest=${asset.bytes}, actual=${stats.size}.`);
  }

  const actualHash = sha256(fullPath);
  if (asset.sha256 !== actualHash) {
    fail(`${label}: sha256 mismatch, manifest=${asset.sha256}, actual=${actualHash}.`);
  }

  const duplicatePath = seenHashes.get(actualHash);
  if (duplicatePath && duplicatePath !== asset.publicPath) {
    warn(`${label}: exact duplicate content also exists at '${duplicatePath}'.`);
  } else if (!duplicatePath) {
    seenHashes.set(actualHash, asset.publicPath);
  }

  for (const field of OPTIONAL_METADATA_FIELDS) {
    if (!(field in asset)) recordMetadataGap(field);
  }

  if (strictMetadata) {
    const missingMetadata = OPTIONAL_METADATA_FIELDS.filter((field) => !(field in asset));
    if (missingMetadata.length > 0) {
      fail(`${label}: missing provenance metadata: ${missingMetadata.join(', ')}.`);
    }
  }

  validateAttribution(asset, label);

  const hasApprovedContactException = asset.licenseStatus === 'teacher_shared_exception'
    && APPROVED_CONTACT_EXCEPTIONS.get(asset.publicPath) === asset.sha256;
  if (asset.licenseStatus === 'teacher_shared_exception' && !hasApprovedContactException) {
    fail(`${label}: teacher_shared_exception is restricted to the approved historical files.`);
  }
  if (
    logicalRole === '电子版教材'
    && (
      asset.reviewStatus !== 'verified'
      || asset.licenseStatus !== 'authorized-redistribution'
      || typeof asset.sourceNote !== 'string'
      || asset.sourceNote.trim() === ''
      || asset.containsPersonalInfo !== false
    )
  ) {
    fail(`${label}: electronic textbooks require verified redistribution authorization, a source note, and containsPersonalInfo=false.`);
  }
  if (containsContactDetails(asset.sourceNote) && !hasApprovedContactException) {
    fail(`${label}: sourceNote indicates personal or contact information; remove or redact the file before publishing.`);
  }

  if (REVIEW_ONLY_UNCERTAINTIES.has(asset.uncertainty) && logicalRole !== '待复核资料') {
    fail(`${label}: uncertainty '${asset.uncertainty}' requires role '待复核资料'.`);
  }

  if (asset.containsPersonalInfo === true) {
    fail(`${label}: containsPersonalInfo=true is not allowed in the public repository.`);
  }
}

function main() {
  const manifest = readManifest();
  if (!manifest) return;

  if (manifest.version !== 1) {
    fail(`Unsupported manifest version '${manifest.version}'. Expected version 1.`);
  }

  if (!Array.isArray(manifest.subjects)) {
    fail('manifest.subjects must be an array.');
    return;
  }

  validateTopLevelFolders(manifest);
  validateCourseFolders();

  const seenSubjects = new Set();
  const seenPaths = new Set();
  const seenHashes = new Map();

  for (const subject of manifest.subjects) {
    if (!subject.name) {
      fail('A subject is missing name.');
      continue;
    }
    if (seenSubjects.has(subject.name)) {
      fail(`Duplicate subject '${subject.name}'.`);
    }
    seenSubjects.add(subject.name);

    if (!Array.isArray(subject.assets)) {
      fail(`Subject '${subject.name}' assets must be an array.`);
      continue;
    }

    for (const asset of subject.assets) {
      validateAsset(subject, asset, seenPaths, seenHashes);
    }
  }

  if (legacyRoleCounts.size > 0) {
    const summary = [...legacyRoleCounts.entries()]
      .map(([role, count]) => `${role}→${canonicalType(role)}: ${count}`)
      .join(', ');
    warn(`Legacy material roles remain for migration compatibility. New entries should use canonical roles. Counts: ${summary}.`);
  }

  if (metadataGaps.size > 0 && !strictMetadata) {
    const summary = [...metadataGaps.entries()]
      .map(([field, count]) => `${field}: ${count}`)
      .join(', ');
    warn(`Optional provenance metadata is incomplete. Run with --strict-metadata after backfilling fields. Missing counts: ${summary}.`);
  }

  for (const warning of warnings) {
    console.warn(`warning: ${warning}`);
  }

  if (errors.length > 0) {
    for (const error of errors) {
      console.error(`error: ${error}`);
    }
    console.error(`\nValidation failed with ${errors.length} error(s) and ${warnings.length} warning(s).`);
    process.exit(1);
  }

  console.log(`Material validation passed with ${warnings.length} warning(s).`);
}

main();
