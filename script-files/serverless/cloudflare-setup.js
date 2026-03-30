#!/usr/bin/env node

/**
 * @title Cloudflare Workers Environment Setup Script
 * @description Automated setup tool for Cloudflare Workers resources (KV, R2, D1, Secrets)
 * @version 1.0.0
 * @author ropean
 *
 * This script automates the setup of Cloudflare Workers resources including:
 * - KV Namespaces (Key-Value storage)
 * - R2 Buckets (Object storage)
 * - D1 Databases (SQL database)
 * - JWT Secrets (Authentication)
 *
 * @example
 * node cloudflare-setup.js
 * node cloudflare-setup.js --env production
 *
 * @requires wrangler
 *
 * Usage:
 *   node scripts/cloudflare-setup.js                        # local (default) - creates .dev.vars
 *   node scripts/cloudflare-setup.js --env local            # same as above
 *   node scripts/cloudflare-setup.js --env dev              # dev environment
 *   node scripts/cloudflare-setup.js --env preview          # preview environment
 *   node scripts/cloudflare-setup.js --env staging          # staging environment
 *   node scripts/cloudflare-setup.js --env production       # production environment
 *
 * Environment Behavior:
 * ┌─────────────┬────────────────────────────────────────────────────────────┐
 * │ Environment │ Behavior                                                   │
 * ├─────────────┼────────────────────────────────────────────────────────────┤
 * │ local       │ • Generates JWT_SECRET to .dev.vars (for wrangler dev)     │
 * │             │ • No Cloudflare resources created                          │
 * │             │ • Uses local simulated storage                             │
 * ├─────────────┼────────────────────────────────────────────────────────────┤
 * │ dev         │ • Creates resources with -dev suffix                       │
 * │             │ • Sets JWT_SECRET via wrangler secret put                  │
 * │             │ • Generates wrangler.toml configuration                    │
 * ├─────────────┼────────────────────────────────────────────────────────────┤
 * │ preview     │ • Creates resources with -preview suffix                   │
 * │             │ • Temporary environment for testing/PRs                    │
 * │             │ • Sets JWT_SECRET via wrangler secret put                  │
 * ├─────────────┼────────────────────────────────────────────────────────────┤
 * │ staging     │ • Creates resources with -staging suffix                   │
 * │             │ • Pre-production testing environment                       │
 * │             │ • Sets JWT_SECRET via wrangler secret put                  │
 * ├─────────────┼────────────────────────────────────────────────────────────┤
 * │ production  │ • Creates resources without suffix                         │
 * │             │ • Production environment                                   │
 * │             │ • Sets JWT_SECRET via wrangler secret put                  │
 * └─────────────┴────────────────────────────────────────────────────────────┘
 *
 * Resource Naming Convention:
 *   production:  api-kit-users
 *   dev:         api-kit-users-dev
 *   preview:     api-kit-users-preview
 *   staging:     api-kit-users-staging
 *
 * Features:
 *   • Smart caching: Lists resources once, checks from memory
 *   • Idempotent: Safe to run multiple times (skips existing resources)
 *   • Filtered output: Only shows resources defined in RESOURCES config
 *   • Auto-generates wrangler.toml configuration
 *   • Optional save to timestamped backup file
 *
 * Prerequisites:
 *   • Node.js installed
 *   • Wrangler CLI installed (pnpm install -g wrangler)
 *   • Logged in to Cloudflare (wrangler login)
 *
 * Examples:
 *   # Local development (no cloud resources)
 *   node scripts/cloudflare-setup.js
 *
 *   # Setup dev environment
 *   node scripts/cloudflare-setup.js --env dev
 *
 *   # Setup production
 *   node scripts/cloudflare-setup.js --env production
 */

import { execSync } from 'child_process';
import { createInterface } from 'readline';
import { existsSync, writeFileSync } from 'fs';

// ============================================================================
// Configuration
// ============================================================================

/**
 * Resource definitions for the API Kit project
 * Only resources defined here will be created and shown in output
 */
const RESOURCES = {
  kv: [
    { binding: 'USERS_KV', baseName: 'api-kit-users' },
    { binding: 'CONFIG_KV', baseName: 'api-kit-config' },
    { binding: 'RATE_LIMIT_KV', baseName: 'api-kit-ratelimit' },
    { binding: 'STATS_KV', baseName: 'api-kit-stats' },
  ],
  r2: [
    { binding: 'FILE_BUCKET', baseName: 'api-kit-files' },
    { binding: 'LOG_ARCHIVE', baseName: 'api-kit-logs' },
  ],
  d1: [
    { binding: 'DB', baseName: 'api-kit-logs' },
  ],
  analytics: [
    { binding: 'ANALYTICS' },
  ],
};

const VALID_ENVIRONMENTS = ['local', 'dev', 'preview', 'staging', 'production'];

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Execute shell command and return output
 * @param {string} command - Command to execute
 * @returns {string} Command output
 */
function exec(command) {
  try {
    return execSync(command, { encoding: 'utf-8', stdio: ['pipe', 'pipe', 'pipe'] });
  } catch (error) {
    throw new Error(`Command failed: ${command}\n${error.message}`);
  }
}

/**
 * Execute shell command silently (ignore errors)
 * @param {string} command - Command to execute
 * @returns {string|null} Command output or null if failed
 */
function execSilent(command) {
  try {
    return execSync(command, { encoding: 'utf-8', stdio: ['pipe', 'pipe', 'pipe'] });
  } catch (error) {
    return null;
  }
}

/**
 * Get resource name with environment suffix
 * @param {string} baseName - Base resource name
 * @param {string} env - Environment name
 * @returns {string} Resource name with suffix
 */
function getResourceName(baseName, env) {
  if (env === 'production') {
    return baseName; // production has no suffix
  }
  return `${baseName}-${env}`;
}

/**
 * Parse command line arguments
 * @returns {string} Environment name
 */
function parseArgs() {
  const args = process.argv.slice(2);

  // Default to local if no args
  if (args.length === 0) {
    return 'local';
  }

  // Parse --env flag
  const envIndex = args.indexOf('--env');
  if (envIndex !== -1 && args[envIndex + 1]) {
    const env = args[envIndex + 1];

    if (!VALID_ENVIRONMENTS.includes(env)) {
      console.error(`❌ Invalid environment: "${env}"\n`);
      console.error('Valid environments:');
      console.error('  • local      - Local development (wrangler dev)');
      console.error('  • dev        - Development environment');
      console.error('  • preview    - Preview/temporary environment');
      console.error('  • staging    - Pre-production staging');
      console.error('  • production - Production environment\n');
      console.error('Usage:');
      console.error('  node scripts/cloudflare-setup.js                    # defaults to local');
      console.error('  node scripts/cloudflare-setup.js --env local        # local environment');
      console.error('  node scripts/cloudflare-setup.js --env dev          # dev environment');
      console.error('  node scripts/cloudflare-setup.js --env preview      # preview environment');
      console.error('  node scripts/cloudflare-setup.js --env staging      # staging environment');
      console.error('  node scripts/cloudflare-setup.js --env production   # production environment');
      process.exit(1);
    }

    return env;
  }

  console.error('❌ Invalid arguments. Use --env flag to specify environment.\n');
  console.error('Usage:');
  console.error('  node scripts/cloudflare-setup.js --env <environment>\n');
  console.error('Example:');
  console.error('  node scripts/cloudflare-setup.js --env dev');
  process.exit(1);
}

/**
 * Prompt user for yes/no input
 * @param {string} question - Question to ask
 * @returns {Promise<boolean>} True if user answered yes
 */
function prompt(question) {
  const rl = createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      rl.close();
      resolve(['y', 'yes'].includes(answer.toLowerCase().trim()));
    });
  });
}

// ============================================================================
// Resource Manager (with caching)
// ============================================================================

class ResourceManager {
  constructor(env) {
    this.env = env;
    this.kvCache = null;
    this.r2Cache = null;
    this.d1Cache = null;
  }

  /**
   * Get KV namespaces list (cached)
   * @param {boolean} forceRefresh - Force refresh cache
   * @returns {Array} List of KV namespaces
   */
  getKVList(forceRefresh = false) {
    if (!this.kvCache || forceRefresh) {
      console.log('📋 Fetching KV namespaces...');
      const output = exec('wrangler kv namespace list');
      try {
        this.kvCache = JSON.parse(output);
      } catch (error) {
        // If parsing fails, assume no namespaces exist
        console.log('  ⚠️  Warning: Could not parse KV list output');
        this.kvCache = [];
      }
    }
    return this.kvCache;
  }

  /**
   * Get R2 buckets list (cached)
   * @param {boolean} forceRefresh - Force refresh cache
   * @returns {Array} List of R2 buckets
   */
  getR2List(forceRefresh = false) {
    if (!this.r2Cache || forceRefresh) {
      console.log('📋 Fetching R2 buckets...');
      try {
        const output = exec('wrangler r2 bucket list');

        // Parse text output format:
        // name:           api-kit-files
        // creation_date:  2025-10-21T17:18:30.289Z
        const buckets = [];
        const lines = output.split('\n');

        for (let i = 0; i < lines.length; i++) {
          const line = lines[i].trim();
          if (line.startsWith('name:')) {
            const name = line.replace('name:', '').trim();
            if (name) {
              buckets.push({ name });
            }
          }
        }

        this.r2Cache = buckets;
      } catch (error) {
        console.log('  ⚠️  Warning: Could not fetch R2 buckets');
        this.r2Cache = [];
      }
    }
    return this.r2Cache;
  }

  /**
   * Get D1 databases list (cached)
   * @param {boolean} forceRefresh - Force refresh cache
   * @returns {Array} List of D1 databases
   */
  getD1List(forceRefresh = false) {
    if (!this.d1Cache || forceRefresh) {
      console.log('📋 Fetching D1 databases...');
      try {
        const output = exec('wrangler d1 list');

        // Parse table output format:
        // │ uuid                                 │ name                 │ created_at               │ ...
        // │ 22bc420e-0672-4f5d-9e6b-8fcdaa34592d │ api-kit-logs         │ 2025-10-22T04:02:57.242Z │ ...
        const databases = [];
        const lines = output.split('\n');

        for (const line of lines) {
          // Skip header, separator, and empty lines
          if (!line.includes('│') || line.includes('uuid') || line.includes('─')) {
            continue;
          }

          // Split by │ and extract uuid and name
          const parts = line
            .split('│')
            .map((p) => p.trim())
            .filter((p) => p);
          if (parts.length >= 2) {
            const uuid = parts[0];
            const name = parts[1];

            // Validate UUID format (contains hyphens)
            if (uuid.includes('-') && name && !name.includes('name')) {
              databases.push({
                database_id: uuid,
                name: name,
              });
            }
          }
        }

        this.d1Cache = databases;
      } catch (error) {
        console.log('  ⚠️  Warning: Could not fetch D1 databases');
        this.d1Cache = [];
      }
    }
    return this.d1Cache;
  }

  /**
   * Check if KV namespace exists
   * @param {string} name - KV namespace name
   * @returns {object|null} KV namespace object or null
   */
  findKV(name) {
    const list = this.getKVList();
    return list.find((kv) => kv.title === name) || null;
  }

  /**
   * Check if R2 bucket exists
   * @param {string} name - R2 bucket name
   * @returns {object|null} R2 bucket object or null
   */
  findR2(name) {
    const list = this.getR2List();
    return list.find((bucket) => bucket.name === name) || null;
  }

  /**
   * Check if D1 database exists
   * @param {string} name - D1 database name
   * @returns {object|null} D1 database object or null
   */
  findD1(name) {
    const list = this.getD1List();
    return list.find((db) => db.name === name) || null;
  }

  /**
   * Create KV namespace
   * @param {string} name - KV namespace name
   * @returns {object} Created KV namespace
   */
  createKV(name) {
    console.log(`  🔨 Creating KV namespace: ${name}...`);
    const output = exec(`wrangler kv namespace create "${name}"`);
    this.kvCache = null; // Clear cache

    // Parse ID from output
    const match = output.match(/id = "([a-f0-9]+)"/);
    if (!match) {
      throw new Error('Failed to parse KV namespace ID from output');
    }

    return { title: name, id: match[1] };
  }

  /**
   * Create R2 bucket
   * @param {string} name - R2 bucket name
   * @returns {object} Created R2 bucket
   */
  createR2(name) {
    console.log(`  🔨 Creating R2 bucket: ${name}...`);
    exec(`wrangler r2 bucket create "${name}"`);
    this.r2Cache = null; // Clear cache

    // Fetch to get details
    const list = this.getR2List(true);
    return list.find((bucket) => bucket.name === name);
  }

  /**
   * Create D1 database
   * @param {string} name - D1 database name
   * @returns {object} Created D1 database
   */
  createD1(name) {
    console.log(`  🔨 Creating D1 database: ${name}...`);
    const output = exec(`wrangler d1 create "${name}"`);
    this.d1Cache = null; // Clear cache

    // Parse database_id from output
    const match = output.match(/database_id = "([a-f0-9-]+)"/);
    if (!match) {
      throw new Error('Failed to parse D1 database ID from output');
    }

    return { name: name, database_id: match[1] };
  }

  /**
   * Initialize D1 database schema
   * @param {string} name - D1 database name
   */
  initD1Schema(name) {
    const schemaPath = 'database/schema.sql';

    if (!existsSync(schemaPath)) {
      console.log(`  ⚠️  Schema file not found: ${schemaPath}`);
      console.log(`  ⚠️  Skipping schema initialization`);
      return;
    }

    console.log(`  🔧 Initializing database schema...`);

    // Build command with environment flag if needed
    let command = `wrangler d1 execute "${name}" --file="${schemaPath}"`;
    if (this.env !== 'production') {
      command += ` --env ${this.env}`;
    }

    const result = execSilent(command);
    if (result !== null) {
      console.log(`  ✅ Schema initialized successfully`);
    } else {
      console.log(`  ⚠️  Schema initialization may have failed (might be normal if tables exist)`);
    }
  }
}

// ============================================================================
// Cloud Environment Setup
// ============================================================================

/**
 * Setup cloud environment (dev/preview/staging/production)
 * @param {string} env - Environment name
 */
async function setupCloudEnvironment(env) {
  console.log('=======================================');
  console.log(`API Kit - Setup Script (${env.toUpperCase()})`);
  console.log('=======================================\n');

  // Check prerequisites
  console.log('🔍 Checking prerequisites...');

  // Check if wrangler is installed
  if (!execSilent('wrangler --version')) {
    console.error('❌ Wrangler CLI is not installed!');
    console.error('   Install it with: pnpm install -g wrangler\n');
    process.exit(1);
  }
  console.log('  ✅ Wrangler CLI is installed');

  // Check if logged in
  if (!execSilent('wrangler whoami')) {
    console.error('❌ Not logged in to Cloudflare!');
    console.error('   Run: wrangler login\n');
    process.exit(1);
  }
  console.log('  ✅ Logged in to Cloudflare\n');

  const manager = new ResourceManager(env);
  const createdResources = {
    kv: [],
    r2: [],
    d1: [],
  };

  // ============================================================
  // Setup KV Namespaces
  // ============================================================
  console.log('📦 Setting up KV Namespaces...\n');

  for (const resource of RESOURCES.kv) {
    const name = getResourceName(resource.baseName, env);
    console.log(`Setting up ${resource.binding} (${name})...`);

    const existing = manager.findKV(name);
    if (existing) {
      console.log(`  ✅ Already exists (ID: ${existing.id})`);
      createdResources.kv.push({
        binding: resource.binding,
        name: name,
        id: existing.id,
      });
    } else {
      const created = manager.createKV(name);
      console.log(`  ✅ Created successfully (ID: ${created.id})`);
      createdResources.kv.push({
        binding: resource.binding,
        name: created.title,
        id: created.id,
      });
    }
    console.log('');
  }

  // ============================================================
  // Setup R2 Buckets
  // ============================================================
  console.log('📦 Setting up R2 Buckets...\n');

  for (const resource of RESOURCES.r2) {
    const name = getResourceName(resource.baseName, env);
    console.log(`Setting up ${resource.binding} (${name})...`);

    const existing = manager.findR2(name);
    if (existing) {
      console.log(`  ✅ Already exists`);
      createdResources.r2.push({
        binding: resource.binding,
        bucket_name: existing.name,
      });
    } else {
      const created = manager.createR2(name);
      console.log(`  ✅ Created successfully`);
      createdResources.r2.push({
        binding: resource.binding,
        bucket_name: created.name,
      });
    }
    console.log('');
  }

  // ============================================================
  // Setup D1 Databases
  // ============================================================
  console.log('📦 Setting up D1 Databases...\n');

  for (const resource of RESOURCES.d1) {
    const name = getResourceName(resource.baseName, env);
    console.log(`Setting up ${resource.binding} (${name})...`);

    const existing = manager.findD1(name);
    if (existing) {
      console.log(`  ✅ Already exists (ID: ${existing.database_id})`);
      createdResources.d1.push({
        binding: resource.binding,
        database_name: existing.name,
        database_id: existing.database_id,
      });
    } else {
      const created = manager.createD1(name);
      console.log(`  ✅ Created successfully (ID: ${created.database_id})`);
      createdResources.d1.push({
        binding: resource.binding,
        database_name: created.name,
        database_id: created.database_id,
      });

      // Initialize schema for newly created database
      manager.initD1Schema(name);
    }
    console.log('');
  }

  // ============================================================
  // Setup JWT Secret
  // ============================================================
  // Generate wrangler.toml configuration
  // ============================================================
  console.log('📋 Generated Configuration:');
  console.log('=======================================\n');

  const config = generateWranglerConfig(env, createdResources);
  console.log(config);
  console.log('=======================================\n');

  // Ask if user wants to save to file
  const shouldSave = await prompt('💾 Save configuration to file? (y/n): ');
  if (shouldSave) {
    const timestamp = Date.now();
    const filename = `wrangler.${env}.${timestamp}.toml`;
    writeFileSync(filename, config);
    console.log(`✅ Configuration saved to: ${filename}\n`);
  }

  // ============================================================
  // Summary
  // ============================================================
  console.log('=======================================');
  console.log('✅ Setup Complete!');
  console.log('=======================================\n');

  console.log('📊 Summary:');
  console.log(`  ✅ ${createdResources.kv.length} KV Namespaces`);
  console.log(`  ✅ ${createdResources.r2.length} R2 Buckets`);
  console.log(`  ✅ ${createdResources.d1.length} D1 Databases`);
}

/**
 * Generate wrangler.toml configuration
 * @param {string} env - Environment name
 * @param {object} resources - Created resources
 * @returns {string} wrangler.toml configuration
 */
function generateWranglerConfig(env, resources) {
  const prefix = `env.${env}.`;
  const lines = [];
  lines.push(`[env.${env}]`);
  lines.push('');

  // KV Namespaces
  for (const kv of resources.kv) {
    lines.push(`[[${prefix}kv_namespaces]]`);
    lines.push(`binding = "${kv.binding}"`);
    lines.push(`id = "${kv.id}"`);
    lines.push('');
  }

  // R2 Buckets
  for (const r2 of resources.r2) {
    lines.push(`[[${prefix}r2_buckets]]`);
    lines.push(`binding = "${r2.binding}"`);
    lines.push(`bucket_name = "${r2.bucket_name}"`);
    lines.push('');
  }

  // D1 Databases
  for (const d1 of resources.d1) {
    lines.push(`[[${prefix}d1_databases]]`);
    lines.push(`binding = "${d1.binding}"`);
    lines.push(`database_name = "${d1.database_name}"`);
    lines.push(`database_id = "${d1.database_id}"`);
    lines.push('');
  }

  // Analytics Engine Datasets (binding only, no ID needed)
  for (const analytics of RESOURCES.analytics) {
    lines.push(`[[${prefix}analytics_engine_datasets]]`);
    lines.push(`binding = "${analytics.binding}${env === 'production' ? '' : `-${env}`}"`);
    lines.push('');
  }

  return lines.join('\n');
}

// ============================================================================
// Main Entry Point
// ============================================================================

async function main() {
  const env = parseArgs();

  if (env === 'local') {
    console.log('⚙️  Local environment — no cloud resources needed.');    
    console.log('⚠️  `wrangler dev` Automatically Creates Local D1 SQLite Databases.');
    return;
  }

  await setupCloudEnvironment(env);
}

// Run the script
main().catch((error) => {
  console.error('\n❌ Setup failed!');
  console.error(error.message);
  process.exit(1);
});
