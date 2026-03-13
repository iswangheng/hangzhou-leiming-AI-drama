import cv2
import numpy as np

def check_blur(img_path, y, h):
    img = cv2.imread(img_path)
    if img is None:
        return f"Error loading {img_path}"
    
    # Extract subtitle area
    roi = img[y:y+h, :]
    
    # Let's see if there are regions in the ROI with very low variance (which is typical for boxblur)
    # Convert to grayscale
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    
    # Calculate local variance using a window
    mean, stddev = cv2.meanStdDev(gray)
    
    # Edge detection to see if edges are suppressed in specific rectangular blocks
    edges = cv2.Canny(gray, 50, 150)
    edge_density = np.sum(edges) / (edges.shape[0] * edges.shape[1])
    
    return f"{img_path}: mean={mean[0][0]:.2f}, stddev={stddev[0][0]:.2f}, edge_density={edge_density:.2f}"

y = 421
h = 55
print(check_blur("clips/frames/frame_3_5s.jpg", y, h))
print(check_blur("clips/frames/frame_20_5s.jpg", y, h))
print(check_blur("clips/frames/frame_38_5s.jpg", y, h))
