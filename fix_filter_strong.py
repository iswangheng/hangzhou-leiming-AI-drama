import subprocess
cmd = [
    'ffmpeg', '-y', '-i', '260306-待剪辑-漫剧网盘素材1/烈日重生/烈日重生-1.mp4',
    '-filter_complex',
    "[0:v]crop=x=98:y=437:w=106:h=35,boxblur=20:5[blur0];"
    "[0:v][blur0]overlay=x=98:y=437:enable='between(t\\,19.300\\,20.900)'[v0];"
    "[v0]crop=x=132:y=439:w=101:h=31,boxblur=20:5[blur1];"
    "[v0][blur1]overlay=x=132:y=439:enable='between(t\\,20.300\\,21.700)'[v1];"
    "[v1]crop=x=69:y=438:w=105:h=37,boxblur=20:5[blur2];"
    "[v1][blur2]overlay=x=69:y=438:enable='between(t\\,36.500\\,37.700)'",
    '-c:v', 'libx264', '-preset', 'fast', '-crf', '23', '-c:a', 'copy',
    'clips/test_filter_strong.mp4'
]
res = subprocess.run(cmd, capture_output=True, text=True)
