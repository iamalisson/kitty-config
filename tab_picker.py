#!/usr/bin/env python
# Fuzzy tab switcher: type part of a tab's cwd/path or title, Enter jumps there.
# ctrl+r toggles history mode: pick a dir from a closed tab/window (logged by
# dir_history.py) and it opens as a new tab there.
# Modeled on kitty's own bundled resize_window/broadcast kittens (Handler + Loop).

import json
import os
import subprocess
import sys

from kitty.key_encoding import EventType
from kittens.tui.handler import Handler, result_handler
from kittens.tui.line_edit import LineEdit
from kittens.tui.loop import Loop
from kittens.tui.operations import styled

HISTORY_FILE = os.path.expanduser('~/.cache/kitty/dir_history.txt')


def get_history():
    try:
        with open(HISTORY_FILE) as f:
            lines = [l.strip() for l in f if l.strip()]
    except FileNotFoundError:
        return []
    seen = set()
    out = []
    for path in reversed(lines):
        if path not in seen:
            seen.add(path)
            out.append(path)
    return out


def get_tabs():
    try:
        proc = subprocess.run(['kitty', '@', 'ls'], capture_output=True, text=True, timeout=5)
    except Exception as e:
        return [], str(e)
    if proc.returncode != 0:
        return [], (proc.stderr or 'kitty @ ls failed').strip()
    data = json.loads(proc.stdout) if proc.stdout.strip() else []
    tabs = []
    for osw in data:
        for tab in osw.get('tabs', []):
            windows = tab.get('windows', [])
            active = next((w for w in windows if w.get('is_focused')), windows[0] if windows else {})
            # Every window's cwd/title in the tab is searched, not just the active one.
            window_cwds = [w.get('cwd', '') for w in windows if w.get('cwd')]
            window_titles = [w.get('title', '') for w in windows if w.get('title')]
            tabs.append({
                'id': tab['id'],
                'cwd': active.get('cwd', '~'),
                'title': tab.get('title') or active.get('title', ''),
                'window_cwds': window_cwds,
                'window_titles': window_titles,
            })
    return tabs, None


class Picker(Handler):

    def __init__(self, tabs, error):
        self.tabs = tabs
        self.error = error
        self.history = get_history()
        self.show_history = False
        self.query = LineEdit()
        self.selected = 0
        self.result = ''

    def initialize(self):
        self.cmd.set_cursor_visible(False)
        self.draw_screen()

    def matches(self):
        q = self.query.current_input.lower()
        if self.show_history:
            if not q:
                return self.history
            return [p for p in self.history if q in p.lower()]
        if not q:
            return self.tabs
        out = []
        for t in self.tabs:
            haystacks = [t['cwd'], t['title']] + t['window_cwds'] + t['window_titles']
            if any(q in h.lower() for h in haystacks):
                out.append(t)
        return out

    def draw_screen(self):
        items = self.matches()
        self.selected = max(0, min(self.selected, len(items) - 1))
        self.cmd.clear_screen()
        p = self.print
        title = 'Reopen a directory' if self.show_history else 'Switch to tab'
        p(styled(title, bold=True), ' (', styled('Esc', italic=True), ' cancel, ',
          styled('ctrl+r', italic=True), ' toggle history)')
        p('> ' + self.query.current_input)
        p()
        if self.show_history:
            if not items:
                p(styled('  no history yet (closes a tab/window to log its cwd)', fg='red'))
            for i, path in enumerate(items):
                p(styled('> ' + path, reverse=True) if i == self.selected else '  ' + path)
            return
        if self.error:
            p(styled('  kitty @ ls failed: ' + self.error, fg='red'))
            p(styled('  (remote control needs a kitty restart to take effect)', fg='gray', fg_intense=True))
        elif not items:
            p(styled('  no match', fg='red'))
        for i, t in enumerate(items):
            others = ' · '.join(c for c in t['window_cwds'] if c and c != t['cwd'])
            line = f"{t['cwd']}  {styled(t['title'], fg='gray', fg_intense=True)}"
            if others:
                line += '  ' + styled('[+ ' + others + ']', fg='blue', fg_intense=True)
            p(styled('> ' + line, reverse=True) if i == self.selected else '  ' + line)

    def on_text(self, text, in_bracketed_paste=False):
        self.query.on_text(text, in_bracketed_paste)
        self.selected = 0
        self.draw_screen()

    def on_key(self, key_event):
        if key_event.type is EventType.RELEASE:
            return
        if key_event.matches('esc'):
            self.result = ''
            self.quit_loop(0)
            return
        if key_event.matches('enter'):
            items = self.matches()
            if items:
                self.result = ('open:' + items[self.selected] if self.show_history
                                else 'switch:' + str(items[self.selected]['id']))
            self.quit_loop(0)
            return
        if key_event.matches('ctrl+r'):
            self.show_history = not self.show_history
            self.selected = 0
            self.draw_screen()
            return
        if key_event.matches('down') or key_event.matches('ctrl+n'):
            self.selected += 1
            self.draw_screen()
            return
        if key_event.matches('up') or key_event.matches('ctrl+p'):
            self.selected -= 1
            self.draw_screen()
            return
        if self.query.on_key(key_event):
            self.selected = 0
            self.draw_screen()


def main(args):
    tabs, error = get_tabs()
    loop = Loop()
    handler = Picker(tabs, error)
    loop.loop(handler)
    return handler.result


@result_handler()
def handle_result(args, answer, target_window_id, boss):
    if not answer:
        return
    kind, value = answer.split(':', 1)
    if kind == 'switch':
        tid = int(value)
        for tab in boss.all_tabs:
            if tab.id == tid:
                boss.set_active_tab(tab)
                break
    elif kind == 'open':
        subprocess.run(['kitty', '@', 'launch', '--type=tab', '--cwd', value])


if __name__ == '__main__':
    main(sys.argv)
