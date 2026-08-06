#!/usr/bin/env python3
"""
Live dashboard for the SX1262 radio log printed over UART4 (115200 8N1).

Requires an external USB-to-serial adapter wired to UART4 (PA0=TX, PA1=RX,
plus GND) -- this board has no onboard USB-serial bridge chip.

Usage:
    pip install pyserial
    python radio_dashboard.py
"""

import queue
import re
import threading
import tkinter as tk
from tkinter import ttk

import serial
import serial.tools.list_ports

BAUD_RATE = 115200
POLL_INTERVAL_MS = 100
MAX_ROWS = 1000

LINE_RE = re.compile(r"^\[(\d+)\]\s+RADIO\s+(\S+)\s*(.*)$")

# ---- palette (dark mode) ---------------------------------------------------
BG = "#000000"
PANEL_BG = "#141414"
CARD_TEXT = "#FFFFFF"
BORDER = "#262626"
TEXT_MAIN = "#F5F5F5"
TEXT_MUTED = "#9A9A9A"
ACCENT = "#B18AFF"
ACCENT_DARK = "#9569E8"

EVENT_COLORS = {
    "TX": "#FF6FA8",
    "RX": "#3ED694",
    "TXDONE": "#4FA8FF",
    "TIMEOUT": "#FFA34D",
    "RAW": "#8C7EC9",
}
EVENT_TINTS = {
    "TX": "#241318",
    "RX": "#0F2118",
    "TXDONE": "#0F1B26",
    "TIMEOUT": "#26190D",
    "RAW": "#1C1922",
}
EVENT_EMOJI = {
    "TX": "\U0001F4E4",
    "RX": "\U0001F4E5",
    "TXDONE": "✅",
    "TIMEOUT": "⏱",
    "RAW": "\U0001F4DD",
}
CONNECTED_COLOR = "#3ED694"
DISCONNECTED_COLOR = "#FF5C6C"


def _rounded_rect(canvas, x1, y1, x2, y2, radius=16, **kwargs):
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


class StatCard(tk.Canvas):
    """A little rounded pastel card showing an emoji, a label, and a value."""

    def __init__(self, parent, emoji, label, color, width=150, height=92, value="0"):
        super().__init__(parent, width=width, height=height, bg=BG, highlightthickness=0)
        _rounded_rect(self, 2, 2, width - 2, height - 2, radius=18, fill=color, outline="")
        self.create_text(16, 18, text=emoji, font=("Segoe UI Emoji", 15), anchor="w", fill=CARD_TEXT)
        self.create_text(width - 14, 18, text=label, font=("Segoe UI Semibold", 9), anchor="e", fill=CARD_TEXT)
        self.value_id = self.create_text(
            width / 2, height - 28, text=value, font=("Segoe UI Semibold", 22), fill=CARD_TEXT
        )

    def set_value(self, value):
        self.itemconfig(self.value_id, text=str(value))


class RadioDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Radio Dashboard")
        self.root.configure(bg=BG)

        self.serial_port = None
        self.reader_thread = None
        self.stop_event = threading.Event()
        self.line_queue = queue.Queue()

        self.stats = {"TX": 0, "RX": 0, "TXDONE": 0, "TIMEOUT": 0}
        self.cards = {}

        self._build_style()
        self._build_ui()
        self._refresh_ports()
        self.root.after(POLL_INTERVAL_MS, self._poll_queue)

    def _build_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=TEXT_MAIN, font=("Segoe UI", 10))
        style.configure("Header.TLabel", background=BG, foreground=ACCENT_DARK, font=("Segoe UI Semibold", 20))
        style.configure("Sub.TLabel", background=BG, foreground=TEXT_MUTED, font=("Segoe UI", 10))
        style.configure("Status.TLabel", background=BG, foreground=TEXT_MAIN, font=("Segoe UI Semibold", 10))

        style.configure(
            "TButton",
            background=ACCENT,
            foreground="white",
            font=("Segoe UI Semibold", 10),
            borderwidth=0,
            padding=(12, 6),
        )
        style.map("TButton", background=[("active", ACCENT_DARK)])

        style.configure("TCombobox", padding=4, font=("Segoe UI", 10))

        style.configure(
            "Treeview",
            background=PANEL_BG,
            fieldbackground=PANEL_BG,
            foreground=TEXT_MAIN,
            rowheight=26,
            font=("Consolas", 10),
            borderwidth=0,
        )
        style.map("Treeview", background=[("selected", ACCENT_DARK)], foreground=[("selected", "white")])
        style.configure("Treeview.Heading", background=ACCENT, foreground="white", font=("Segoe UI Semibold", 10))
        style.map("Treeview.Heading", background=[("active", ACCENT_DARK)])

        style.configure(
            "Vertical.TScrollbar",
            background=ACCENT,
            troughcolor=PANEL_BG,
            bordercolor=PANEL_BG,
            arrowcolor=TEXT_MAIN,
            darkcolor=PANEL_BG,
            lightcolor=PANEL_BG,
        )
        style.map("Vertical.TScrollbar", background=[("active", ACCENT_DARK)])

    def _build_ui(self):
        header = ttk.Frame(self.root, padding=(16, 16, 16, 4))
        header.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(header, text="\U0001F4E1 Radio Dashboard", style="Header.TLabel").pack(side=tk.LEFT)
        ttk.Label(header, text="  SX1262 link monitor", style="Sub.TLabel").pack(side=tk.LEFT, padx=(4, 0))

        conn = ttk.Frame(self.root, padding=(16, 8))
        conn.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(conn, text="Port:").pack(side=tk.LEFT)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(conn, textvariable=self.port_var, width=18, state="readonly")
        self.port_combo.pack(side=tk.LEFT, padx=(4, 8))

        ttk.Button(conn, text="\U0001F504 Refresh", command=self._refresh_ports).pack(side=tk.LEFT, padx=4)
        self.connect_btn = ttk.Button(conn, text="▶ Connect", command=self._toggle_connection)
        self.connect_btn.pack(side=tk.LEFT, padx=4)

        self.status_dot = tk.Canvas(conn, width=14, height=14, bg=BG, highlightthickness=0)
        self.status_dot_id = self.status_dot.create_oval(2, 2, 12, 12, fill=DISCONNECTED_COLOR, outline="")
        self.status_dot.pack(side=tk.LEFT, padx=(16, 4))
        self.status_var = tk.StringVar(value="Disconnected")
        ttk.Label(conn, textvariable=self.status_var, style="Status.TLabel").pack(side=tk.LEFT)

        ttk.Button(conn, text="\U0001F9F9 Clear", command=self._clear_log).pack(side=tk.RIGHT)

        cards_row = ttk.Frame(self.root, padding=(16, 8))
        cards_row.pack(side=tk.TOP, fill=tk.X)

        card_defs = [
            ("TX", "\U0001F4E4", "SENT"),
            ("RX", "\U0001F4E5", "RECEIVED"),
            ("TXDONE", "✅", "TX DONE"),
            ("TIMEOUT", "⏱", "TIMEOUTS"),
        ]
        for key, emoji, label in card_defs:
            card = StatCard(cards_row, emoji, label, EVENT_COLORS[key])
            card.pack(side=tk.LEFT, padx=(0, 10))
            self.cards[key] = card

        self.rssi_card = StatCard(cards_row, "\U0001F4F6", "RSSI dBm", ACCENT, value="--")
        self.rssi_card.pack(side=tk.LEFT, padx=(0, 10))
        self.snr_card = StatCard(cards_row, "\U0001F4C8", "SNR dB", ACCENT_DARK, value="--")
        self.snr_card.pack(side=tk.LEFT)

        log_label = ttk.Label(self.root, text="\U0001F4DC Event Log", style="Sub.TLabel")
        log_label.pack(side=tk.TOP, anchor="w", padx=18, pady=(6, 0))

        table_frame = tk.Frame(self.root, bg=BORDER, highlightthickness=0)
        table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=16, pady=(4, 16))

        inner = tk.Frame(table_frame, bg=PANEL_BG)
        inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        columns = ("time", "event", "details")
        self.tree = ttk.Treeview(inner, columns=columns, show="headings")
        self.tree.heading("time", text="Time (ms)")
        self.tree.heading("event", text="Event")
        self.tree.heading("details", text="Details")
        self.tree.column("time", width=100, anchor="w")
        self.tree.column("event", width=110, anchor="w")
        self.tree.column("details", width=520, anchor="w")

        for key, tint in EVENT_TINTS.items():
            self.tree.tag_configure(key, background=tint, foreground=TEXT_MAIN)

        scrollbar = ttk.Scrollbar(inner, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_combo["values"] = ports
        if ports and not self.port_var.get():
            self.port_var.set(ports[0])

    def _toggle_connection(self):
        if self.serial_port is None:
            self._connect()
        else:
            self._disconnect()

    def _connect(self):
        port = self.port_var.get()
        if not port:
            self.status_var.set("No port selected")
            return

        try:
            self.serial_port = serial.Serial(port, BAUD_RATE, timeout=0.2)
        except serial.SerialException as exc:
            self.status_var.set(f"Failed to open {port}: {exc}")
            return

        self.stop_event.clear()
        self.reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.reader_thread.start()

        self.status_var.set(f"Connected: {port} @ {BAUD_RATE}")
        self.status_dot.itemconfig(self.status_dot_id, fill=CONNECTED_COLOR)
        self.connect_btn.config(text="⏹ Disconnect")

    def _disconnect(self):
        self.stop_event.set()
        if self.reader_thread is not None:
            self.reader_thread.join(timeout=1)
        if self.serial_port is not None:
            self.serial_port.close()
        self.serial_port = None
        self.status_var.set("Disconnected")
        self.status_dot.itemconfig(self.status_dot_id, fill=DISCONNECTED_COLOR)
        self.connect_btn.config(text="▶ Connect")

    def _read_loop(self):
        while not self.stop_event.is_set():
            try:
                raw = self.serial_port.readline()
            except serial.SerialException:
                break
            if raw:
                line = raw.decode("utf-8", errors="replace").strip()
                if line:
                    self.line_queue.put(line)

    def _poll_queue(self):
        try:
            while True:
                line = self.line_queue.get_nowait()
                self._handle_line(line)
        except queue.Empty:
            pass
        self.root.after(POLL_INTERVAL_MS, self._poll_queue)

    def _handle_line(self, line):
        match = LINE_RE.match(line)
        if not match:
            self._add_row("?", "RAW", line)
            return

        timestamp, event, details = match.groups()
        details = details.strip()

        if event in self.stats:
            self.stats[event] += 1
            self.cards[event].set_value(self.stats[event])

        if event == "RX":
            rssi_match = re.search(r"rssi=(-?\d+)", details)
            snr_match = re.search(r"snr=(-?\d+)", details)
            if rssi_match:
                self.rssi_card.set_value(rssi_match.group(1))
            if snr_match:
                self.snr_card.set_value(snr_match.group(1))

        self._add_row(timestamp, event, details)

    def _add_row(self, timestamp, event, details):
        emoji = EVENT_EMOJI.get(event, "")
        tag = event if event in EVENT_TINTS else "RAW"
        self.tree.insert("", "end", values=(timestamp, f"{emoji} {event}", details), tags=(tag,))
        children = self.tree.get_children()
        if len(children) > MAX_ROWS:
            self.tree.delete(children[0])
        self.tree.yview_moveto(1.0)

    def _clear_log(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for key in self.stats:
            self.stats[key] = 0
            self.cards[key].set_value(0)
        self.rssi_card.set_value("--")
        self.snr_card.set_value("--")

    def _on_close(self):
        self._disconnect()
        self.root.destroy()


def main():
    root = tk.Tk()
    RadioDashboard(root)
    root.geometry("900x560")
    root.minsize(760, 480)
    root.mainloop()


if __name__ == "__main__":
    main()
