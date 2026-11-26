#!/usr/bin/env python3
"""
Neon Task Manager - مدير مهام NeonOS
العمليات (بحث/ترتيب/إنهاء) + الأداء (مخططات حيّة للمعالج والذاكرة والقرص والشبكة).
"""
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, GLib

import collections
import os
import signal
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import neon_ui as ui

try:
    import psutil
except ImportError:
    psutil = None

HISTORY = 60


class Chart(Gtk.DrawingArea):
    """مخطط خطي حي بتوهّج نيون."""

    def __init__(self, title, color, unit="%", fixed_max=100.0):
        super().__init__()
        self.title, self.color, self.unit, self.fixed_max = title, color, unit, fixed_max
        self.values = collections.deque([0.0] * HISTORY, maxlen=HISTORY)
        self.caption = ""
        self.set_size_request(260, 150)
        self.connect("draw", self.on_draw)

    def push(self, v, caption=""):
        self.values.append(float(v))
        self.caption = caption
        self.queue_draw()

    @staticmethod
    def _round(cr, x, y, w, h, r):
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -1.5708, 0)
        cr.arc(x + w - r, y + h - r, r, 0, 1.5708)
        cr.arc(x + r, y + h - r, r, 1.5708, 3.14159)
        cr.arc(x + r, y + r, r, 3.14159, 4.71239)
        cr.close_path()

    def on_draw(self, widget, cr):
        w, h = widget.get_allocated_width(), widget.get_allocated_height()
        r, g, b = self.color
        self._round(cr, 0, 0, w, h, 16)
        cr.set_source_rgba(1, 1, 1, 0.05)
        cr.fill_preserve()
        cr.set_source_rgba(r, g, b, 0.25)
        cr.set_line_width(1)
        cr.stroke()

        pad_t, pad_b = 34, 10
        gw, gh = w - 20, h - pad_t - pad_b
        cr.set_source_rgba(1, 1, 1, 0.07)
        for i in range(1, 4):
            y = pad_t + gh * i / 4
            cr.move_to(10, y)
            cr.line_to(10 + gw, y)
        cr.stroke()

        vmax = self.fixed_max or max(max(self.values), 1.0) * 1.25
        pts = []
        n = len(self.values)
        for i, v in enumerate(self.values):
            x = 10 + gw * i / (n - 1)
            y = pad_t + gh - gh * min(v / vmax, 1.0)
            pts.append((x, y))

        # تعبئة متدرجة تحت الخط
        import cairo
        grad = cairo.LinearGradient(0, pad_t, 0, pad_t + gh)
        grad.add_color_stop_rgba(0, r, g, b, 0.40)
        grad.add_color_stop_rgba(1, r, g, b, 0.0)
        cr.move_to(pts[0][0], pad_t + gh)
        for x, y in pts:
            cr.line_to(x, y)
        cr.line_to(pts[-1][0], pad_t + gh)
        cr.close_path()
        cr.set_source(grad)
        cr.fill()
        # توهّج ثم الخط
        for width, alpha in ((7, 0.10), (4, 0.22), (2, 1.0)):
            cr.set_line_width(width)
            cr.set_source_rgba(r, g, b, alpha)
            cr.move_to(*pts[0])
            for x, y in pts[1:]:
                cr.line_to(x, y)
            cr.stroke()

        cr.set_source_rgba(0.91, 0.93, 1, 0.9)
        cr.select_font_face("Sans", 0, 1)
        cr.set_font_size(13)
        cr.move_to(14, 22)
        cr.show_text(self.title)
        cr.set_source_rgba(r, g, b, 1)
        cr.set_font_size(13)
        txt = self.caption or f"{self.values[-1]:.0f}{self.unit}"
        ext = cr.text_extents(txt)
        cr.move_to(w - ext.width - 14, 22)
        cr.show_text(txt)
        return False


def fmt_bytes(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


class TaskManager(Gtk.Window):
    COLS = ["Name", "PID", "User", "CPU", "Memory"]

    def __init__(self):
        super().__init__(title="Task Manager")
        self.set_default_size(*ui.fit_size(980, 640))
        self.get_style_context().add_class("neon")
        if os.path.exists(ui.LOGO):
            try:
                self.set_icon_from_file(ui.LOGO)
            except Exception:
                pass

        self.procs = {}
        self.rows = {}
        self.last_net = psutil.net_io_counters() if psutil else None
        self.last_disk = psutil.disk_io_counters() if psutil else None
        self.last_t = time.time()
        self.ncpu = (psutil.cpu_count() or 1) if psutil else 1

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(root)
        self.nb = Gtk.Notebook()
        root.pack_start(self.nb, True, True, 0)
        self.nb.append_page(self.build_processes(), Gtk.Label(label="⚙  Processes"))
        self.nb.append_page(self.build_performance(), Gtk.Label(label="📈  Performance"))

        if psutil:
            psutil.cpu_percent(None)
            self.tick()
            GLib.timeout_add(1000, self.tick)
        else:
            self.status.set_text("python3-psutil is missing")

    # ---- العمليات
    def build_processes(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(18)

        top = Gtk.Box(spacing=10)
        self.search = Gtk.SearchEntry()
        self.search.set_placeholder_text("Search processes…")
        self.search.connect("search-changed", lambda *_: self.filter.refilter())
        top.pack_start(self.search, True, True, 0)
        self.end_btn = ui.button("End task", "danger", self.end_task)
        top.pack_end(self.end_btn, False, False, 0)
        box.pack_start(top, False, False, 0)

        # name, pid, user, cpu, mem_mb, mem_text, cpu_text
        self.store = Gtk.ListStore(str, int, str, float, float, str, str)
        self.filter = self.store.filter_new()
        self.filter.set_visible_func(self.visible)
        self.sort = Gtk.TreeModelSort(model=self.filter)
        self.sort.set_sort_column_id(3, Gtk.SortType.DESCENDING)
        self.view = Gtk.TreeView(model=self.sort)
        self.view.set_headers_clickable(True)
        specs = [("Name", 0, 0, 300), ("PID", 1, 1, 80), ("User", 2, 2, 120), ("CPU", 6, 3, 110), ("Memory", 5, 4, 120)]
        for title, text_col, sort_col, width in specs:
            cell = Gtk.CellRendererText()
            col = Gtk.TreeViewColumn(title, cell, text=text_col)
            col.set_sort_column_id(sort_col)
            col.set_resizable(True)
            col.set_min_width(width)
            self.view.append_column(col)
        sw = Gtk.ScrolledWindow()
        sw.add(self.view)
        box.pack_start(sw, True, True, 0)

        self.status = ui.label("", "dim")
        box.pack_start(self.status, False, False, 0)
        return box

    def visible(self, model, it, _data):
        q = self.search.get_text().strip().lower()
        if not q:
            return True
        return q in model[it][0].lower() or q == str(model[it][1])

    def end_task(self, _b):
        model, it = self.view.get_selection().get_selected()
        if not it:
            return
        pid, name = model[it][1], model[it][0]
        dlg = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.QUESTION,
                                buttons=Gtk.ButtonsType.NONE, text=f"End “{name}”?")
        dlg.format_secondary_text("Unsaved work in this program will be lost.")
        dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "End task", Gtk.ResponseType.OK)
        resp = dlg.run()
        dlg.destroy()
        if resp != Gtk.ResponseType.OK:
            return
        try:
            os.kill(pid, signal.SIGTERM)
            GLib.timeout_add(2500, self._force_kill, pid)
        except (ProcessLookupError, PermissionError) as e:
            self.status.set_text(f"Couldn't end {name}: {e}")

    @staticmethod
    def _force_kill(pid):
        try:
            os.kill(pid, 0)
            os.kill(pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        return False

    # ---- الأداء
    def build_performance(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.set_border_width(18)
        grid = Gtk.Grid(row_spacing=14, column_spacing=14, column_homogeneous=True, row_homogeneous=True)
        self.c_cpu = Chart("CPU", (0.0, 0.9, 1.0))
        self.c_mem = Chart("Memory", (0.69, 0.36, 1.0))
        self.c_disk = Chart("Disk I/O", (0.2, 1.0, 0.67), unit=" MB/s", fixed_max=0)
        self.c_net = Chart("Network", (1.0, 0.24, 0.78), unit=" KB/s", fixed_max=0)
        for i, c in enumerate((self.c_cpu, self.c_mem, self.c_disk, self.c_net)):
            c.set_hexpand(True)
            c.set_vexpand(True)
            grid.attach(c, i % 2, i // 2, 1, 1)
        box.pack_start(grid, True, True, 0)
        self.info = ui.label("", "dim")
        box.pack_start(self.info, False, False, 0)
        return box

    # ---- التحديث الدوري
    def tick(self):
        now = time.time()
        dt = max(now - self.last_t, 0.001)
        self.last_t = now
        seen = set()
        for p in psutil.process_iter(["pid", "name", "username", "memory_info"]):
            try:
                pid = p.info["pid"]
                seen.add(pid)
                proc = self.procs.get(pid)
                if proc is None:
                    proc = self.procs[pid] = p
                    proc.cpu_percent(None)
                    cpu = 0.0
                else:
                    cpu = proc.cpu_percent(None) / self.ncpu
                mem = (p.info["memory_info"].rss if p.info["memory_info"] else 0) / 2**20
                name = p.info["name"] or "?"
                user = p.info["username"] or "?"
                vals = [name, pid, user, cpu, mem, f"{mem:,.1f} MB", f"{cpu:.1f}%"]
                it = self.rows.get(pid)
                if it is not None and self.store.iter_is_valid(it):
                    for idx, v in enumerate(vals):
                        if self.store[it][idx] != v:
                            self.store[it][idx] = v
                else:
                    self.rows[pid] = self.store.append(vals)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        for pid in list(self.rows):
            if pid not in seen:
                it = self.rows.pop(pid)
                if self.store.iter_is_valid(it):
                    self.store.remove(it)
                self.procs.pop(pid, None)

        cpu_total = psutil.cpu_percent(None)
        vm = psutil.virtual_memory()
        self.c_cpu.push(cpu_total, f"{cpu_total:.0f}%")
        self.c_mem.push(vm.percent, f"{fmt_bytes(vm.used)} / {fmt_bytes(vm.total)}")

        net = psutil.net_io_counters()
        if net and self.last_net:
            kb = ((net.bytes_recv - self.last_net.bytes_recv) + (net.bytes_sent - self.last_net.bytes_sent)) / 1024 / dt
            self.c_net.push(kb, f"{kb:,.0f} KB/s")
        self.last_net = net
        disk = psutil.disk_io_counters()
        if disk and self.last_disk:
            mb = ((disk.read_bytes - self.last_disk.read_bytes) + (disk.write_bytes - self.last_disk.write_bytes)) / 2**20 / dt
            self.c_disk.push(mb, f"{mb:.1f} MB/s")
        self.last_disk = disk

        temp = "n/a"
        try:
            temps = psutil.sensors_temperatures()
            vals = [t.current for lst in temps.values() for t in lst if t.current]
            if vals:
                temp = f"{max(vals):.0f}°C"
        except (AttributeError, OSError):
            pass
        up = int(time.time() - psutil.boot_time())
        self.info.set_text(f"Uptime {up // 3600}h {(up % 3600) // 60}m   ·   Temperature {temp}   ·   "
                           f"{len(seen)} processes   ·   {self.ncpu} threads")
        self.status.set_text(f"{len(seen)} processes   ·   CPU {cpu_total:.0f}%   ·   RAM {vm.percent:.0f}%")
        return True


def main():
    ui.apply_css()
    win = TaskManager()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    if "--perf" in sys.argv:
        win.nb.set_current_page(1)
    Gtk.main()


if __name__ == "__main__":
    main()
