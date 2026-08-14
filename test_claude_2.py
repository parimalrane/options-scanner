import traceback
import subprocess
try:
    with open('test_results.txt', 'w') as f: f.write('starting\n')
    subprocess.run(['taskkill', '/F', '/IM', 'python.exe'])
except Exception as e:
    with open('test_results.txt', 'w') as f: f.write(traceback.format_exc())
