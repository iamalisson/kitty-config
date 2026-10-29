#!/usr/bin/env python
# Fuzzy tab switcher: type part of a tab's cwd/path or title, Enter jumps there.
# ctrl+r toggles history mode: pick a dir from a closed tab/window (logged by
# dir_history.py) and cds the current window there. Pass `history` as the
# first arg to open straight in history mode.
# Query is split on spaces; every word must appear (any order, case-insensitive).
# The list scrolls with the selection, so long histories stay reachable.
# Modeled on kitty's own bundled resize_window/broadcast kittens (Handler + Loop).

import json
import os
import shlex
import subprocess
import sys

from kitty.key_encoding import EventType
from kittens.tui.handler import Handler, result_handler
from kittens.tui.line_edit import LineEdit
from kittens.tui.loop import Loop
from kittens.tui.operations import styled

HISTORY_FILE = os.path.expanduser('~/.cache/kitty/dir_history.txt')
HOME = os.path.expanduser('~')
# Title, query and blank line above the list; status line below it.
HEADER_ROWS = 3
FOOTER_ROWS = 1


def get_history():
    try:
        with open(HISTORY_FILE) as f:
            lines = [l.strip() for l in f if l.strip()]
    except FileNotFoundError:
        return []
    seen = set()
    out = []
    for path in reversed(lines):
        if path not in seen and os.path.isdir(path):
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


def tilde(path):
    if path == HOME or path.startswith(HOME + '/'):
        return '~' + path[len(HOME):]
    return path


def clip(text, width):
    if width <= 0:
        return ''
    return text if len(text) <= width else text[:max(width - 1, 0)] + '…'


def matches_all(words, haystacks):
    hay = '\n'.join(haystacks).lower()
    return all(w in hay for w in words)


class Picker(Handler):

    def __init__(self, tabs, error, show_history=False):
        self.tabs = tabs
        self.error = error
        self.history = get_history()
        self.show_history = show_history
        self.query = LineEdit()
        self.selected = 0
        self.offset = 0
        self.result = ''

    def initialize(self):
        self.cmd.set_cursor_visible(False)
        self.draw_screen()

    def on_resize(self, new_size):
        super().on_resize(new_size)
        self.draw_screen()

    def matches(self):
        words = self.query.current_input.lower().split()
        if self.show_history:
            if not words:
                return self.history
            hits = [p for p in self.history if matches_all(words, [p, tilde(p)])]
            # Dirs whose own name matches the last word come first, keeping recency order otherwise.
            last = words[-1]
            return sorted(hits, key=lambda p: last not in os.path.basename(p).lower())
        if not words:
            return self.tabs
        return [t for t in self.tabs
                if matches_all(words, [t['cwd'], t['title']] + t['window_cwds'] + t['window_titles'])]

    def visible_rows(self):
        return max(1, self.screen_size.rows - HEADER_ROWS - FOOTER_ROWS)

    def clamp(self, count):
        self.selected = max(0, min(self.selected, count - 1))
        rows = self.visible_rows()
        if self.selected < self.offset:
            self.offset = self.selected
        elif self.selected >= self.offset + rows:
            self.offset = self.selected - rows + 1
        self.offset = max(0, min(self.offset, max(count - rows, 0)))

    def draw_screen(self):
        items = self.matches()
        self.clamp(len(items))
        cols = self.screen_size.cols
        self.cmd.clear_screen()
        p = self.print
        title = 'Reopen a directory' if self.show_history else 'Switch to tab'
        p(styled(title, bold=True), ' (', styled('Esc', italic=True), ' cancel, ',
          styled('ctrl+r', italic=True), ' toggle history)')
        p('> ' + self.query.current_input + styled(' ', reverse=True))
        p()
        rows = self.visible_rows()
        window = items[self.offset:self.offset + rows]
        if self.show_history:
            if not self.history:
                p(styled('  no history yet (cd somewhere or close a window to log its cwd)', fg='red'))
            elif not items:
                p(styled('  no match', fg='red'))
            for i, path in enumerate(window, self.offset):
                line = clip(tilde(path), cols - 2)
                p(styled('> ' + line, reverse=True) if i == self.selected else '  ' + line)
        else:
            if self.error:
                p(styled('  kitty @ ls failed: ' + self.error, fg='red'))
                p(styled('  (remote control needs a kitty restart to take effect)', fg='gray', fg_intense=True))
            elif not items:
                p(styled('  no match', fg='red'))
            for i, t in enumerate(window, self.offset):
                cwd = clip(tilde(t['cwd']), cols - 2)
                room = cols - 2 - len(cwd) - 2
                tab_title = clip(t['title'], room)
                room -= len(tab_title) + 2
                others = ' · '.join(tilde(c) for c in t['window_cwds'] if c and c != t['cwd'])
                others = clip('[+ ' + others + ']', room) if others and room > 4 else ''
                if i == self.selected:
                    line = '  '.join(x for x in (cwd, tab_title, others) if x)
                    p(styled('> ' + line, reverse=True))
                    continue
                line = cwd
                if tab_title:
                    line += '  ' + styled(tab_title, fg='gray', fg_intense=True)
                if others:
                    line += '  ' + styled(others, fg='blue', fg_intense=True)
                p('  ' + line)
        if items:
            shown_to = min(self.offset + rows, len(items))
            status = f'{self.selected + 1}/{len(items)}'
            if len(items) > rows:
                status += f'  (showing {self.offset + 1}-{shown_to}, ↑↓ / PgUp PgDn to scroll)'
            self.cmd.set_cursor_position(0, self.screen_size.rows - 1)
            self.write(styled(clip(status, cols), fg='gray', fg_intense=True))

    def on_text(self, text, in_bracketed_paste=False):
        self.query.on_text(text, in_bracketed_paste)
        self.selected = self.offset = 0
        self.draw_screen()

    def move(self, delta, wrap=True):
        count = len(self.matches())
        if not count:
            return
        target = self.selected + delta
        if wrap and abs(delta) == 1:
            target %= count
        self.selected = max(0, min(target, count - 1))
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
            self.selected = self.offset = 0
            self.draw_screen()
            return
        if key_event.matches('down') or key_event.matches('ctrl+n') or key_event.matches('ctrl+j'):
            return self.move(1)
        if key_event.matches('up') or key_event.matches('ctrl+p') or key_event.matches('ctrl+k'):
            return self.move(-1)
        if key_event.matches('page_down'):
            return self.move(self.visible_rows(), wrap=False)
        if key_event.matches('page_up'):
            return self.move(-self.visible_rows(), wrap=False)
        if self.query.on_key(key_event):
            self.selected = self.offset = 0
            self.draw_screen()


def main(args):
    tabs, error = get_tabs()
    loop = Loop()
    handler = Picker(tabs, error, show_history='history' in args[1:])
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
        w = boss.window_id_map.get(target_window_id) or boss.active_window
        if w:
            w.write_to_child(f'cd {shlex.quote(value)}\n')


if __name__ == '__main__':
    main(sys.argv)
