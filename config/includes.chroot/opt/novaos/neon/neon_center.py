#!/usr/bin/env python3
"""
Neon Center - مركز التحكم في NeonOS
الرئيسية | الخلفيات | الألعاب | تطبيقات ويندوز | التحديثات | الإعدادات | حول
"""
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, GLib, GdkPixbuf

import glob
import os
import platform
import random
import shutil
import subprocess
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import neon_ui as ui
import neon_pages

UPDATER = "/opt/novaos/updater/updater.py"
EXE_HANDLER = "/opt/novaos/neon/neon-run-exe.sh"
BOTTLES = "com.usebottles.bottles"
STEAM = "com.valvesoftware.Steam"
LUTRIS = "net.lutris.Lutris"


def spawn(cmd):
    """يشغّل تطبيقاً منفصلاً بدون انتظار."""
    try:
        subprocess.Popen(cmd, shell=isinstance(cmd, str), start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as e:
        print("spawn failed:", e)


def flatpak_installed(app_id):
    if not shutil.which("flatpak"):
        return False
    r = ui.run_quiet(["flatpak", "info", app_id], timeout=10)
    return bool(r and r.returncode == 0)


def page_box(title, subtitle=""):
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
    box.set_border_width(32)
    box.pack_start(ui.label(title, "title-1"), False, False, 0)
    if subtitle:
        box.pack_start(ui.label(subtitle, "dim", wrap=True), False, False, 0)
    return box


# ------------------------------------------------------------------ XO مع بوت
class TicTacToe(Gtk.Box):
    LINES = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.board = [""] * 9
        self.over = False
        self.score = {"You": 0, "Bot": 0, "Draw": 0}

        top = Gtk.Box(spacing=10)
        top.pack_start(ui.label("Bot level:"), False, False, 0)
        self.level = Gtk.ComboBoxText()
        for lv in ("Easy", "Normal", "Legendary"):
            self.level.append_text(lv)
        self.level.set_active(1)
        top.pack_start(self.level, False, False, 0)
        top.pack_start(ui.button("New game", "accent", lambda *_: self.reset()), False, False, 0)
        self.score_lb = ui.label("", "dim")
        top.pack_end(self.score_lb, False, False, 0)
        self.pack_start(top, False, False, 0)

        grid = Gtk.Grid(row_spacing=8, column_spacing=8)
        self.cells = []
        for i in range(9):
            b = Gtk.Button(label="")
            b.get_style_context().add_class("cell")
            b.connect("clicked", self.on_click, i)
            grid.attach(b, i % 3, i // 3, 1, 1)
            self.cells.append(b)
        self.pack_start(grid, False, False, 0)
        self.msg = ui.label("Your move — you are X", "neon-text")
        self.pack_start(self.msg, False, False, 0)
        self._refresh_score()

    def _refresh_score(self):
        s = self.score
        self.score_lb.set_text(f"You {s['You']}  ·  Bot {s['Bot']}  ·  Draw {s['Draw']}")

    def winner(self, b):
        for x, y, z in self.LINES:
            if b[x] and b[x] == b[y] == b[z]:
                return b[x]
        return "Draw" if all(b) else None

    def minimax(self, b, turn):
        w = self.winner(b)
        if w == "O":
            return 1
        if w == "X":
            return -1
        if w == "Draw":
            return 0
        scores = []
        for i in range(9):
            if not b[i]:
                b[i] = turn
                scores.append(self.minimax(b, "X" if turn == "O" else "O"))
                b[i] = ""
        return max(scores) if turn == "O" else min(scores)

    def bot_move(self):
        free = [i for i in range(9) if not self.board[i]]
        lvl = self.level.get_active_text()
        if lvl == "Easy" or (lvl == "Normal" and random.random() < 0.35):
            return random.choice(free)
        best, best_i = -2, free[0]
        for i in free:
            self.board[i] = "O"
            sc = self.minimax(self.board, "X")
            self.board[i] = ""
            if sc > best:
                best, best_i = sc, i
        return best_i

    def mark(self, i, who):
        self.board[i] = who
        self.cells[i].set_label(who)
        self.cells[i].set_sensitive(False)

    def check_end(self):
        w = self.winner(self.board)
        if not w:
            return False
        self.over = True
        if w == "X":
            self.score["You"] += 1
            self.msg.set_text("You win! 🎉")
        elif w == "O":
            self.score["Bot"] += 1
            self.msg.set_text("Bot wins — try again")
        else:
            self.score["Draw"] += 1
            self.msg.set_text("It's a draw")
        self._refresh_score()
        return True

    def on_click(self, _btn, i):
        if self.over or self.board[i]:
            return
        self.mark(i, "X")
        if self.check_end():
            return
        GLib.timeout_add(280, self._bot_turn)

    def _bot_turn(self):
        if not self.over:
            self.mark(self.bot_move(), "O")
            if not self.check_end():
                self.msg.set_text("Your move — you are X")
        return False

    def reset(self):
        self.board = [""] * 9
        self.over = False
        for c in self.cells:
            c.set_label("")
            c.set_sensitive(True)
        self.msg.set_text("Your move — you are X")


# -------------------------------------------------------------------- النافذة
class NeonCenter(neon_pages.ExtraPages, Gtk.Window):
    PAGES = [
        ("home", "🏠", "Home"),
        ("network", "📶", "Network"),
        ("wallpapers", "🎨", "Appearance"),
        ("language", "🌐", "Language"),
        ("drivers", "🧩", "Drivers"),
        ("updates", "⬆", "Updates"),
        ("games", "🎮", "Games"),
        ("windows", "🪟", "Windows Apps"),
        ("settings", "⚙", "Performance"),
        ("about", "ℹ", "About"),
    ]

    def __init__(self, start_page="home"):
        super().__init__(title="Settings")
        self.set_default_size(*ui.fit_size(1080, 700))
        self.get_style_context().add_class("neon")
        if os.path.exists(ui.LOGO):
            try:
                self.set_icon_from_file(ui.LOGO)
            except GLib.Error:
                pass

        root = Gtk.Box()
        self.add(root)

        side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        side.set_size_request(230, -1)
        side.get_style_context().add_class("sidebar")
        head = Gtk.Box(spacing=12)
        head.set_border_width(18)
        try:
            pb = GdkPixbuf.Pixbuf.new_from_file_at_size(ui.LOGO, 44, 44)
            logo = Gtk.Image.new_from_pixbuf(pb)
            logo.get_style_context().add_class("logo-glow")
            head.pack_start(logo, False, False, 0)
        except GLib.Error:
            pass
        head.pack_start(ui.label("<b>Neon</b>OS", "title-2 neon-text", markup=True), False, False, 0)
        side.pack_start(head, False, False, 0)

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        for key, icon, name in self.PAGES:
            row = Gtk.ListBoxRow()
            row.page_key = key
            hb = Gtk.Box(spacing=12)
            hb.pack_start(ui.label(icon), False, False, 0)
            hb.pack_start(ui.label(name), False, False, 0)
            if key == "updates":
                self.update_dot = ui.label("●", "dot-yellow")
                self.update_dot.set_no_show_all(True)
                hb.pack_end(self.update_dot, False, False, 0)
            row.add(hb)
            self.listbox.add(row)
        self.listbox.connect("row-selected", self.on_row)
        side.pack_start(self.listbox, True, True, 0)
        root.pack_start(side, False, False, 0)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_UP_DOWN)
        self.stack.set_transition_duration(340)
        root.pack_start(self.stack, True, True, 0)

        self.update_banner = None
        self.update_dot = getattr(self, "update_dot", None)
        builders = {
            "home": self.build_home, "wallpapers": self.build_wallpapers,
            "games": self.build_games, "windows": self.build_windows,
            "updates": self.build_updates, "settings": self.build_settings,
            "about": self.build_about, "network": self.build_network,
            "language": self.build_language, "drivers": self.build_drivers,
        }
        for key, _i, _n in self.PAGES:
            sw = Gtk.ScrolledWindow()
            sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            sw.add(builders[key]())
            self.stack.add_named(sw, key)

        self.select_page(start_page)
        threading.Thread(target=self.bg_check_update, daemon=True).start()

    def select_page(self, key):
        for row in self.listbox.get_children():
            if row.page_key == key:
                self.listbox.select_row(row)
                return

    def on_row(self, _lb, row):
        if row:
            self.stack.set_visible_child_name(row.page_key)

    # ---- الرئيسية
    def build_home(self):
        box = page_box("Welcome to NeonOS", f"Version {ui.os_version()}  ·  everything in one place")

        self.update_banner = Gtk.Revealer()
        self.update_banner.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self.update_banner.set_transition_duration(450)
        bn = Gtk.Box(spacing=14)
        bn.get_style_context().add_class("banner")
        self.banner_lb = ui.label("Update available", "title-2")
        bn.pack_start(self.banner_lb, True, True, 0)
        bn.pack_start(ui.button("Install now", "accent", lambda *_: self.select_page("updates")), False, False, 0)
        bn.pack_start(ui.button("Later", None, lambda *_: self.update_banner.set_reveal_child(False)), False, False, 0)
        self.update_banner.add(bn)
        box.pack_start(self.update_banner, False, False, 6)

        tiles = Gtk.FlowBox()
        tiles.set_selection_mode(Gtk.SelectionMode.NONE)
        tiles.set_max_children_per_line(4)
        tiles.set_column_spacing(16)
        tiles.set_row_spacing(16)
        items = [
            ("📊", "Task Manager", lambda: spawn(["python3", "/opt/novaos/neon/neon_taskmgr.py"])),
            ("🎨", "Appearance", lambda: self.select_page("wallpapers")),
            ("🎮", "Games", lambda: self.select_page("games")),
            ("🪟", "Windows Apps", lambda: self.select_page("windows")),
            ("⬆", "Updates", lambda: self.select_page("updates")),
            ("🌡", "ThermalCtl", lambda: spawn(["python3", "/opt/novaos/thermalctl/thermalctl_gui.py"])),
            ("🤖", "AI Assistant", lambda: spawn(["python3", "/opt/novaos/ai-assistant/ai_assistant.py"])),
            ("⚙", "Performance", lambda: self.select_page("settings")),
        ]
        for icon, name, fn in items:
            b = Gtk.Button()
            b.get_style_context().add_class("tile")
            v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            v.pack_start(ui.label(f"<span size='36000'>{icon}</span>", markup=True, xalign=0.5), False, False, 0)
            v.pack_start(ui.label(name, xalign=0.5), False, False, 0)
            b.add(v)
            b.connect("clicked", lambda _b, f=fn: f())
            tiles.add(b)
        box.pack_start(tiles, False, False, 10)
        return box

    def bg_check_update(self):
        r = ui.run_quiet(["python3", UPDATER, "check"], timeout=45)
        if not r:
            return
        for line in r.stdout.splitlines():
            if line.startswith("RESULT available"):
                ver = line.split()[-1]
                GLib.idle_add(self._show_banner, ver)

    def _show_banner(self, ver):
        if self.update_banner:
            self.banner_lb.set_text(f"⬆  NeonOS {ver} is available")
            self.update_banner.set_reveal_child(True)
        if self.update_dot:
            self.update_dot.show()
            self.update_dot.set_tooltip_text(f"Update {ver} available")
        return False

    # ---- الخلفيات
    def build_wallpapers(self):
        box = page_box("Appearance", "Taskbar and wallpapers — changes apply instantly.")
        box.pack_start(self.taskbar_card(), False, False, 4)
        box.pack_start(ui.label("Wallpapers", "title-2"), False, False, 6)
        fb = Gtk.FlowBox()
        fb.set_selection_mode(Gtk.SelectionMode.NONE)
        fb.set_column_spacing(14)
        fb.set_row_spacing(14)
        files = sorted(glob.glob(os.path.join(ui.WALL_DIR, "*.jpg")) + glob.glob(os.path.join(ui.WALL_DIR, "*.png")))
        files += sorted(glob.glob(os.path.expanduser("~/Pictures/*.jpg")) + glob.glob(os.path.expanduser("~/Pictures/*.png")))
        for f in files:
            try:
                pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(f, 240, 135, True)
            except GLib.Error:
                continue
            b = Gtk.Button()
            v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            v.pack_start(Gtk.Image.new_from_pixbuf(pb), False, False, 0)
            name = os.path.splitext(os.path.basename(f))[0].replace("neon-", "").title()
            v.pack_start(ui.label(name, xalign=0.5), False, False, 0)
            b.add(v)
            b.connect("clicked", lambda _b, p=f: threading.Thread(target=ui.set_wallpaper, args=(p,), daemon=True).start())
            fb.add(b)
        box.pack_start(fb, False, False, 6)
        box.pack_start(ui.button("Choose your own picture…", "accent", self.pick_wallpaper), False, False, 6)
        return box

    def pick_wallpaper(self, _b):
        dlg = Gtk.FileChooserDialog(title="Choose a wallpaper", parent=self, action=Gtk.FileChooserAction.OPEN)
        dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "Set wallpaper", Gtk.ResponseType.OK)
        flt = Gtk.FileFilter()
        flt.set_name("Images")
        for pat in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
            flt.add_pattern(pat)
        dlg.add_filter(flt)
        if dlg.run() == Gtk.ResponseType.OK:
            threading.Thread(target=ui.set_wallpaper, args=(dlg.get_filename(),), daemon=True).start()
        dlg.destroy()

    # ---- الألعاب
    GAMES = [
        ("♟", "Chess vs Stockfish bot", "gnome-chess", None),
        ("⚫", "Reversi vs bot", "iagno", None),
        ("🔴", "Four in a Row vs bot", "four-in-a-row", None),
        ("🎲", "Backgammon vs GNU bot", "gnubg", None),
        ("💣", "Mines", "gnome-mines", None),
        ("🧱", "Tetris", "quadrapassel", None),
        ("🔢", "Sudoku", "gnome-sudoku", None),
        ("🐍", "Snake (Nibbles)", "gnome-nibbles", None),
        ("🔟", "2048", "gnome-2048", None),
        ("🧩", "Klotski puzzle", "gnome-klotski", None),
        ("🎯", "Five or More", "five-or-more", None),
        ("💡", "Lights Off", "lightsoff", None),
        ("🀄", "Mahjongg", "gnome-mahjongg", None),
        ("🃏", "Solitaire", "sol", None),
        ("🐧", "SuperTux (platformer)", "supertux2", None),
        ("🫧", "Frozen Bubble", "frozen-bubble", None),
        ("⛏", "Luanti — free blocks sandbox, offline, no account", "luanti|minetest", None),
        ("🏎", "SuperTuxKart — race vs AI karts", "supertuxkart", "org.supertuxkart.SuperTuxKart"),
        ("🔫", "OpenArena — shooter with many bots", "openarena", "ws.openarena.OpenArena"),
        ("🎯", "Xonotic — arena shooter with bots", "xonotic", "org.xonotic.Xonotic"),
        ("🟩", "Minecraft Java (Prism) — needs your own purchased account", "/opt/novaos/minecraft/first-run.sh", None),
    ]

    def build_games(self):
        box = page_box("Games", "22 games — play against bots, race, solve puzzles. Luanti is a free sandbox that works offline.")
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        card.get_style_context().add_class("card")
        card.pack_start(ui.label("❌⭕  Tic-Tac-Toe vs Bot", "title-2"), False, False, 0)
        card.pack_start(TicTacToe(), False, False, 0)
        box.pack_start(card, False, False, 6)

        box.pack_start(ui.label("More games", "title-2"), False, False, 10)
        for icon, name, cmd, flat in self.GAMES:
            row = Gtk.Box(spacing=12)
            row.get_style_context().add_class("card")
            row.pack_start(ui.label(f"<span size='20000'>{icon}</span>", markup=True), False, False, 0)
            row.pack_start(ui.label(name), True, True, 0)
            found = next((c for c in cmd.split("|") if shutil.which(c) or os.path.exists(c)), None)
            if found:
                row.pack_end(ui.button("Play", "accent", lambda _b, c=found: spawn([c])), False, False, 0)
            elif flat and flatpak_installed(flat):
                row.pack_end(ui.button("Play", "accent", lambda _b, f=flat: spawn(["flatpak", "run", f])), False, False, 0)
            elif flat:
                row.pack_end(ui.button("Install", None, lambda _b, f=flat, n=name: self.install_flatpak(f, n)), False, False, 0)
            else:
                row.pack_end(ui.label("not installed", "dim"), False, False, 0)
            box.pack_start(row, False, False, 0)
        return box

    def install_flatpak(self, app_id, name):
        ok, _ = ui.run_dialog(self, f"Installing {name}",
                              ["flatpak", "install", "-y", "--noninteractive", "flathub", app_id],
                              "Installed — reopen this page to play")
        return ok

    # ---- تطبيقات ويندوز
    def build_windows(self):
        box = page_box("Windows Apps",
                       "Run .exe programs and Windows games. Double-clicking any .exe file opens it automatically.")
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card.get_style_context().add_class("card")
        card.pack_start(ui.label("Run a Windows program", "title-2"), False, False, 0)
        card.pack_start(ui.label("Pick any .exe or .msi file. On first use NeonOS installs the compatibility layer "
                                 "(about 500 MB, needs internet).", "dim", wrap=True), False, False, 0)
        card.pack_start(ui.button("Choose .exe file…", "accent", self.pick_exe), False, False, 0)
        box.pack_start(card, False, False, 6)

        tools = [
            ("🍾", "Bottles — runs Windows apps in isolated bottles", BOTTLES),
            ("🎮", "Steam — thousands of games (Proton)", STEAM),
            ("🕹", "Lutris — games from many stores", LUTRIS),
        ]
        for icon, name, app_id in tools:
            row = Gtk.Box(spacing=12)
            row.get_style_context().add_class("card")
            row.pack_start(ui.label(f"<span size='20000'>{icon}</span>", markup=True), False, False, 0)
            row.pack_start(ui.label(name), True, True, 0)
            if flatpak_installed(app_id):
                row.pack_end(ui.button("Open", "accent", lambda _b, a=app_id: spawn(["flatpak", "run", a])), False, False, 0)
            else:
                row.pack_end(ui.button("Install", None, lambda _b, a=app_id, n=name: self.install_flatpak(a, n)), False, False, 0)
            box.pack_start(row, False, False, 0)
        box.pack_start(ui.label("Note: programs with strict anti-cheat or kernel drivers may not work.", "dim", wrap=True),
                       False, False, 8)
        return box

    def pick_exe(self, _b):
        dlg = Gtk.FileChooserDialog(title="Choose a Windows program", parent=self, action=Gtk.FileChooserAction.OPEN)
        dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "Run", Gtk.ResponseType.OK)
        flt = Gtk.FileFilter()
        flt.set_name("Windows programs")
        for pat in ("*.exe", "*.EXE", "*.msi", "*.MSI", "*.bat"):
            flt.add_pattern(pat)
        dlg.add_filter(flt)
        if dlg.run() == Gtk.ResponseType.OK:
            spawn([EXE_HANDLER, dlg.get_filename()])
        dlg.destroy()

    # ---- التحديثات
    def build_updates(self):
        box = page_box("Updates", "Updates download and install in the background — no restart needed.")
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card.get_style_context().add_class("card")
        self.ver_lb = ui.label(f"Installed version:  <b>{ui.os_version()}</b>", markup=True)
        self.upd_status = ui.label("Press “Check” to look for updates.", "dim", wrap=True)
        self.check_btn = ui.button("Check for updates", None, self.do_check)
        self.install_btn = ui.button("Download & install", "accent", self.do_install)
        self.install_btn.set_sensitive(False)
        row = Gtk.Box(spacing=10)
        row.pack_start(self.check_btn, False, False, 0)
        row.pack_start(self.install_btn, False, False, 0)
        card.pack_start(self.ver_lb, False, False, 0)
        card.pack_start(self.upd_status, False, False, 0)
        card.pack_start(row, False, False, 4)
        box.pack_start(card, False, False, 6)

        self.restart_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.restart_card.get_style_context().add_class("card")
        self.restart_card.pack_start(ui.label("A restart is recommended (optional)", "title-2"), False, False, 0)
        self.restart_card.pack_start(
            ui.label("Some system updates (like the kernel) apply after a restart. You can keep working — "
                     "nothing is closed. Save your work before restarting; open windows are restored after login.",
                     "dim", wrap=True), False, False, 0)
        rb = Gtk.Box(spacing=10)
        rb.pack_start(ui.button("Later", None, lambda *_: self.restart_card.hide()), False, False, 0)
        rb.pack_start(ui.button("Restart now", "danger", lambda *_: spawn(["xfce4-session-logout", "--reboot"])), False, False, 0)
        self.restart_card.pack_start(rb, False, False, 0)
        box.pack_start(self.restart_card, False, False, 0)
        self.restart_card.set_no_show_all(True)
        self.restart_card.hide()
        self.pending_version = None
        return box

    def do_check(self, _b):
        self.check_btn.set_sensitive(False)
        self.upd_status.set_text("Checking…")

        def work():
            r = ui.run_quiet(["python3", UPDATER, "check"], timeout=60)
            GLib.idle_add(self._after_check, r)
        threading.Thread(target=work, daemon=True).start()

    def _after_check(self, r):
        self.check_btn.set_sensitive(True)
        if not r:
            self.upd_status.set_text("Could not run the updater.")
            return False
        res = [ln for ln in r.stdout.splitlines() if ln.startswith("RESULT")]
        if res and res[-1].startswith("RESULT available"):
            self.pending_version = res[-1].split()[-1]
            kind = ""
            notes = ""
            for ln in r.stdout.splitlines():
                if "النوع:" in ln:
                    kind = ln.split(":", 1)[1].strip()
                if "ملاحظات:" in ln:
                    notes = ln.split(":", 1)[1].strip()
            self.upd_status.set_text(f"Update {self.pending_version} available" +
                                     (f"  ({kind})" if kind else "") + (f"\n{notes}" if notes else ""))
            self.install_btn.set_sensitive(True)
        elif res and res[-1].startswith("RESULT up-to-date"):
            self.upd_status.set_text("✓ You're up to date.")
        else:
            tail = (r.stdout + r.stderr).strip().splitlines()
            self.upd_status.set_text("Couldn't reach the update server. " + (tail[-1][:120] if tail else ""))
        return False

    def do_install(self, _b):
        ok, lines = ui.run_dialog(self, f"Installing update {self.pending_version or ''}",
                                  ["python3", UPDATER, "apply"],
                                  "Updated — no restart needed")
        if ok:
            self.ver_lb.set_markup(f"Installed version:  <b>{ui.os_version()}</b>")
            self.upd_status.set_text("✓ Update installed. You can keep working.")
            self.install_btn.set_sensitive(False)
            if self.update_dot:
                self.update_dot.hide()
            ui.run_quiet(["pkill", "-USR1", "-f", "neon-tray.py"], timeout=3)
            if os.path.exists("/var/run/reboot-required"):
                self.restart_card.show_all()
        else:
            self.upd_status.set_text("The update failed. Nothing was changed — try again later.")

    # ---- الإعدادات
    def build_settings(self):
        box = page_box("Performance & Settings", "Speed, animations and quick links to system tools.")
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        card.get_style_context().add_class("card")

        def toggle_row(title, desc, active, cb):
            r = Gtk.Box(spacing=12)
            v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            v.pack_start(ui.label(title), False, False, 0)
            v.pack_start(ui.label(desc, "dim"), False, False, 0)
            r.pack_start(v, True, True, 0)
            sw = Gtk.Switch()
            sw.set_active(active)
            sw.set_valign(Gtk.Align.CENTER)
            sw.connect("state-set", lambda _s, st: (cb(st), False)[1])
            r.pack_end(sw, False, False, 0)
            card.pack_start(r, False, False, 0)

        toggle_row("Window animations & shadows", "Smooth effects (turn off on very old PCs)", True,
                   lambda st: ui.xfconf_set("xfwm4", "/general/use_compositing", st, "bool"))
        toggle_row("Window buttons on the left", "Close / minimize / maximize on the left side", False,
                   lambda st: ui.xfconf_set("xfwm4", "/general/button_layout", "CHM|" if st else "|HMC", "string"))
        toggle_row("Restore windows after restart", "Re-open your apps next time you log in", True,
                   lambda st: ui.xfconf_set("xfce4-session", "/general/SaveOnExit", st, "bool"))
        box.pack_start(card, False, False, 6)
        box.pack_start(self.performance_card(), False, False, 6)

        box.pack_start(ui.label("System settings", "title-2"), False, False, 8)
        links = [
            ("📶 Network", ["nm-connection-editor"]),
            ("🖥 Display", ["xfce4-display-settings"]),
            ("🔊 Sound & Keyboard", ["xfce4-settings-manager"]),
            ("🔋 Power", ["xfce4-power-manager-settings"]),
            ("🌡 ThermalCtl", ["python3", "/opt/novaos/thermalctl/thermalctl_gui.py"]),
            ("🤖 AI Assistant", ["python3", "/opt/novaos/ai-assistant/ai_assistant.py"]),
        ]
        fb = Gtk.FlowBox()
        fb.set_selection_mode(Gtk.SelectionMode.NONE)
        fb.set_column_spacing(12)
        fb.set_row_spacing(12)
        for name, cmd in links:
            fb.add(ui.button(name, None, lambda _b, c=cmd: spawn(c)))
        box.pack_start(fb, False, False, 0)
        return box

    # ---- حول
    def build_about(self):
        box = page_box("About NeonOS")
        try:
            pb = GdkPixbuf.Pixbuf.new_from_file_at_size(ui.LOGO, 140, 140)
            img = Gtk.Image.new_from_pixbuf(pb)
            img.get_style_context().add_class("logo-glow")
            img.set_halign(Gtk.Align.START)
            box.pack_start(img, False, False, 8)
        except GLib.Error:
            pass
        box.pack_start(ui.label(f"NeonOS {ui.os_version()}", "title-2 neon-text"), False, False, 0)
        try:
            import psutil
            ram = f"{psutil.virtual_memory().total / 2**30:.1f} GB"
            cores = str(psutil.cpu_count(logical=True))
        except ImportError:
            ram, cores = "?", "?"
        cpu = "Unknown CPU"
        try:
            with open("/proc/cpuinfo") as f:
                for ln in f:
                    if ln.startswith("model name"):
                        cpu = ln.split(":", 1)[1].strip()
                        break
        except OSError:
            pass
        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        info.get_style_context().add_class("card")
        for k, v in [("Processor", cpu), ("Threads", cores), ("Memory", ram),
                     ("Kernel", platform.release()), ("Base", "Debian 12 (Bookworm)")]:
            info.pack_start(ui.label(f"<b>{k}</b>   {v}", markup=True), False, False, 0)
        box.pack_start(info, False, False, 8)
        return box


def main():
    page = "home"
    if "--page" in sys.argv:
        i = sys.argv.index("--page")
        if i + 1 < len(sys.argv):
            page = sys.argv[i + 1]
    ui.apply_css()
    win = NeonCenter(page)
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
