import cv2
import numpy as np

def analyze_diff(img_path, original_path, x, y, w, h):
    img = cv2.imread(img_path)
    orig = cv2.imread(original_path)
    
    # Extract the specific masked region
    roi_mod = img[y:y+h, x:x+w]
    roi_orig = orig[y:y+h, x:x+w]
    
    # Calculate difference
    diff = cv2.absdiff(roi_mod, roi_orig)
    mean_diff = np.mean(diff)
    
    return mean_diff

print("Analyzing differences between masked and original...")
import os
os.system("ffmpeg -y -i 260306-待剪辑-漫剧网盘素材1/烈日重生/烈日重生-1.mp4 -ss 00:00:20.500 -vframes 1 clips/frames/orig_20_5s.jpg -loglevel error")
os.system("ffmpeg -y -i 260306-待剪辑-漫剧网盘素材1/烈日重生/烈日重生-1.mp4 -ss 00:00:38.500 -vframes 1 clips/frames/orig_38_5s.jpg -loglevel error")

diff_20 = analyze_diff("clips/frames/frame_20_5s.jpg", "clips/frames/orig_20_5s.jpg", 107, 439, 106, 32)
diff_38 = analyze_diff("clips/frames/frame_38_5s.jpg", "clips/frames/orig_38_5s.jpg", 68, 438, 105, 34)

print(f"Diff at 20.5s (高温末世): {diff_20:.2f} (Should be > 0 if blurred)")
print(f"Diff at 38.5s (高温末世): {diff_38:.2f} (Should be > 0 if blurred)")
