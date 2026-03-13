import cv2
import numpy as np

img = cv2.imread("clips/test_compare/test_filter_20s.jpg")
cv2.imwrite("clips/test_compare/crop_20s_blur.jpg", img[437:437+35, 98:98+106])

img_orig = cv2.imread("clips/test_compare/orig_20s.jpg")
cv2.imwrite("clips/test_compare/crop_20s_orig.jpg", img_orig[437:437+35, 98:98+106])

print(img[437:437+35, 98:98+106].mean())
print(img_orig[437:437+35, 98:98+106].mean())
