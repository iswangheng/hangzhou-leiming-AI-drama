import cv2
import numpy as np
import os
import logging
from paddleocr import PaddleOCR

# Suppress debug logs from Paddle
logging.getLogger('ppocr').setLevel(logging.ERROR)

ocr = PaddleOCR(lang='ch')
video_path = '260306-待剪辑-漫剧网盘素材1/烈日重生/烈日重生-1.mp4'

cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS)
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))

y_start = int(height * 0.5847)
y_end = y_start + int(height * 0.0764)

os.makedirs('clips/debug_frames', exist_ok=True)

def process_frame(time_sec, name_prefix, sensitive_word="高温末世"):
    frame_idx = int(time_sec * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    if not ret: return
    
    # 裁剪区域
    subtitle_area = frame[y_start:y_end, :]
    
    result = ocr.ocr(subtitle_area)
    
    canvas = frame.copy()
    
    if result and len(result) > 0 and result[0]:
        res = result[0]
        if isinstance(res, dict):
            rec_texts = res.get('rec_texts', [])
            rec_boxes = res.get('rec_polys', res.get('rec_boxes', []))
            for text, box in zip(rec_texts, rec_boxes):
                if hasattr(box, 'tolist'): box = box.tolist()
                print(f"[{time_sec:.1f}s] text: '{text}' box: {box}")
                
                if len(box) == 4 and isinstance(box[0], (list, tuple)):
                    p0, p1, p2, p3 = box[0], box[1], box[2], box[3]
                    # 画完整的整行框 (绿色)
                    pts = np.array([[p0[0], p0[1]+y_start], [p1[0], p1[1]+y_start], 
                                    [p2[0], p2[1]+y_start], [p3[0], p3[1]+y_start]], np.int32)
                    pts = pts.reshape((-1, 1, 2))
                    cv2.polylines(canvas, [pts], True, (0, 255, 0), 2)
                    
                    # 计算插值的敏感词框 (红色)
                    if sensitive_word in text:
                        idx = text.index(sensitive_word)
                        word_len = len(sensitive_word)
                        char_w = (p1[0] - p0[0]) / len(text)
                        
                        cx1 = int(p0[0] + idx * char_w)
                        cx2 = int(p0[0] + (idx + word_len) * char_w)
                        
                        # 红色框
                        cv2.rectangle(canvas, (cx1, int(p0[1]+y_start)), (cx2, int(p2[1]+y_start)), (0, 0, 255), 2)
                        print(f"[{time_sec:.1f}s] => 匹配到敏感词！计算出的区域 x1={cx1}, x2={cx2}")
        else:
            for line in res:
                box = line[0]
                text = line[1][0] if isinstance(line[1], tuple) else line[1]
                print(f"[{time_sec:.1f}s] text: '{text}' box: {box}")
                if len(box) == 4:
                    p0, p1, p2, p3 = box[0], box[1], box[2], box[3]
                    pts = np.array([[p0[0], p0[1]+y_start], [p1[0], p1[1]+y_start], 
                                    [p2[0], p2[1]+y_start], [p3[0], p3[1]+y_start]], np.int32)
                    pts = pts.reshape((-1, 1, 2))
                    cv2.polylines(canvas, [pts], True, (0, 255, 0), 2)
                    
                    if sensitive_word in text:
                        idx = text.index(sensitive_word)
                        word_len = len(sensitive_word)
                        char_w = (p1[0] - p0[0]) / len(text)
                        cx1 = int(p0[0] + idx * char_w)
                        cx2 = int(p0[0] + (idx + word_len) * char_w)
                        cv2.rectangle(canvas, (cx1, int(p0[1]+y_start)), (cx2, int(p2[1]+y_start)), (0, 0, 255), 2)
                        print(f"[{time_sec:.1f}s] => 匹配到敏感词！计算出的区域 x1={cx1}, x2={cx2}")
    else:
        print(f"[{time_sec:.1f}s] 未检测到文字")
        
    cv2.imwrite(f"clips/debug_frames/{name_prefix}_{time_sec:.1f}.jpg", canvas)

print("--- 调试 19秒附近 ---")
for t in np.arange(19.3, 19.8, 0.1): process_frame(t, "T19")

print("--- 调试 37秒附近 ---")
for t in np.arange(37.3, 38.2, 0.1): process_frame(t, "T37")

cap.release()
