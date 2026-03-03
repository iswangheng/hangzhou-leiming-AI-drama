/**
 * 生成杭州雷鸣 Excel 导入示例文件
 *
 * 用途：生成符合格式要求的示例 Excel 文件
 * 输出：public/examples/hangzhou-leiming-template.xlsx
 */

import * as XLSX from "xlsx";
import * as fs from "fs";
import * as path from "path";

// 示例数据（20条）
const exampleData = [
  { 集数: "第1集", 时间点: "00:35", 标记类型: "高光点", 描述: "高能冲突开场" },
  { 集数: "第1集", 时间点: "01:20", 标记类型: "钩子点", 描述: "悬念设置" },
  { 集数: "第1集", 时间点: "02:15", 标记类型: "高光点", 描述: "身份揭露" },
  { 集数: "第1集", 时间点: "03:40", 标记类型: "钩子点", 描述: "情感爆发" },
  { 集数: "第1集", 时间点: "05:10", 标记类型: "高光点", 描述: "剧情反转" },
  { 集数: "第2集", 时间点: "00:45", 标记类型: "高光点", 描述: "开场冲突" },
  { 集数: "第2集", 时间点: "01:30", 标记类型: "钩子点", 描述: "悬念结尾" },
  { 集数: "第2集", 时间点: "02:50", 标记类型: "高光点", 描述: "真相揭露" },
  { 集数: "第2集", 时间点: "04:15", 标记类型: "钩子点", 描述: "情绪高潮" },
  { 集数: "第3集", 时间点: "00:30", 标记类型: "高光点", 描述: "高能对决" },
  { 集数: "第3集", 时间点: "01:15", 标记类型: "钩子点", 描述: "悬念设置" },
  { 集数: "第3集", 时间点: "02:40", 标记类型: "高光点", 描述: "身份揭秘" },
  { 集数: "第3集", 时间点: "03:55", 标记类型: "钩子点", 描述: "情感爆发" },
  { 集数: "第4集", 时间点: "00:40", 标记类型: "高光点", 描述: "剧情高潮" },
  { 集数: "第4集", 时间点: "01:25", 标记类型: "钩子点", 描述: "悬念结尾" },
  { 集数: "第4集", 时间点: "02:50", 标记类型: "高光点", 描述: "反转揭露" },
  { 集数: "第5集", 时间点: "00:35", 标记类型: "高光点", 描述: "开场高能" },
  { 集数: "第5集", 时间点: "01:20", 标记类型: "钩子点", 描述: "情感高潮" },
  { 集数: "第5集", 时间点: "02:45", 标记类型: "高光点", 描述: "真相大白" },
  { 集数: "第5集", 时间点: "04:00", 标记类型: "钩子点", 描述: "悬念结尾" },
];

/**
 * 生成 Excel 文件
 */
function generateExcelFile() {
  console.log("📊 开始生成示例 Excel 文件...\n");

  // 1. 创建工作表
  const worksheet = XLSX.utils.json_to_sheet(exampleData);

  // 2. 设置列宽
  worksheet['!cols'] = [
    { wch: 12 }, // 集数
    { wch: 10 }, // 时间点
    { wch: 12 }, // 标记类型
    { wch: 20 }, // 描述
  ];

  // 3. 创建工作簿
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "标记数据");

  // 4. 生成文件
  const outputDir = path.join(process.cwd(), "public", "examples");
  const outputFile = path.join(outputDir, "hangzhou-leiming-template.xlsx");

  // 确保目录存在
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
    console.log(`✅ 创建目录: ${outputDir}\n`);
  }

  // 5. 写入文件
  XLSX.writeFile(workbook, outputFile);

  // 6. 输出统计信息
  console.log("✅ 示例文件生成成功！\n");
  console.log("📄 文件信息:");
  console.log(`   路径: ${outputFile}`);
  console.log(`   大小: ${fs.statSync(outputFile).size} bytes`);
  console.log(`   行数: ${exampleData.length + 1} (包含表头)\n`);

  console.log("📋 数据预览:");
  console.log("   集数    | 时间点 | 标记类型 | 描述");
  console.log("   " + "-".repeat(50));
  exampleData.slice(0, 5).forEach((row, index) => {
    console.log(
      `   ${row.集数.padEnd(7)} | ${row.时间点.padEnd(6)} | ${row.标记类型.padEnd(8)} | ${row.描述}`
    );
  });
  if (exampleData.length > 5) {
    console.log(`   ... 还有 ${exampleData.length - 5} 条数据`);
  }
  console.log("\n✨ 完成！用户可以下载此文件作为参考。\n");
}

/**
 * 生成 CSV 格式示例文件
 */
function generateCSVFile() {
  console.log("📊 开始生成示例 CSV 文件...\n");

  const outputDir = path.join(process.cwd(), "public", "examples");
  const outputFile = path.join(outputDir, "hangzhou-leiming-template.csv");

  // 确保目录存在
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  // 生成 CSV 内容
  const headers = "集数,时间点,标记类型,描述";
  const rows = exampleData.map(
    (row) => `${row.集数},${row.时间点},${row.标记类型},${row.描述}`
  );
  const csvContent = [headers, ...rows].join("\n");

  // 写入文件
  fs.writeFileSync(outputFile, csvContent, "utf-8");

  console.log("✅ CSV 示例文件生成成功！");
  console.log(`   路径: ${outputFile}\n`);
}

// 主函数
function main() {
  console.log("\n" + "=".repeat(60));
  console.log("  杭州雷鸣 - Excel 导入示例文件生成器");
  console.log("=".repeat(60) + "\n");

  try {
    generateExcelFile();
    generateCSVFile();
  } catch (error) {
    console.error("❌ 生成失败:", error);
    process.exit(1);
  }
}

// 运行
main();
