import sys
sys.path.insert(0, '/Users/weilingkeji/Documents/hangzhou-leiming-AI-drama')
import scripts.preprocess.video_cleaner as vc
import subprocess

original_run = subprocess.run

def mock_run(cmd, *args, **kwargs):
    if cmd[0] == 'ffmpeg':
        print("\n=== FFMPEG COMMAND EXECUTED ===")
        print(" ".join(cmd))
        print("===============================\n")
    return original_run(cmd, *args, **kwargs)

vc.subprocess.run = mock_run

# Use the test script to trigger the execution
import test.test_precise_mask as tpm
tpm.main()
