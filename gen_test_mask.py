import subprocess
cmd = [
    'ffmpeg', '-y', '-i', '260306-待剪辑-漫剧网盘素材1/烈日重生/烈日重生-1.mp4',
    '-filter_complex',
    "[0:v]crop=x=98:y=437:w=106:h=35,boxblur=5[blur2];[0:v][blur2]overlay=x=98:y=437:enable='between(t\\,19.300\\,20.900)'[v2];"
    "[v2]crop=x=69:y=438:w=105:h=37,boxblur=5[blur4];[v2][blur4]overlay=x=69:y=438:enable='between(t\\,36.500\\,37.700)'",
    '-c:v', 'libx264', '-preset', 'fast', '-crf', '23', '-c:a', 'copy',
    'clips/test_hardcoded_mask.mp4'
]
print("Running:", " ".join(cmd))
res = subprocess.run(cmd, capture_output=True, text=True)
if res.returncode != 0:
    print(res.stderr)
else:
    print("Done")
