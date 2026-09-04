# Watcher: logs each window's cwd on close, so tab_picker.py can offer
# "reopen a directory I had open before" alongside its live-tab search.
import os

HISTORY_FILE = os.path.expanduser('~/.cache/kitty/dir_history.txt')
MAX_LINES = 500


def on_close(boss, window, data):
    cwd = window.cwd_of_child
    if not cwd:
        return
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, 'a') as f:
        f.write(cwd + '\n')
    if os.path.getsize(HISTORY_FILE) > MAX_LINES * 200:
        with open(HISTORY_FILE) as f:
            lines = f.readlines()[-MAX_LINES:]
        with open(HISTORY_FILE, 'w') as f:
            f.writelines(lines)
