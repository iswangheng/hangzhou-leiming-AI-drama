/**
 * 集数解析工具
 *
 * 功能：从视频文件名中解析集数
 * 支持多种格式：ep01, 第1集, 01, 001, E01 等
 */

/**
 * 从文件名解析集数（更宽松的规则）
 *
 * @param filename - 文件名（如：ep01.mp4, 第1集.mp4, 01 骨血灯.mp4）
 * @returns 集数（1-100），如果无法识别则返回 null
 *
 * @example
 * parseEpisodeNumber("ep01.mp4")           // 1
 * parseEpisodeNumber("第2集.mp4")          // 2
 * parseEpisodeNumber("01 骨血灯.mp4")      // 1
 * parseEpisodeNumber("骨血灯_03_1080p.mp4") // 3
 * parseEpisodeNumber("trailer.mp4")        // null
 */
export function parseEpisodeNumber(filename: string): number | null {
  if (!filename) return null;

  // 规则1：明确的"集"或"ep"关键字
  const explicitPatterns = [
    /ep(\d+)\b/i,           // ep01, ep1, EP01, EP1（边界匹配，避免episode）
    /第(\d+)集/,            // 第1集, 第01集
    /(\d+)集/,              // 1集, 01集
    /[eE](\d+)\b/,          // e01, e1, E01, E1（边界匹配）
  ];

  for (const pattern of explicitPatterns) {
    const match = filename.match(pattern);
    if (match) {
      const num = parseInt(match[1], 10);
      if (num >= 1 && num <= 200) {  // 合理性检查
        return num;
      }
    }
  }

  // 规则2：文件名开头的2-3位数字（后面跟分隔符）
  // 例: "01 骨血灯.mp4", "02.mp4", "001 - 第一集.mp4"
  const leadingNumberPattern = /^(\d{2,3})[\s\-_.]/;
  const match = filename.match(leadingNumberPattern);
  if (match) {
    const num = parseInt(match[1], 10);
    if (num >= 1 && num <= 200) {
      return num;
    }
  }

  // 规则3：文件名中独立的2-3位数字（被分隔符包围）
  // 例: "骨血灯_03_1080p.mp4", "drama-04-final.mp4", "show_05_1080p.mp4"
  const standaloneNumberPattern = /[-_\s](\d{2,3})[-_\s\.]/;
  const match2 = filename.match(standaloneNumberPattern);
  if (match2) {
    const num = parseInt(match2[1], 10);
    if (num >= 1 && num <= 200) {
      return num;
    }
  }

  // 规则4：纯数字文件名（不含扩展名）
  // 例: "1.mp4", "01.mp4", "001.mp4"
  const pureNumberPattern = /^(\d{1,3})\.[^.]+$/;
  const match3 = filename.match(pureNumberPattern);
  if (match3) {
    const num = parseInt(match3[1], 10);
    if (num >= 1 && num <= 200) {
      return num;
    }
  }

  return null;
}

/**
 * 生成显示标题
 *
 * @param episodeNumber - 集数
 * @param filename - 原始文件名（可选）
 * @returns 显示标题（如："第1集"、"第1集：骨血灯"）
 *
 * @example
 * generateDisplayTitle(1, "ep01.mp4")              // "第1集"
 * generateDisplayTitle(1, "骨血灯-ep01.mp4")        // "第1集：骨血灯"
 * generateDisplayTitle(2, "第02集：午夜凶铃.mp4")    // "第2集：午夜凶铃"
 */
export function generateDisplayTitle(episodeNumber: number, filename?: string): string {
  const baseTitle = `第${episodeNumber}集`;

  if (!filename) {
    return baseTitle;
  }

  // 尝试从文件名提取副标题
  const nameWithoutExt = filename.replace(/\.[^.]+$/, '');  // 去除扩展名
  const nameWithoutEp = nameWithoutExt
    .replace(/ep?0*\d+/i, '')           // 去除 ep01, ep1 等
    .replace(/第?\d+集/, '')           // 去除 第1集, 1集 等
    .replace(/^[\s\-_]+|[\s\-_]+$/g, '') // 去除开头和结尾的分隔符
    .trim();

  if (nameWithoutEp && nameWithoutEp.length > 0 && nameWithoutEp.length < 30) {
    // 如果副标题长度合理，添加到标题中
    return `${baseTitle}：${nameWithoutEp}`;
  }

  return baseTitle;
}

/**
 * 批量解析文件名并排序
 *
 * @param filenames - 文件名数组
 * @returns 排序后的文件名数组（按集数排序）
 *
 * @example
 * const files = ["ep03.mp4", "ep01.mp4", "ep02.mp4"];
 * const sorted = sortFilesByEpisode(files);  // ["ep01.mp4", "ep02.mp4", "ep03.mp4"]
 */
export function sortFilesByEpisode(filenames: string[]): Array<{
  filename: string;
  episodeNumber: number | null;
}> {
  return filenames
    .map(filename => ({
      filename,
      episodeNumber: parseEpisodeNumber(filename),
    }))
    .sort((a, b) => {
      // 有集数的排在前面
      if (a.episodeNumber === null && b.episodeNumber !== null) return 1;
      if (a.episodeNumber !== null && b.episodeNumber === null) return -1;
      if (a.episodeNumber === null && b.episodeNumber === null) return 0;

      // 按集数升序排序
      return (a.episodeNumber || 0) - (b.episodeNumber || 0);
    });
}

/**
 * 验证集数是否连续
 *
 * @param episodeNumbers - 集数数组
 * @returns 是否连续（1, 2, 3, 4...）
 *
 * @example
 * validateConsecutive([1, 2, 3, 4])  // true
 * validateConsecutive([1, 3, 4, 5])  // false（缺少第2集）
 */
export function validateConsecutive(episodeNumbers: number[]): boolean {
  if (episodeNumbers.length === 0) return false;

  const sorted = [...episodeNumbers].sort((a, b) => a - b);
  const start = sorted[0];

  for (let i = 0; i < sorted.length; i++) {
    if (sorted[i] !== start + i) {
      return false;
    }
  }

  return true;
}

/**
 * 检测缺失的集数
 *
 * @param episodeNumbers - 集数数组
 * @returns 缺失的集数数组
 *
 * @example
 * detectMissingEpisodes([1, 2, 4, 5])  // [3]
 * detectMissingEpisodes([1, 2, 3])      // []
 */
export function detectMissingEpisodes(episodeNumbers: number[]): number[] {
  if (episodeNumbers.length === 0) return [];

  const sorted = [...episodeNumbers].sort((a, b) => a - b);
  const start = sorted[0];
  const end = sorted[sorted.length - 1];
  const missing: number[] = [];

  for (let i = start; i <= end; i++) {
    if (!sorted.includes(i)) {
      missing.push(i);
    }
  }

  return missing;
}
