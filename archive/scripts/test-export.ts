/**
 * 视频导出功能测试脚本
 *
 * 用途：测试视频导出模块的核心功能
 *
 * 运行方式：
 * npm run test:export
 */

import { exportCombination, getExportStatus, cleanupTempFiles } from "../lib/export/video-exporter";

/**
 * 测试导出功能
 */
async function testExport() {
  console.log("\n========================================");
  console.log("  视频导出功能测试");
  console.log("========================================\n");

  try {
    // 1. 创建测试导出任务
    console.log("1️⃣  创建导出任务...");
    console.log("   项目 ID: 1");
    console.log("   组合 ID: 10");
    console.log("   输出格式: mp4\n");

    const result = await exportCombination({
      projectId: 1,
      combinationId: 10,
      outputFormat: "mp4",
    });

    // 2. 显示导出结果
    console.log("\n2️⃣  导出结果:");
    console.log("   成功:", result.success);
    console.log("   输出路径:", result.outputPath || "无");
    console.log("   文件大小:", result.fileSize ? `${(result.fileSize / 1024 / 1024).toFixed(2)} MB` : "未知");
    console.log("   视频时长:", result.durationMs ? `${(result.durationMs / 1000 / 60).toFixed(2)} 分钟` : "未知");
    console.log("   导出 ID:", result.exportId || "无");

    if (!result.success) {
      console.log("\n❌ 导出失败:", result.errorMessage);
      return;
    }

    // 3. 查询导出状态
    if (result.exportId) {
      console.log("\n3️⃣  查询导出状态...");
      const status = await getExportStatus(result.exportId);

      if (status) {
        console.log("   状态:", status.success ? "成功" : "失败");
        console.log("   文件路径:", status.outputPath || "无");
      }
    }

    console.log("\n✅ 测试完成！");

  } catch (error) {
    console.error("\n❌ 测试失败:", error);
  }
}

/**
 * 测试临时文件清理
 */
async function testCleanup() {
  console.log("\n========================================");
  console.log("  临时文件清理测试");
  console.log("========================================\n");

  const testDir = "/tmp/test_export_cleanup";

  try {
    console.log("1️⃣  清理测试目录:", testDir);
    await cleanupTempFiles(testDir, false);

    console.log("\n✅ 清理测试完成！");
  } catch (error) {
    console.error("\n❌ 清理测试失败:", error);
  }
}

/**
 * 主测试入口
 */
async function main() {
  const args = process.argv.slice(2);
  const testType = args[0] || "export";

  switch (testType) {
    case "export":
      await testExport();
      break;
    case "cleanup":
      await testCleanup();
      break;
    case "all":
      await testExport();
      await testCleanup();
      break;
    default:
      console.log("\n❌ 未知的测试类型:", testType);
      console.log("\n可用测试类型:");
      console.log("  - export:  测试导出功能");
      console.log("  - cleanup: 测试清理功能");
      console.log("  - all:      运行所有测试");
  }
}

// 运行测试
main();
