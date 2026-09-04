# Watcher: logs a window's cwd whenever it changes (each new prompt, so a
# plain `cd` counts) and on close, so tab_picker.py can offer "reopen a
# directory I had open before" alongside its live-tab search.
import os

HISTORY_FILE = os.path.expanduser('~/.cache/kitty/dir_history.txt')
MAX_LINES = 500

_last_cwd = {}


def _log(window):
    cwd = window.cwd_of_child
    if not cwd or _last_cwd.get(window.id) == cwd:
        return
    _last_cwd[window.id] = cwd
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, 'a') as f:
        f.write(cwd + '\n')
    if os.path.getsize(HISTORY_FILE) > MAX_LINES * 200:
        with open(HISTORY_FILE) as f:
            lines = f.readlines()[-MAX_LINES:]
        with open(HISTORY_FILE, 'w') as f:
            f.writelines(lines)


def on_cmd_startstop(boss, window, data):
    _log(window)


def on_close(boss, window, data):
    _log(window)
    _last_cwd.pop(window.id, None)
