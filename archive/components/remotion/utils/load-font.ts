import { continueRender, delayRender } from "remotion";

export const TheBoldFont = `TheBoldFont`;

let loaded = false;

/**
 * 加载字体文件
 * 用于字幕渲染的粗体字体
 */
export const loadFont = async (): Promise<void> => {
  if (loaded) {
    return Promise.resolve();
  }

  const waitForFont = delayRender();
  loaded = true;

  try {
    // 使用系统字体作为默认字体
    const font = new FontFace(
      TheBoldFont,
      `local('PingFang SC'), local('Microsoft YaHei'), local('SimHei'), local('Arial Black')`,
    );

    await font.load();
    document.fonts.add(font);
  } catch (error) {
    // 如果系统字体加载失败，使用默认字体
    console.warn("字体加载失败，使用系统默认字体:", error);
  }

  continueRender(waitForFont);
};
