#!/usr/bin/env python3
"""neon-tray: أيقونة صفراء بجانب الساعة تظهر فقط عند وجود تحديث. نقرة واحدة تفتح صفحة التحديثات."""
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

import os
import signal
import subprocess
import threading

ICON = "/usr/share/novaos/neon-update.png"
UPDATER = "/opt/novaos/updater/updater.py"
CENTER = "/opt/novaos/neon/neon_center.py"


class Tray:
    def __init__(self):
        self.icon = Gtk.StatusIcon.new_from_file(ICON) if os.path.exists(ICON) else Gtk.StatusIcon()
        self.icon.set_visible(False)
        self.icon.set_title("NeonOS Update")
        self.icon.connect("activate", self.open_updates)
        self.icon.connect("popup-menu", self.open_updates_menu)
        self.notified = None
        GLib.timeout_add_seconds(25, self.check_once)
        GLib.timeout_add_seconds(1800, lambda: (self.check(), True)[1])
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR1, self.on_usr1)

    def check_once(self):
        self.check()
        return False

    def on_usr1(self):
        self.check()
        return True

    def check(self):
        threading.Thread(target=self._work, daemon=True).start()

    def _work(self):
        try:
            r = subprocess.run(["python3", UPDATER, "check"], capture_output=True, text=True, timeout=60)
            ver = ""
            for ln in r.stdout.splitlines():
                if ln.startswith("RESULT available"):
                    ver = ln.split()[-1]
        except Exception:
            ver = ""
        GLib.idle_add(self._apply, ver)

    def _apply(self, ver):
        if ver:
            self.icon.set_tooltip_text(f"NeonOS {ver} is available — click to install (no restart needed)")
            self.icon.set_visible(True)
            if self.notified != ver:
                self.notified = ver
                subprocess.Popen(["notify-send", "-i", ICON, "NeonOS update available",
                                  f"Version {ver} is ready. Click the yellow icon to install."])
        else:
            self.icon.set_visible(False)
        return False

    def open_updates(self, *_):
        subprocess.Popen(["python3", CENTER, "--page", "updates"], start_new_session=True)

    def open_updates_menu(self, *_):
        self.open_updates()


if __name__ == "__main__":
    Tray()
    Gtk.main()
