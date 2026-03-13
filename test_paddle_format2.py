from paddleocr import PaddleOCR
import cv2

ocr = PaddleOCR(lang='ch')
img_path = '260306-待剪辑-漫剧网盘素材1/烈日重生/烈日重生-1.mp4'
cap = cv2.VideoCapture(img_path)
cap.set(cv2.CAP_PROP_POS_FRAMES, 590)
ret, frame = cap.read()
if ret:
    h = frame.shape[0]
    area = frame[int(h*0.58):int(h*0.66), :]
    res = ocr.ocr(area)
    r = res[0]
    print(f"rec_texts: {r.get('rec_texts')}")
    print(f"rec_boxes shape: {r.get('rec_boxes').shape}")
    print(f"rec_boxes: {r.get('rec_boxes')}")
    print(f"rec_polys shape: {len(r.get('rec_polys'))}, type of first: {type(r.get('rec_polys')[0])} shape: {r.get('rec_polys')[0].shape}")
    print(f"rec_polys: {r.get('rec_polys')}")
