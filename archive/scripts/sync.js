#!/usr/bin/env node

/**
 * DramaGen AI - 自动同步脚本
 *
 * 用途：定期从远程仓库拉取最新代码，避免冲突
 * 使用：node scripts/sync.js
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// 颜色输出
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  red: '\x1b[31m',
  blue: '\x1b[34m',
};

function log(message, color = 'reset') {
  const timestamp = new Date().toLocaleTimeString('zh-CN');
  console.log(`${colors[color]}[${timestamp}] ${message}${colors.reset}`);
}

function exec(command, description) {
  try {
    log(`执行: ${description}...`, 'blue');
    const output = execSync(command, {
      encoding: 'utf-8',
      stdio: ['ignore', 'pipe', 'pipe']
    });
    log(`✓ ${description} 完成`, 'green');
    return { success: true, output };
  } catch (error) {
    log(`✗ ${description} 失败`, 'red');
    log(`错误: ${error.message}`, 'red');
    return { success: false, error };
  }
}

async function main() {
  log('🔄 DramaGen AI 自动同步开始', 'bright');

  // 检查是否在 Git 仓库中
  if (!fs.existsSync('.git')) {
    log('✗ 错误: 当前目录不是 Git 仓库', 'red');
    process.exit(1);
  }

  // 获取当前分支
  const branchResult = exec('git rev-parse --abbrev-ref HEAD', '获取当前分支');
  if (!branchResult.success) {
    process.exit(1);
  }
  const currentBranch = branchResult.output.trim();
  log(`当前分支: ${currentBranch}`, 'blue');

  // 检查是否有未提交的更改
  const statusResult = exec('git status --porcelain', '检查工作区状态');
  if (!statusResult.success) {
    process.exit(1);
  }

  if (statusResult.output.trim()) {
    log('⚠️  检测到未提交的更改:', 'yellow');
    log(statusResult.output, 'yellow');

    // 询问是否暂存（在非交互模式下自动暂存）
    if (process.env.CI || process.env.AUTO_SYNC_STASH === 'true') {
      log('自动暂存更改...', 'yellow');
      exec('git stash push -m "auto-sync-stash"', '暂存更改');
    } else {
      log('提示: 使用 git stash 暂存或 git commit 提交更改', 'yellow');
      log('或设置环境变量 AUTO_SYNC_STASH=true 自动暂存', 'yellow');
    }
  }

  // 拉取最新代码
  log('从远程仓库拉取最新代码...', 'bright');
  const pullResult = exec(`git pull origin ${currentBranch}`, '拉取代码');

  if (!pullResult.success) {
    log('❌ 拉取失败，可能存在冲突', 'red');
    log('请手动解决冲突后重试', 'yellow');
    process.exit(1);
  }

  // 检查是否有新的依赖
  if (fs.existsSync('package.json')) {
    const packageJsonBefore = JSON.parse(fs.readFileSync('package.json', 'utf-8'));

    // 再次拉取以确保最新
    exec(`git pull origin ${currentBranch}`, '再次拉取');

    const packageJsonAfter = JSON.parse(fs.readFileSync('package.json', 'utf-8'));

    // 比较依赖
    const depsBefore = JSON.stringify(packageJsonBefore.dependencies);
    const depsAfter = JSON.stringify(packageJsonAfter.dependencies);

    if (depsBefore !== depsAfter) {
      log('📦 检测到新的依赖，建议运行 npm install', 'yellow');
    }
  }

  // 显示协作状态
  if (fs.existsSync('COLLABORATION.md')) {
    log('\n📋 协作状态:', 'bright');
    const collab = fs.readFileSync('COLLABORATION.md', 'utf-8');

    // 提取当前阻塞项
    const blockedSection = collab.match(/## 🚨 当前阻塞项([\s\S]*?)(?=##|$)/);
    if (blockedSection) {
      log(blockedSection[1].trim(), 'yellow');
    }
  }

  log('\n✅ 同步完成!', 'green');
  log(`下次同步: ${new Date(Date.now() + 5 * 60 * 1000).toLocaleTimeString('zh-CN')}`, 'blue');
}

// 处理错误
process.on('unhandledRejection', (error) => {
  log(`未处理的错误: ${error.message}`, 'red');
  process.exit(1);
});

main().catch((error) => {
  log(`同步失败: ${error.message}`, 'red');
  process.exit(1);
});
