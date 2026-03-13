import subprocess
cmd = [
    'ffmpeg', '-y', '-i', '260306-待剪辑-漫剧网盘素材1/烈日重生/烈日重生-1.mp4',
    '-filter_complex',
    "[0:v]split=2[orig1][orig2];"
    "[orig1]crop=x=98:y=437:w=106:h=35,boxblur=5[blur0];"
    "[orig2][blur0]overlay=x=98:y=437:enable='between(t\\,19.300\\,20.900)'",
    '-c:v', 'libx264', '-preset', 'fast', '-crf', '23', '-c:a', 'copy',
    'clips/test_split.mp4'
]
res = subprocess.run(cmd, capture_output=True, text=True)
print("Done")
