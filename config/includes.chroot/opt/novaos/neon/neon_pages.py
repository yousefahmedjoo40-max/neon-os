"""neon_pages.py - صفحات الإعدادات الإضافية: الشبكة، الدرايفرات، شريط المهام، اللغة، الأداء."""
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

import os
import re
import shutil
import subprocess
import threading

import neon_ui as ui

DRIVER_HELPER = "/opt/novaos/neon/neon-install-driver.sh"
APPLY_DEFAULTS = "/opt/novaos/neon/apply-defaults.sh"

TASKBAR_POS = {
    "Bottom": ("p=10;x=0;y=0", 0),
    "Top": ("p=6;x=0;y=0", 0),
    "Left": ("p=5;x=0;y=0", 1),
    "Right": ("p=4;x=0;y=0", 1),
}
LANGS = [
    ("العربية", "ar_EG.UTF-8", "ar"), ("English", "en_US.UTF-8", "en"), ("Español", "es_ES.UTF-8", "es"),
    ("Français", "fr_FR.UTF-8", "fr"), ("Deutsch", "de_DE.UTF-8", "de"), ("Русский", "ru_RU.UTF-8", "ru"),
    ("Türkçe", "tr_TR.UTF-8", "tr"), ("Português", "pt_BR.UTF-8", "pt"), ("中文", "zh_CN.UTF-8", "zh"),
    ("हिन्दी", "hi_IN.UTF-8", "hi"), ("Bahasa Indonesia", "id_ID.UTF-8", "id"), ("日本語", "ja_JP.UTF-8", "ja"),
]
KEYBOARDS = [("English (US)", "us"), ("Arabic", "ara"), ("French", "fr"), ("German", "de"),
             ("Spanish", "es"), ("Russian", "ru"), ("Turkish", "tr")]


def page_box(title, subtitle=""):
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
    box.set_border_width(28)
    box.pack_start(ui.label(title, "title-1"), False, False, 0)
    if subtitle:
        box.pack_start(ui.label(subtitle, "dim", wrap=True), False, False, 0)
    return box


def card():
    c = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    c.get_style_context().add_class("card")
    return c


def switch_row(parent, title, desc, active, cb):
    r = Gtk.Box(spacing=12)
    v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    v.pack_start(ui.label(title), False, False, 0)
    v.pack_start(ui.label(desc, "dim", wrap=True), False, False, 0)
    r.pack_start(v, True, True, 0)
    sw = Gtk.Switch()
    sw.set_active(active)
    sw.set_valign(Gtk.Align.CENTER)
    sw.connect("state-set", lambda _s, st: (cb(st), False)[1])
    r.pack_end(sw, False, False, 0)
    parent.pack_start(r, False, False, 0)


def parse_nmcli_wifi(text):
    """يحلّل ناتج: nmcli -t -f IN-USE,SSID,SIGNAL,SECURITY dev wifi list"""
    nets, seen = [], set()
    for line in text.splitlines():
        parts = [p.replace("\\:", ":") for p in re.split(r"(?<!\\):", line)]
        if len(parts) < 4 or not parts[1]:
            continue
        in_use, ssid, sig, sec = parts[0] == "*", parts[1], int(parts[2] or 0), parts[3]
        if ssid in seen:
            continue
        seen.add(ssid)
        nets.append({"in_use": in_use, "ssid": ssid, "signal": sig, "secure": bool(sec and sec != "--")})
    return sorted(nets, key=lambda n: (not n["in_use"], -n["signal"]))


def parse_lspci(text):
    gpus = []
    for line in text.splitlines():
        if re.search(r"VGA compatible|3D controller|Display controller", line, re.I):
            name = line.split(": ", 1)[-1]
            low = line.lower()
            vendor = "nvidia" if "nvidia" in low else "amd" if ("amd" in low or "ati " in low or "radeon" in low) \
                else "intel" if "intel" in low else "other"
            gpus.append({"name": name.strip(), "vendor": vendor})
    return gpus


class ExtraPages:
    # ------------------------------------------------------------ الشبكة
    def build_network(self):
        box = page_box("Network", "Connect to Wi-Fi or cable. In a virtual machine the internet is shared automatically.")
        self.net_status = ui.label("Checking…", "dim")
        c = card()
        c.pack_start(ui.label("Connection", "title-2"), False, False, 0)
        c.pack_start(self.net_status, False, False, 0)
        row = Gtk.Box(spacing=10)
        row.pack_start(ui.button("Test internet", "accent", self.test_internet), False, False, 0)
        row.pack_start(ui.button("Refresh", None, lambda *_: self.refresh_net()), False, False, 0)
        row.pack_start(ui.button("Advanced…", None, lambda *_: ui.spawn(["nm-connection-editor"])), False, False, 0)
        c.pack_start(row, False, False, 0)
        box.pack_start(c, False, False, 0)
        box.pack_start(ui.label("Wi-Fi networks", "title-2"), False, False, 8)
        self.wifi_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.pack_start(self.wifi_box, False, False, 0)
        GLib.idle_add(self.refresh_net)
        return box

    def refresh_net(self):
        threading.Thread(target=self._net_work, daemon=True).start()
        return False

    def _net_work(self):
        if not shutil.which("nmcli"):
            GLib.idle_add(self._net_show, "NetworkManager is not available here.", [])
            return
        st = ui.run_quiet(["nmcli", "-t", "-f", "TYPE,STATE,CONNECTION", "dev"], timeout=10)
        status = "Not connected"
        has_wifi = False
        if st:
            for ln in st.stdout.splitlines():
                t, s, conn = (ln.split(":") + ["", "", ""])[:3]
                if t == "wifi":
                    has_wifi = True
                if s == "connected" and t in ("wifi", "ethernet"):
                    status = f"✓ Connected via {'Wi-Fi' if t == 'wifi' else 'cable'}" + (f"  ({conn})" if conn else "")
        nets = []
        if has_wifi:
            r = ui.run_quiet(["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "dev", "wifi", "list", "--rescan", "yes"], timeout=25)
            nets = parse_nmcli_wifi(r.stdout) if r else []
        elif status == "Not connected":
            status = "No Wi-Fi adapter found. Plug in a cable, or use USB tethering from your phone."
        GLib.idle_add(self._net_show, status, nets, has_wifi)

    def _net_show(self, status, nets, has_wifi=True):
        self.net_status.set_text(status)
        for ch in self.wifi_box.get_children():
            self.wifi_box.remove(ch)
        if not nets:
            self.wifi_box.pack_start(ui.label("No Wi-Fi networks found." if has_wifi else "", "dim"), False, False, 0)
        for n in nets[:14]:
            row = Gtk.Box(spacing=12)
            row.get_style_context().add_class("card")
            bars = "▂▄▆█" [: max(1, min(4, n["signal"] // 25 + 1))]
            row.pack_start(ui.label(f"{bars}", "neon-text"), False, False, 0)
            row.pack_start(ui.label(("🔒 " if n["secure"] else "") + n["ssid"]), True, True, 0)
            if n["in_use"]:
                row.pack_end(ui.label("Connected ✓", "neon-text"), False, False, 0)
            else:
                row.pack_end(ui.button("Connect", "accent", lambda _b, x=n: self.connect_wifi(x)), False, False, 0)
            self.wifi_box.pack_start(row, False, False, 0)
        self.wifi_box.show_all()
        return False

    def connect_wifi(self, net):
        cmd = ["nmcli", "dev", "wifi", "connect", net["ssid"]]
        if net["secure"]:
            dlg = Gtk.Dialog(title=f"Connect to {net['ssid']}", transient_for=self, modal=True)
            dlg.get_style_context().add_class("neon")
            dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "Connect", Gtk.ResponseType.OK)
            area = dlg.get_content_area()
            area.set_spacing(10)
            area.set_border_width(20)
            area.pack_start(ui.label("Wi-Fi password"), False, False, 0)
            entry = Gtk.Entry()
            entry.set_visibility(False)
            entry.set_activates_default(True)
            area.pack_start(entry, False, False, 0)
            dlg.set_default_response(Gtk.ResponseType.OK)
            dlg.show_all()
            resp = dlg.run()
            pw = entry.get_text()
            dlg.destroy()
            if resp != Gtk.ResponseType.OK or not pw:
                return
            cmd += ["password", pw]
        ok, lines = ui.run_dialog(self, f"Connecting to {net['ssid']}", cmd, "Connected")
        self.refresh_net()

    def test_internet(self, _b):
        import socket

        def work():
            try:
                socket.create_connection(("1.1.1.1", 53), timeout=4).close()
                msg = "✓ Internet works"
            except OSError:
                msg = "✗ No internet. Check Wi-Fi/cable."
            GLib.idle_add(self.net_status.set_text, msg)
        threading.Thread(target=work, daemon=True).start()

    # ------------------------------------------------------------ الدرايفرات
    def build_drivers(self):
        box = page_box("Drivers", "NeonOS detects your processor and graphics card. Intel and AMD work out of the box.")
        text = ""
        if os.environ.get("NEON_FAKE_LSPCI"):
            text = open(os.environ["NEON_FAKE_LSPCI"]).read()
        elif shutil.which("lspci"):
            r = ui.run_quiet(["lspci", "-nn"], timeout=10)
            text = r.stdout if r else ""
        gpus = parse_lspci(text)

        cpu_name, cpu_vendor = "Unknown processor", ""
        try:
            for ln in open("/proc/cpuinfo"):
                if ln.startswith("model name") and cpu_name == "Unknown processor":
                    cpu_name = ln.split(":", 1)[1].strip()
                if ln.startswith("vendor_id") and not cpu_vendor:
                    cpu_vendor = ln.split(":", 1)[1].strip()
        except OSError:
            pass
        c = card()
        c.pack_start(ui.label("Processor", "title-2"), False, False, 0)
        c.pack_start(ui.label(cpu_name), False, False, 0)
        mc = "intel-microcode" if "Intel" in cpu_vendor else "amd64-microcode" if "AMD" in cpu_vendor else ""
        if mc:
            ok = ui.run_quiet(["dpkg", "-s", mc], timeout=8)
            have = bool(ok and ok.returncode == 0)
            c.pack_start(ui.label(("✓ " if have else "• ") + f"CPU security microcode ({mc}) " +
                                  ("installed" if have else "comes with system updates"), "dim"), False, False, 0)
        c.pack_start(ui.label("Ryzen / Intel Core: no extra drivers needed.", "dim"), False, False, 0)
        box.pack_start(c, False, False, 0)

        loaded = ""
        try:
            loaded = open("/proc/modules").read()
        except OSError:
            pass
        live = False
        try:
            live = "boot=live" in open("/proc/cmdline").read()
        except OSError:
            pass
        if not gpus:
            gpus = [{"name": "No graphics card detected (virtual machine?)", "vendor": "other"}]
        for g in gpus:
            c = card()
            c.pack_start(ui.label("Graphics card", "title-2"), False, False, 0)
            c.pack_start(ui.label(g["name"], wrap=True), False, False, 0)
            if g["vendor"] in ("intel", "amd"):
                c.pack_start(ui.label("✓ Works out of the box (open-source Mesa driver + firmware + Vulkan).", "neon-text"),
                             False, False, 0)
            elif g["vendor"] == "nvidia":
                if re.search(r"^nvidia ", loaded, re.M):
                    c.pack_start(ui.label("✓ Official NVIDIA driver is active.", "neon-text"), False, False, 0)
                else:
                    c.pack_start(ui.label("Using the basic open driver. Install the official NVIDIA driver for full "
                                          "speed in games and 3D. NeonOS picks the right version for your card.",
                                          "dim", wrap=True), False, False, 0)
                    if live:
                        c.pack_start(ui.label("Tip: install NeonOS to your disk first, then install the driver.", "dim"), False, False, 0)
                    c.pack_start(ui.button("Install NVIDIA driver", "accent", self.install_driver), False, False, 0)
            else:
                c.pack_start(ui.label("Standard driver in use.", "dim"), False, False, 0)
            box.pack_start(c, False, False, 0)
        if len([g for g in gpus if g["vendor"] != "other"]) > 1:
            box.pack_start(ui.label("Laptop with two graphics cards: apps use the integrated one by default (saves battery); "
                                    "heavy games switch to the stronger card.", "dim", wrap=True), False, False, 4)
        box.pack_start(ui.label("NVIDIA's driver needs a restart (optional — nothing closes by itself). "
                                "On computers with Secure Boot you may be asked to set a one-time password.",
                                "dim", wrap=True), False, False, 4)
        return box

    def install_driver(self, _b):
        ok, lines = ui.run_dialog(self, "Installing NVIDIA driver", ["sudo", "-n", DRIVER_HELPER],
                                  "Installed — restart when you like")

    # ------------------------------------------------------------ شريط المهام
    def taskbar_card(self):
        c = card()
        c.pack_start(ui.label("Taskbar", "title-2"), False, False, 0)
        row = Gtk.Box(spacing=8)
        row.pack_start(ui.label("Position:"), False, False, 6)
        group = None
        for name in ("Bottom", "Top", "Left", "Right"):
            rb = Gtk.RadioButton.new_with_label_from_widget(group, name)
            group = group or rb
            rb.get_style_context().add_class("neon")
            rb.connect("toggled", lambda b, n=name: b.get_active() and self.set_taskbar(n))
            row.pack_start(rb, False, False, 6)
        c.pack_start(row, False, False, 0)
        srow = Gtk.Box(spacing=10)
        srow.pack_start(ui.label("Size:"), False, False, 6)
        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 32, 80, 2)
        scale.set_value(46)
        scale.set_size_request(220, -1)
        scale.set_draw_value(True)
        self._size_timer = None

        def on_size(s):
            if self._size_timer:
                GLib.source_remove(self._size_timer)
            self._size_timer = GLib.timeout_add(350, lambda: (ui.xfconf_set("xfce4-panel", "/panels/panel-1/size", int(s.get_value()), "uint"), False)[1])
        scale.connect("value-changed", on_size)
        srow.pack_start(scale, False, False, 0)
        c.pack_start(srow, False, False, 0)
        switch_row(c, "Auto-hide taskbar", "Slides away until you move the mouse to the edge", False,
                   lambda st: ui.xfconf_set("xfce4-panel", "/panels/panel-1/autohide-behavior", 2 if st else 0, "uint"))
        switch_row(c, "Show window titles", "Show names next to the app icons (like Windows)", True,
                   lambda st: ui.xfconf_set("xfce4-panel", "/plugins/plugin-4/show-labels", st, "bool"))
        return c

    def set_taskbar(self, name):
        pos, mode = TASKBAR_POS[name]
        ui.xfconf_set("xfce4-panel", "/panels/panel-1/mode", mode, "uint")
        ui.xfconf_set("xfce4-panel", "/panels/panel-1/position", pos, "string")

    # ------------------------------------------------------------ اللغة
    def build_language(self):
        box = page_box("Language & Keyboard", "Choose your language. Applies the next time you sign in — nothing closes now.")
        c = card()
        c.pack_start(ui.label("System language", "title-2"), False, False, 0)
        combo = Gtk.ComboBoxText()
        cur = os.environ.get("LANG", "en_US.UTF-8")
        active = 1
        for i, (name, loc, _c) in enumerate(LANGS):
            combo.append_text(name)
            if cur.startswith(loc.split("_")[0]):
                active = i
        combo.set_active(active)
        self.lang_msg = ui.label("", "neon-text")

        def on_lang(cb):
            name, loc, code = LANGS[cb.get_active()]
            try:
                with open(os.path.expanduser("~/.xsessionrc"), "w") as f:
                    f.write(f"export LANG={loc}\nexport LANGUAGE={code}\nexport LC_ALL={loc}\n")
                self.lang_msg.set_text(f"✓ {name} will be used after your next sign-in.")
            except OSError as e:
                self.lang_msg.set_text(f"Could not save: {e}")
        combo.connect("changed", on_lang)
        c.pack_start(combo, False, False, 0)
        c.pack_start(self.lang_msg, False, False, 0)
        box.pack_start(c, False, False, 0)

        k = card()
        k.pack_start(ui.label("Keyboard layouts", "title-2"), False, False, 0)
        k.pack_start(ui.label("Pick the layouts you use. Switch between them with Alt + Shift.", "dim", wrap=True), False, False, 0)
        self.kb_checks = []
        for name, code in KEYBOARDS:
            cb = Gtk.CheckButton(label=name)
            cb.set_active(code == "us")
            cb.connect("toggled", lambda *_: self.apply_keyboards())
            k.pack_start(cb, False, False, 0)
            self.kb_checks.append((cb, code))
        box.pack_start(k, False, False, 0)
        return box

    def apply_keyboards(self):
        codes = [c for cb, c in self.kb_checks if cb.get_active()] or ["us"]
        layout = ",".join(codes)
        ui.xfconf_set("keyboard-layout", "/Default/XkbDisable", False, "bool")
        ui.xfconf_set("keyboard-layout", "/Default/XkbLayout", layout, "string")
        ui.xfconf_set("keyboard-layout", "/Default/XkbOptions/Group", "grp:alt_shift_toggle", "string")
        ui.run_quiet(["setxkbmap", "-layout", layout, "-option", "grp:alt_shift_toggle"], timeout=5)

    # ------------------------------------------------------------ الأداء
    def performance_card(self):
        c = card()
        c.pack_start(ui.label("Performance", "title-2"), False, False, 0)

        def lite(st):
            os.makedirs(os.path.dirname(ui.LITE_FILE), exist_ok=True)
            if st:
                open(ui.LITE_FILE, "w").close()
            elif os.path.exists(ui.LITE_FILE):
                os.remove(ui.LITE_FILE)
            ui.xfconf_set("xfwm4", "/general/use_compositing", not st, "bool")
        switch_row(c, "Lite mode (older PCs, 1 GB RAM)", "Turns off animations and shadows to run faster on weak computers",
                   ui.is_lite(), lite)
        c.pack_start(ui.label("Tip: NeonOS turns Lite mode on by itself when it finds less than 2 GB of RAM.", "dim", wrap=True),
                     False, False, 0)
        c.pack_start(ui.button("Repair desktop settings", None, self.repair), False, False, 0)
        return c

    def repair(self, _b):
        ui.run_dialog(self, "Repairing desktop settings", ["bash", APPLY_DEFAULTS, "--force"],
                      "Done — your old settings were backed up")
