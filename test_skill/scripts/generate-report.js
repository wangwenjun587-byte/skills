/**
 * 测试报告生成脚本
 * 用途：将 JSON 测试结果注入 HTML 模板，生成最终报告
 *
 * 使用方式：
 *   node scripts/generate-report.js --input results.json --output report.html
 *
 * results.json 格式：
 * {
 *   "skillName": "被测 Skill 名称",
 *   "testTime": "2026-05-22 14:00",
 *   "evalMode": "full_test",
 *   "dimensions": [
 *     { "name": "输出质量", "score": 5, "mode": "full_test", "evidence": "说明" },
 *     ...
 *   ],
 *   "issues": [
 *     { "level": "P0", "dimension": "维度名", "desc": "问题描述", "evidence": "证据" },
 *     ...
 *   ]
 * }
 */

const fs = require('fs');
const path = require('path');

// 解析命令行参数
function parseArgs() {
  const args = {};
  process.argv.slice(2).forEach(arg => {
    if (arg.startsWith('--')) {
      const [key, ...rest] = arg.slice(2).split('=');
      args[key] = rest.join('=') || process.argv[process.argv.indexOf(arg) + 1];
    }
  });
  return args;
}

// 获取模板目录的绝对路径
function getTemplatePath() {
  // 优先从脚本所在位置向上查找 templates/
  const scriptDir = __dirname;
  const templatePath = path.join(scriptDir, '..', 'templates', 'test-report.html');
  if (fs.existsSync(templatePath)) return templatePath;
  throw new Error(`模板文件未找到: ${templatePath}`);
}

// 生成报告
function generateReport(inputPath, outputPath) {
  // 读取测试结果
  if (!fs.existsSync(inputPath)) {
    console.error(`错误: 输入文件不存在: ${inputPath}`);
    process.exit(1);
  }
  const data = JSON.parse(fs.readFileSync(inputPath, 'utf-8'));

  // 读取模板
  const templatePath = getTemplatePath();
  let html = fs.readFileSync(templatePath, 'utf-8');

  // 替换 DATA 对象
  const dataStr = JSON.stringify(data, null, 2);
  html = html.replace(
    /const DATA = \{[\s\S]*?\};/,
    `const DATA = ${dataStr};`
  );

  // 如果未指定输出路径，默认在输入文件同目录生成
  if (!outputPath) {
    outputPath = inputPath.replace(/\.json$/, '.html');
  }

  // 写入报告
  fs.writeFileSync(outputPath, html, 'utf-8');

  // 输出摘要
  const total = data.dimensions.reduce((s, d) => s + d.score, 0);
  const maxTotal = data.dimensions.length * 5;
  const avg = total / data.dimensions.length;
  let grade;
  if (avg >= 4.7) grade = 'A';
  else if (avg >= 4.0) grade = 'B';
  else if (avg >= 3.0) grade = 'C';
  else if (avg >= 2.0) grade = 'D';
  else grade = 'E';

  console.log(`\n报告已生成: ${outputPath}`);
  console.log(`Skill: ${data.skillName}`);
  console.log(`得分: ${total}/${maxTotal} (${grade})`);
  console.log(`问题: ${data.issues.length} 个 (${data.issues.filter(i => i.level === 'P0').length} P0, ${data.issues.filter(i => i.level === 'P1').length} P1, ${data.issues.filter(i => i.level === 'P2').length} P2)\n`);
}

// 入口
const args = parseArgs();
if (!args.input) {
  console.log('用法: node scripts/generate-report.js --input <results.json> [--output <report.html>]');
  console.log('');
  console.log('参数:');
  console.log('  --input   测试结果 JSON 文件路径（必需）');
  console.log('  --output  输出 HTML 报告路径（可选，默认与输入同名 .html）');
  process.exit(1);
}

generateReport(args.input, args.output);
