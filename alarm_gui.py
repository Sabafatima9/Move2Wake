"""
Dance Alarm Dashboard (tkinter) - manage alarms and trigger the
"dance for 10 seconds to stop the ringing" flow.

Run:
    python alarm_gui.py
"""

import json
import queue
import threading
import uuid
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox

from alarm import SNOOZE_MINUTES, dance_check, ring_loop, victory_tune

ALARM_FILE = "alarms.json"
POLL_MS = 500


def load_alarms():
    try:
        with open(ALARM_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return []


def save_alarms(alarms):
    with open(ALARM_FILE, "w", encoding="utf-8") as f:
        json.dump(alarms, f, indent=2)


class DanceAlarmApp:
    def __init__(self, root):
        self.root = root
        root.title("Dance Alarm")
        root.geometry("560x430")
        root.resizable(False, False)

        self.alarms = load_alarms()
        self.fired = set()          # (alarm_id, date_str) already triggered
        self.snooze_until = {}      # alarm_id -> datetime
        self.ringing_id = None
        self.ring_label = ""
        self.stop_event = None
        self.msg_q = queue.Queue()

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(POLL_MS, self._poll)

    # ---------- UI ----------

    def _build_ui(self):
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="Time (HH:MM)").grid(row=0, column=0, padx=(0, 4))
        self.time_entry = ttk.Entry(top, width=8)
        self.time_entry.grid(row=0, column=1, padx=(0, 12))

        ttk.Label(top, text="Label").grid(row=0, column=2, padx=(0, 4))
        self.label_entry = ttk.Entry(top, width=18)
        self.label_entry.grid(row=0, column=3, padx=(0, 12))

        ttk.Label(top, text="Repeat").grid(row=0, column=4, padx=(0, 4))
        self.repeat_box = ttk.Combobox(top, width=7, state="readonly",
                                       values=["Once", "Daily"])
        self.repeat_box.current(1)
        self.repeat_box.grid(row=0, column=5, padx=(0, 12))

        ttk.Button(top, text="Add alarm", command=self._add).grid(row=0, column=6)

        mid = ttk.Frame(self.root, padding=(10, 0))
        mid.pack(fill="both", expand=True)

        cols = ("time", "label", "repeat", "status")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", height=8)
        for c, text, width in [("time", "Time", 80), ("label", "Label", 180),
                               ("repeat", "Repeat", 70), ("status", "Status", 140)]:
            self.tree.heading(c, text=text)
            self.tree.column(c, width=width, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(mid, command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sb.set)

        btns = ttk.Frame(self.root, padding=10)
        btns.pack(fill="x")
        ttk.Button(btns, text="Enable / Disable", command=self._toggle).pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="Delete", command=self._delete).pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="Test dance now (10s)",
                   command=self._test_dance).pack(side="left", padx=(0, 8))
        ttk.Label(btns, text="Camera window: keep dancing 10s | S = snooze | Q = quit").pack(side="right")

        self.status = ttk.Label(self.root, text="No alarm ringing", padding=8,
                                anchor="w", relief="sunken")
        self.status.pack(fill="x", side="bottom")

        self._refresh()

    # ---------- actions ----------

    def _add(self):
        t = self.time_entry.get().strip()
        try:
            hh, mm = map(int, t.split(":"))
            if not (0 <= hh <= 23 and 0 <= mm <= 59):
                raise ValueError
        except (ValueError, AttributeError):
            messagebox.showwarning("Invalid time", "Enter time as HH:MM (e.g. 06:30).")
            return
        self.alarms.append({
            "id": uuid.uuid4().hex[:8],
            "time": f"{hh:02d}:{mm:02d}",
            "label": self.label_entry.get().strip() or "Alarm",
            "repeat": self.repeat_box.get(),
            "enabled": True,
        })
        self.alarms.sort(key=lambda a: a["time"])
        self.time_entry.delete(0, "end")
        self.label_entry.delete(0, "end")
        self._persist_and_refresh()

    def _selected(self):
        sel = self.tree.selection()
        if not sel:
            return None
        aid = sel[0]
        return next((a for a in self.alarms if a["id"] == aid), None)

    def _toggle(self):
        a = self._selected()
        if a:
            a["enabled"] = not a["enabled"]
            self._persist_and_refresh()

    def _delete(self):
        a = self._selected()
        if a:
            self.alarms.remove(a)
            self._persist_and_refresh()

    def _test_dance(self):
        if self.ringing_id is None:
            self._trigger({"id": "test", "time": "--:--", "label": "Quick test",
                           "repeat": "Once", "enabled": True})

    # ---------- scheduling ----------

    def _trigger(self, alarm):
        self.ringing_id = alarm["id"]
        self.ring_label = f"{alarm['time']} - {alarm['label']}"
        self.stop_event = threading.Event()
        self._set_status(f"RINGING: {self.ring_label} - get up and DANCE!")
        threading.Thread(target=ring_loop, args=(self.stop_event,), daemon=True).start()
        threading.Thread(target=self._worker, args=(alarm["id"], self.stop_event),
                         daemon=True).start()

    def _worker(self, alarm_id, stop_event):
        res = dance_check(stop_event)
        stop_event.set()
        if res == "success":
            victory_tune()
        self.msg_q.put(("done", alarm_id, res))

    def _poll(self):
        self._drain_queue()
        if self.ringing_id is None:
            self._check_alarms()
        self._refresh_statuses()
        self.root.after(POLL_MS, self._poll)

    def _check_alarms(self):
        now = datetime.now()
        hhmm = now.strftime("%H:%M")
        for a in self.alarms:
            if not a["enabled"]:
                continue
            su = self.snooze_until.get(a["id"])
            if su:
                if now >= su:
                    del self.snooze_until[a["id"]]
                    self._trigger(a)
                continue
            if a["time"] == hhmm:
                key = (a["id"], now.date().isoformat())
                if key not in self.fired:
                    self.fired.add(key)
                    self._trigger(a)
                    break

    def _drain_queue(self):
        try:
            while True:
                _, aid, res = self.msg_q.get_nowait()
        except queue.Empty:
            return
        self.ringing_id = None
        if res == "success":
            a = next((x for x in self.alarms if x["id"] == aid), None)
            if a and a["repeat"] == "Once":
                a["enabled"] = False
                self._persist_and_refresh()
            self._set_status(f"Alarm silenced - nice dancing! ({self.ring_label})")
        elif res == "snooze":
            self.snooze_until[aid] = datetime.now() + timedelta(minutes=SNOOZE_MINUTES)
            self._set_status(f"Snoozed {SNOOZE_MINUTES} minutes ({self.ring_label})")
        else:
            self._set_status(f"Alarm stopped ({self.ring_label})")

    def _set_status(self, text):
        self.status.config(text=text)

    # ---------- tree helpers ----------

    def _persist_and_refresh(self):
        save_alarms(self.alarms)
        self._refresh()

    def _refresh(self):
        self.tree.delete(*self.tree.get_children())
        for a in self.alarms:
            self.tree.insert("", "end", iid=a["id"], values=(
                a["time"], a["label"], a["repeat"],
                "ON" if a["enabled"] else "off"))

    def _refresh_statuses(self):
        for a in self.alarms:
            if self.ringing_id == a["id"]:
                st = "RINGING!"
            elif a["id"] in self.snooze_until:
                st = f"snoozed until {self.snooze_until[a['id']]:%H:%M}"
            else:
                st = "ON" if a["enabled"] else "off"
            self.tree.set(a["id"], "status", st)

    def _on_close(self):
        if self.ringing_id is not None and self.stop_event:
            self.stop_event.set()
        save_alarms(self.alarms)
        self.root.destroy()


def main():
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except tk.TclError:
        pass
    DanceAlarmApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
