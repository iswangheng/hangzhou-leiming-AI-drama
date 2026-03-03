// 测试镜头检测输出
import { execSync } from 'child_process';

const videoPath = 'data/uploads/1771933765095-6eadtc.mp4';
const threshold = 0.3;

const command = `ffmpeg -i "${videoPath}" -filter_complex "[0:v]select='gt(scene,${threshold})',showinfo" -f null - 2>&1 | head -100`;

console.log('🎬 运行 FFmpeg 命令...\n');

try {
  const output = execSync(command, {
    encoding: 'utf-8',
    stdio: ['ignore', 'pipe', 'pipe']
  });

  console.log('📤 FFmpeg 输出（前 2000 字符）：');
  console.log(output.substring(0, 2000));

  console.log('\n\n🔍 正则匹配测试：');
  const lines = output.split('\n');
  let matchCount = 0;
  const matches: number[] = [];

  for (const line of lines) {
    const match = line.match(/pts_time:(\d+\.?\d*)/);
    if (match) {
      matchCount++;
      matches.push(parseFloat(match[1]));
      if (matchCount <= 10) {
        console.log(`  匹配 #${matchCount}: pts_time=${match[1]}`);
      }
    }
  }

  console.log(`\n✅ 总共匹配到 ${matchCount} 个时间戳`);
  if (matches.length > 0) {
    console.log(`📊 前 10 个时间戳: ${matches.slice(0, 10).join(', ')} 秒`);
  }

} catch (error: any) {
  console.error('❌ 错误:', error.message);
  process.exit(1);
}
