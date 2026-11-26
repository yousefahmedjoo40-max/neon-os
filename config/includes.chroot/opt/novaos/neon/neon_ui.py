"""
neon_ui.py - الوحدة المشتركة لهوية NeonOS: ستايل النيون، الحركات، ونافذة تنفيذ الأوامر مع شريط تقدّم.
"""
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib

import os
import re
import subprocess
import threading

LOGO = "/usr/share/novaos/neon-logo-256.png"
WALL_DIR = "/usr/share/backgrounds/novaos"
OS_NAME = "NeonOS"
OS_VERSION_FILE = "/etc/novaos/version"

CSS = b"""
@keyframes neon-pulse {
  from { box-shadow: 0 0 6px rgba(0,229,255,0.25); }
  to   { box-shadow: 0 0 26px rgba(176,92,255,0.75); }
}

window.neon, dialog.neon { background-image: linear-gradient(160deg, #09051d 0%, #120a32 55%, #0a1a3a 100%); color: #e9ecff; }
.neon label { color: #e9ecff; }
.neon .dim { opacity: 0.62; }
.neon .title-1 { font-size: 30px; font-weight: 800; letter-spacing: 1px; }
.neon .title-2 { font-size: 19px; font-weight: 700; }
.neon .neon-text { color: #00e5ff; text-shadow: 0 0 14px rgba(0,229,255,0.85); }

.neon .sidebar { background-color: rgba(255,255,255,0.035); border-right: 1px solid rgba(0,229,255,0.12); }
.neon .sidebar row { padding: 11px 18px; margin: 3px 10px; border-radius: 12px; transition: all 220ms ease; }
.neon .sidebar row:hover { background-color: rgba(0,229,255,0.10); }
.neon .sidebar row:selected { background-image: linear-gradient(90deg, rgba(0,229,255,0.28), rgba(176,92,255,0.22)); box-shadow: inset 3px 0 0 #00e5ff; }
.neon .sidebar row label { font-weight: 600; }

.neon button { border-radius: 14px; border: 1px solid rgba(0,229,255,0.18); background-image: none; background-color: rgba(255,255,255,0.06); color: #e9ecff; padding: 8px 16px; box-shadow: none; text-shadow: none; transition: all 220ms ease; }
.neon button:hover { background-color: rgba(0,229,255,0.12); border-color: #00e5ff; box-shadow: 0 0 22px rgba(0,229,255,0.45); }
.neon button:active { background-color: rgba(176,92,255,0.25); }
.neon button:disabled { opacity: 0.4; }
.neon button.tile { padding: 22px 16px; min-width: 150px; border-radius: 20px; }
.neon button.accent { background-image: linear-gradient(120deg, #00e5ff, #8c46ff); color: #07021a; font-weight: 800; border: none; }
.neon button.accent:hover { box-shadow: 0 0 28px rgba(0,229,255,0.8); }
.neon button.danger { background-image: linear-gradient(120deg, #ff3d71, #ff8a3d); color: #1a0208; font-weight: 800; border: none; }
.neon button.cell { font-size: 44px; font-weight: 800; min-width: 96px; min-height: 96px; border-radius: 18px; }

.neon .card { background-color: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08); border-radius: 18px; padding: 16px; }
.neon .banner { background-image: linear-gradient(120deg, rgba(0,229,255,0.22), rgba(176,92,255,0.25)); border: 1px solid rgba(0,229,255,0.5); border-radius: 16px; padding: 12px 18px; animation: neon-pulse 1.8s ease-in-out infinite alternate; }
.neon .logo-glow { animation: neon-pulse 2.2s ease-in-out infinite alternate; border-radius: 60px; }

.neon progressbar trough { background-color: rgba(255,255,255,0.08); border-radius: 10px; min-height: 12px; border: none; }
.neon progressbar progress { background-image: linear-gradient(90deg, #00e5ff, #b05cff, #ff3cc8); border-radius: 10px; min-height: 12px; border: none; box-shadow: 0 0 14px rgba(0,229,255,0.7); }

.neon entry { background-color: rgba(255,255,255,0.07); border: 1px solid rgba(0,229,255,0.2); border-radius: 12px; color: #fff; padding: 7px 12px; transition: all 200ms ease; }
.neon entry:focus { border-color: #00e5ff; box-shadow: 0 0 16px rgba(0,229,255,0.45); }
.neon treeview { background-color: transparent; color: #e9ecff; }
.neon treeview.view:selected { background-color: rgba(0,229,255,0.28); color: #fff; }
.neon treeview header button { background-color: rgba(255,255,255,0.05); border-radius: 0; border: none; border-bottom: 1px solid rgba(0,229,255,0.2); box-shadow: none; font-weight: 700; padding: 8px 10px; }
.neon scrolledwindow, .neon viewport, .neon stack { background-color: transparent; }
.neon notebook > header { background-color: rgba(255,255,255,0.03); border: none; }
.neon notebook > header > tabs > tab { padding: 10px 22px; border-radius: 12px 12px 0 0; transition: all 200ms ease; }
.neon notebook > header > tabs > tab:checked { background-image: linear-gradient(180deg, rgba(0,229,255,0.22), transparent); box-shadow: inset 0 2px 0 #00e5ff; }
.neon switch { background-color: rgba(255,255,255,0.12); border-radius: 14px; border: none; transition: all 200ms ease; }
.neon switch:checked { background-image: linear-gradient(120deg, #00e5ff, #8c46ff); }
.neon switch slider { border-radius: 14px; background-color: #fff; }
.neon flowboxchild { border-radius: 16px; transition: all 200ms ease; }
.neon flowboxchild:selected, .neon flowboxchild:hover { background-color: rgba(0,229,255,0.12); box-shadow: 0 0 18px rgba(0,229,255,0.4); }
.neon combobox button, .neon combobox box button { padding: 6px 12px; }
.neon textview, .neon textview text { background-color: rgba(255,255,255,0.045); color: #e9ecff; }
.neon spinbutton { background-color: rgba(255,255,255,0.07); border-radius: 12px; color: #fff; }
.neon messagedialog { background-image: linear-gradient(160deg, #09051d, #120a32); }
"""


LITE_FILE = os.path.expanduser("~/.config/neonos/lite")
LITE_CSS = b"* { transition: none; animation: none; box-shadow: none; text-shadow: none; }"
DOT_CSS = b".neon .dot-yellow { color: #ffd23d; text-shadow: 0 0 10px rgba(255,210,61,0.9); font-size: 18px; }"


def is_lite():
    return os.path.exists(LITE_FILE)


def fit_size(w, h):
    """يصغّر النافذة تلقائياً لتناسب الشاشات الصغيرة."""
    try:
        mon = Gdk.Display.get_default().get_primary_monitor() or Gdk.Display.get_default().get_monitor(0)
        g = mon.get_geometry()
        return min(w, int(g.width * 0.94)), min(h, int(g.height * 0.88))
    except Exception:
        return w, h


def spawn(cmd):
    try:
        subprocess.Popen(cmd, shell=isinstance(cmd, str), start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as e:
        print("spawn failed:", e)


def flatpak_installed(app_id):
    import shutil
    if not shutil.which("flatpak"):
        return False
    r = run_quiet(["flatpak", "info", app_id], timeout=10)
    return bool(r and r.returncode == 0)


def apply_css():
    provider = Gtk.CssProvider()
    try:
        provider.load_from_data(CSS + DOT_CSS + (LITE_CSS if is_lite() else b""))
    except GLib.Error as e:
        print("CSS error:", e.message)
        return
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )


def make_window(title, w, h):
    win = Gtk.Window(title=title)
    win.set_default_size(w, h)
    win.get_style_context().add_class("neon")
    if os.path.exists(LOGO):
        try:
            win.set_icon_from_file(LOGO)
        except GLib.Error:
            pass
    return win


def label(text, css=None, xalign=0.0, markup=False, wrap=False):
    lb = Gtk.Label()
    if markup:
        lb.set_markup(text)
    else:
        lb.set_text(text)
    lb.set_xalign(xalign)
    lb.set_line_wrap(wrap)
    if css:
        for c in css.split():
            lb.get_style_context().add_class(c)
    return lb


def button(text, css=None, cb=None):
    b = Gtk.Button(label=text)
    if css:
        for c in css.split():
            b.get_style_context().add_class(c)
    if cb:
        b.connect("clicked", cb)
    return b


def os_version():
    try:
        with open(OS_VERSION_FILE) as f:
            return f.read().strip()
    except OSError:
        return "1.0.0"


def run_quiet(argv, timeout=20):
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None


def xfconf_set(channel, prop, value, vtype):
    """يضبط خاصية xfconf وينشئها إن لم تكن موجودة."""
    v = str(value).lower() if vtype == "bool" else str(value)
    r = run_quiet(["xfconf-query", "-c", channel, "-p", prop, "-s", v])
    if r is None or r.returncode != 0:
        run_quiet(["xfconf-query", "-c", channel, "-p", prop, "-n", "-t", vtype, "-s", v])


def set_wallpaper(path):
    r = run_quiet(["xfconf-query", "-c", "xfce4-desktop", "-l"])
    props = r.stdout.split() if r and r.returncode == 0 else []
    targets = [p for p in props if p.endswith("/last-image")]
    if not targets:
        targets = [
            f"/backdrop/screen0/monitor{m}/workspace0/last-image"
            for m in ("0", "Virtual-1", "eDP-1", "HDMI-1", "VGA-1", "DP-1")
        ]
    for p in targets:
        xfconf_set("xfce4-desktop", p, path, "string")
        xfconf_set("xfce4-desktop", p.replace("last-image", "image-style"), 5, "int")


def dconf_write(key, value):
    run_quiet(["dconf", "write", key, value])


class CommandDialog(Gtk.Dialog):
    """ينفّذ أمراً في الخلفية ويعرض شريط تقدّم حيّ بدون فتح أي طرفية."""

    def __init__(self, parent, title, argv, done_text="Done", on_done=None):
        super().__init__(title=title, transient_for=parent, modal=True)
        self.get_style_context().add_class("neon")
        self.set_default_size(520, 220)
        self.set_deletable(False)
        self._on_done = on_done
        self._done_text = done_text
        self._lines = []
        self._ok = False

        box = self.get_content_area()
        box.set_spacing(14)
        box.set_border_width(24)
        self.title_lb = label(title, "title-2")
        self.status_lb = label("Starting…", "dim", wrap=True)
        self.bar = Gtk.ProgressBar()
        self.bar.set_pulse_step(0.08)
        box.pack_start(self.title_lb, False, False, 0)
        box.pack_start(self.bar, False, False, 6)
        box.pack_start(self.status_lb, False, False, 0)
        self.close_btn = self.add_button("Close", Gtk.ResponseType.CLOSE)
        self.close_btn.get_style_context().add_class("accent")
        self.close_btn.set_sensitive(False)
        self.show_all()

        self._pulse_id = GLib.timeout_add(90, self._pulse)
        self._determinate = False
        threading.Thread(target=self._run, args=(argv,), daemon=True).start()

    def _pulse(self):
        if not self._determinate:
            self.bar.pulse()
        return True

    def _run(self, argv):
        env = dict(os.environ, TERM="dumb", LANG="C.UTF-8")
        try:
            proc = subprocess.Popen(
                argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, env=env,
            )
        except OSError as e:
            GLib.idle_add(self._finish, False, f"Could not start: {e}")
            return
        for raw in proc.stdout:
            line = raw.strip()
            if not line:
                continue
            self._lines.append(line)
            m = re.match(r"PROGRESS\s+(\d+)", line) or re.search(r"(\d{1,3})\s*%", line)
            frac = min(100, int(m.group(1))) / 100 if m else None
            GLib.idle_add(self._update, line, frac)
        proc.wait()
        GLib.idle_add(self._finish, proc.returncode == 0, "")

    def _update(self, line, frac):
        if frac is not None:
            self._determinate = True
            self.bar.set_fraction(frac)
        if not line.startswith("PROGRESS") and not line.startswith("RESULT"):
            self.status_lb.set_text(line[:110])
        return False

    def _finish(self, ok, err):
        self._ok = ok
        GLib.source_remove(self._pulse_id)
        self._determinate = True
        self.bar.set_fraction(1.0 if ok else 0.0)
        if ok:
            self.status_lb.set_text("✓ " + self._done_text)
        else:
            tail = err or (self._lines[-1] if self._lines else "Unknown error")
            self.status_lb.set_text("✗ Failed: " + tail[:140])
        self.close_btn.set_sensitive(True)
        self.set_deletable(True)
        return False

    @property
    def lines(self):
        return list(self._lines)

    @property
    def ok(self):
        return self._ok


def run_dialog(parent, title, argv, done_text="Done"):
    dlg = CommandDialog(parent, title, argv, done_text)
    dlg.run()
    ok, lines = dlg.ok, dlg.lines
    dlg.destroy()
    return ok, lines
