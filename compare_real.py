import cv2
import numpy as np

def diff_score(p1, p2, x, y, w, h):
    i1 = cv2.imread(p1)
    i2 = cv2.imread(p2)
    roi1 = i1[y:y+h, x:x+w]
    roi2 = i2[y:y+h, x:x+w]
    return np.mean(cv2.absdiff(roi1, roi2))

d1 = diff_score("clips/test_compare/test_orig_20s.jpg", "clips/test_compare/test_mask_20s.jpg", 98, 437, 106, 35)
print(f"Diff real 20s: {d1}")
