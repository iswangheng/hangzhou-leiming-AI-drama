text = "真正的高温末世就要开始了吧"
box = [[103, 21], [199, 21], [199, 46], [103, 46]]
char_width = (box[1][0] - box[0][0]) / len(text)

char_boxes = []
for i, char in enumerate(text):
    cx1 = box[0][0] + i * char_width
    cx2 = box[0][0] + (i + 1) * char_width
    cx3 = box[3][0] + (i + 1) * char_width
    cx4 = box[3][0] + i * char_width
    char_boxes.append([[cx1, box[0][1]], [cx2, box[1][1]], [cx3, box[2][1]], [cx4, box[3][1]]])

# check "高温末世"
sensitive_word = "高温末世"
word_len = len(sensitive_word)
for i in range(len(text) - word_len + 1):
    if text[i:i+word_len] == sensitive_word:
        found = char_boxes[i:i+word_len]
        print(f"Found: {found}")
        # combine to one box
        combined_box = [
            found[0][0],   # top-left
            found[-1][1],  # top-right
            found[-1][2],  # bottom-right
            found[0][3]    # bottom-left
        ]
        print(f"Combined: {combined_box}")
