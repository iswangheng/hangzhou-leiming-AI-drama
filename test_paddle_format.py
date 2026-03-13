from paddleocr import PaddleOCR
import cv2

ocr = PaddleOCR(lang='ch')
img_path = '260306-待剪辑-漫剧网盘素材1/烈日重生/烈日重生-1.mp4'
cap = cv2.VideoCapture(img_path)
cap.set(cv2.CAP_PROP_POS_FRAMES, 590) # roughly 19.6s
ret, frame = cap.read()
if ret:
    h = frame.shape[0]
    y_start = int(h * 0.58)
    y_end = int(h * 0.66)
    area = frame[y_start:y_end, :]
    res = ocr.ocr(area)
    print(res)
