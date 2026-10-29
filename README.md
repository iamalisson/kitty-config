<div align="center">

# kitty-config

<img src="https://sw.kovidgoyal.net/kitty/_static/kitty.svg" height="72" alt="kitty" />

**Personal kitty terminal config**
Nord themed. Splits-first tiling. Fuzzy tab switching.

[![kitty](https://img.shields.io/badge/kitty-terminal-1793D1?style=flat-square)](https://sw.kovidgoyal.net/kitty/)
[![Nord](https://img.shields.io/badge/theme-Nord-88C0D0?style=flat-square)](https://www.nordtheme.com/)
[![Python](https://img.shields.io/badge/kitten-python-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org)
[![Status](https://img.shields.io/badge/status-personal-lightgrey?style=flat-square)]()

</div>

---

## Overview

Drop-in [kitty](https://sw.kovidgoyal.net/kitty/) config: **Nord** color theme, dynamic-tiling window layout with splits as the default, a custom wallpaper blended into the terminal background, and a fuzzy tab picker kitten for jumping straight to a tab by typing part of its path or title.

> Fullscreen on launch, cwd-aware new windows/tabs, no session-restore surprises.

---

## Install

> **Back up your existing kitty config first** — this will overwrite `~/.config/kitty`.

```bash
git clone https://github.com/iamalisson/kitty-config.git ~/.config/kitty
```

Reload with `ctrl+shift+F5`, or just restart kitty.

---

## Keybindings

| Key                  | Action                                  |
| --------------------- | ---------------------------------------- |
| `ctrl+shift+enter`     | New window (inherits cwd)               |
| `ctrl+shift+t`         | New tab (inherits cwd)                  |
| `ctrl+shift+n`         | New OS window (inherits cwd)            |
| `ctrl+shift+space`     | New window (inherits cwd) — fcitx5 fallback |
| `ctrl+shift+z`         | Toggle stack layout                     |
| `ctrl+shift+p`         | Fuzzy-jump to a tab (`tab_picker.py`)   |
| `ctrl+shift+d`         | Open the picker straight in dir-history mode |
| `ctrl+r` (inside picker) | Toggle history mode — cd the current window to a dir you had open |
| `↑↓` / `PgUp PgDn` (inside picker) | Move / scroll; type words (any order) to filter, `Enter` picks |

---

## What's In It

| File               | Purpose                                                              |
| ------------------ | --------------------------------------------------------------------- |
| `kitty.conf`        | Main config — font, cursor, layout, keybindings, wallpaper            |
| `theme.conf`        | Nord color theme (full Frost + Aurora palette)                        |
| `session.conf`      | Fullscreen-on-launch state, no windows/layout (avoids restore bugs)   |
| `tab_picker.py`     | Fuzzy tab switcher kitten — type part of a cwd or title, Enter jumps; `ctrl+r` reopens a closed tab's dir |
| `dir_history.py`    | Watcher — logs each closed window's cwd to `~/.cache/kitty/dir_history.txt` for the picker's history mode |
| `wallpaper.png`     | Background artwork, tinted to match the Nord palette                  |

---

## Project Structure

```
kitty/
├── kitty.conf
├── theme.conf
├── session.conf
├── tab_picker.py
└── wallpaper.png
```

---

## Layout & Behavior

- `enabled_layouts splits,stack,tall,grid` — dynamic tiling, splits first
- Every "open something new" shortcut inherits the cwd last reported via OSC 7 (shell prompt, or nvim's project root)
- Background wallpaper scaled and tinted to blend into the Nord background
- `startup_session session.conf` only sets `os_window_state fullscreen` — deliberately carries no window/tab entries, so it can't resurrect stale layouts

---

## Credits

Theme: [Nord](https://www.nordtheme.com/) by Eric N. Vander Weele. Terminal: [kitty](https://sw.kovidgoyal.net/kitty/) by Kovid Goyal.

---

## Disclaimer

Personal config, tuned for my own workflow. Review before applying to your machine.
