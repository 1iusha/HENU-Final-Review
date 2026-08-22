#!/usr/bin/env node
import { existsSync, mkdirSync, readFileSync, renameSync, statSync, writeFileSync } from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const manifestPath = path.join(root, 'manifest.json');
const args = new Set(process.argv.slice(2));
const writeMode = args.has('--write');
const checkMode = args.has('--check') || !writeMode;

if (writeMode && args.has('--check')) {
  console.error('Use either --check or --write, not both.');
  process.exit(2);
}

const LEGACY_ROLE_ALIASES = new Map([
  ['课件PPT', '课件'],
  ['课件资料', '课件'],
  ['课件资料包', '课件'],
  ['待复核课件PPT', '待复核资料']
]);

function canonicalRole(value) {
  return LEGACY_ROLE_ALIASES.get(value) || value;
}

function safeRepoPath(publicPath) {
  if (!publicPath || typeof publicPath !== 'string') {
    throw new Error(`Invalid publicPath: ${String(publicPath)}`);
  }
  if (publicPath.startsWith('/') || publicPath.startsWith('\\')) {
    throw new Error(`Absolute publicPath is not allowed: ${publicPath}`);
  }

  const normalized = path.posix.normalize(publicPath);
  if (normalized !== publicPath || normalized === '..' || normalized.startsWith('../')) {
    throw new Error(`Unsafe publicPath: ${publicPath}`);
  }

  const fullPath = path.resolve(root, ...publicPath.split('/'));
  const relative = path.relative(root, fullPath);
  if (relative === '..' || relative.startsWith(`..${path.sep}`) || path.isAbsolute(relative)) {
    throw new Error(`publicPath escapes repository root: ${publicPath}`);
  }
  return fullPath;
}

if (!existsSync(manifestPath)) {
  console.error('manifest.json is missing.');
  process.exit(1);
}

const rawManifest = readFileSync(manifestPath, 'utf8');
const eol = rawManifest.includes('\r\n') ? '\r\n' : '\n';
let manifest;
try {
  manifest = JSON.parse(rawManifest);
} catch (error) {
  console.error(`manifest.json is invalid JSON: ${error.message}`);
  process.exit(1);
}

const plans = [];
const plannedTargets = new Map();
const errors = [];
const counts = new Map();

function addError(message) {
  errors.push(message);
}

for (const subject of manifest.subjects || []) {
  for (const asset of subject.assets || []) {
    const sourcePublicPath = asset.publicPath;
    if (typeof sourcePublicPath !== 'string') continue;

    const parts = sourcePublicPath.split('/');
    if (parts.length < 3) {
      addError(`${subject.name || '<unknown subject>'} / ${asset.title || '<untitled>'}: invalid publicPath '${sourcePublicPath}'.`);
      continue;
    }

    const physicalRole = parts[1];
    const canonicalAssetRole = canonicalRole(asset.role);
    const canonicalPhysicalRole = canonicalRole(physicalRole);
    const needsMigration = canonicalAssetRole !== asset.role || canonicalPhysicalRole !== physicalRole;
    if (!needsMigration) continue;

    if (canonicalAssetRole !== canonicalPhysicalRole) {
      addError(`${sourcePublicPath}: manifest role '${asset.role}' and physical folder '${physicalRole}' map to different canonical roles ('${canonicalAssetRole}' vs '${canonicalPhysicalRole}').`);
      continue;
    }

    if (parts[0] !== subject.name || asset.subject !== subject.name) {
      addError(`${sourcePublicPath}: subject/path mismatch prevents safe migration.`);
      continue;
    }

    const targetParts = [...parts];
    targetParts[1] = canonicalPhysicalRole;
    const targetPublicPath = targetParts.join('/');

    let sourcePath;
    let targetPath;
    try {
      sourcePath = safeRepoPath(sourcePublicPath);
      targetPath = safeRepoPath(targetPublicPath);
    } catch (error) {
      addError(error.message);
      continue;
    }

    if (!existsSync(sourcePath)) {
      addError(`${sourcePublicPath}: source file does not exist.`);
      continue;
    }
    if (!statSync(sourcePath).isFile()) {
      addError(`${sourcePublicPath}: source path is not a regular file.`);
      continue;
    }

    if (sourcePublicPath !== targetPublicPath && existsSync(targetPath)) {
      addError(`${sourcePublicPath}: target already exists at '${targetPublicPath}'.`);
      continue;
    }

    const priorSource = plannedTargets.get(targetPublicPath);
    if (priorSource && priorSource !== sourcePublicPath) {
      addError(`Multiple legacy files would collide at '${targetPublicPath}': '${priorSource}' and '${sourcePublicPath}'.`);
      continue;
    }
    plannedTargets.set(targetPublicPath, sourcePublicPath);

    const mappingLabel = `${asset.role}→${canonicalAssetRole}`;
    counts.set(mappingLabel, (counts.get(mappingLabel) || 0) + 1);

    plans.push({
      asset,
      sourcePublicPath,
      targetPublicPath,
      sourcePath,
      targetPath,
      targetRole: canonicalAssetRole
    });
  }
}

if (errors.length > 0) {
  for (const error of errors) console.error(`error: ${error}`);
  console.error(`\nMigration preflight failed with ${errors.length} error(s). No files were changed.`);
  process.exit(1);
}

const summary = [...counts.entries()].map(([label, count]) => `${label}: ${count}`).join(', ');

if (checkMode) {
  if (plans.length > 0) {
    console.error(`Legacy material-type migration is still required for ${plans.length} asset(s)${summary ? ` (${summary})` : ''}.`);
    process.exit(1);
  }
  console.log('Material type migration is complete; no legacy role/path entries remain.');
  process.exit(0);
}

if (plans.length === 0) {
  console.log('No legacy material type entries require migration.');
  process.exit(0);
}

for (const plan of plans) {
  if (plan.sourcePublicPath !== plan.targetPublicPath) {
    mkdirSync(path.dirname(plan.targetPath), { recursive: true });
    renameSync(plan.sourcePath, plan.targetPath);
  }
  plan.asset.role = plan.targetRole;
  plan.asset.publicPath = plan.targetPublicPath;
}

manifest.generatedAt = new Date().toISOString();
let nextManifest = `${JSON.stringify(manifest, null, 2)}\n`;
if (eol === '\r\n') nextManifest = nextManifest.replace(/\n/g, '\r\n');
writeFileSync(manifestPath, nextManifest, 'utf8');

console.log(`Migrated ${plans.length} asset(s) to canonical material types${summary ? ` (${summary})` : ''}.`);
