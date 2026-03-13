import cv2
import os

os.system("ffmpeg -y -i clips/test_hardcoded_mask.mp4 -ss 00:00:20.000 -vframes 1 clips/frames/hc_20_0s.jpg -loglevel error")
os.system("ffmpeg -y -i clips/test_hardcoded_mask.mp4 -ss 00:00:37.000 -vframes 1 clips/frames/hc_37_0s.jpg -loglevel error")

img1 = cv2.imread("clips/frames/hc_20_0s.jpg")
img2 = cv2.imread("clips/frames/hc_37_0s.jpg")

print(img1[437:437+35, 98:98+106].mean())
print(img2[438:438+37, 69:69+105].mean())
