import cv2
import numpy as np

def diff_score(p1, p2, x, y, w, h):
    i1 = cv2.imread(p1)[y:y+h, x:x+w]
    i2 = cv2.imread(p2)[y:y+h, x:x+w]
    return np.mean(cv2.absdiff(i1, i2))

d1 = diff_score("clips/test_compare/orig_20s.jpg", "clips/frames/hc_20_0s.jpg", 98, 437, 106, 35)
d2 = diff_score("clips/test_compare/orig_37s.jpg", "clips/frames/hc_37_0s.jpg", 69, 438, 105, 37)
print(f"Diff 20s: {d1}")
print(f"Diff 37s: {d2}")
