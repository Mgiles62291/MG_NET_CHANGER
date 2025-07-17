"""
Network Profile Switcher (Auto‑Elevating)
----------------------------------------
Cross‑platform (Windows/macOS) Tkinter GUI that lets you store multiple static IP
profiles and apply them to a chosen adapter.  This version **auto‑elevates itself on
Windows** using UAC and refuses to run (with a warning) when not executed under
`sudo` on macOS.

Features
~~~~~~~~
* Detect network adapters (psutil)
* Create / edit / delete profiles stored in `profiles.json`
* Import profiles from a CSV file (header row required)
* Apply profile – runs `netsh` (Windows) or `networksetup` (macOS)
* Auto‑elevate on Windows; friendly warning on macOS if not root

Dependencies
~~~~~~~~~~~~
    pip install psutil

Author: ChatGPT (o3) – 2025‑07‑17
"""

from __future__ import annotations
import csv
import json
import os
import platform
import subprocess
import sys
import ctypes
from pathlib import Path
from typing import List, Dict

import psutil  # third‑party, cross‑platform NIC query
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

PROFILE_FILE = "profiles.json"

# ---------------------------------------------------------------------------
# Elevation helpers
# ---------------------------------------------------------------------------

def is_admin() -> bool:
    """Return True if running with administrative/root privileges."""
    system = platform.system()
    if system == "Windows":
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
    elif system == "Darwin":
        return os.geteuid() == 0
    else:
        return False  # unsupported OS for elevation logic


def elevate_if_needed() -> None:
    """Auto‑elevate on Windows; warn and exit on macOS if not root."""
    system = platform.system()
    if is_admin():
        return  # already elevated

    if system == "Windows":
        # Relaunch the current Python interpreter with UAC prompt
        params = " ".join([f'"{arg}"' for arg in sys.argv])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        sys.exit()  # parent exits – child continues after UAC
    elif system == "Darwin":
        # macOS – kindly inform the user to rerun with sudo
        messagebox.showwarning(
            "Administrator rights required",
            "Network changes need elevated privileges.\n\n"
            "Please close and relaunch the app with:\n"
            "sudo python3 network_profile_switcher.py",
        )
        sys.exit(1)
    else:
        messagebox.showerror("Unsupported OS", "Only Windows and macOS are supported.")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def load_profiles() -> List[Dict]:
    path = Path(PROFILE_FILE)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def save_profiles(data: List[Dict]) -> None:
    Path(PROFILE_FILE).write_text(json.dumps(data, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# OS interaction helpers
# ---------------------------------------------------------------------------

def list_adapters() -> List[str]:
    """Return a list of network interface names as reported by psutil."""
    return list(psutil.net_if_addrs().keys())


def apply_profile(adapter: str, profile: Dict) -> None:
    """Generate and execute OS‑specific commands to apply a static IP profile."""
    ip = profile["IP"]
    subnet = profile["Subnet"]
    gateway = profile["Gateway"]
    dns1 = profile.get("DNS1")
    dns2 = profile.get("DNS2")

    system = platform.system()
    if system == "Windows":
        cmds = [
            f'netsh interface ip set address "{adapter}" static {ip} {subnet} {gateway}',
            f'netsh interface ip set dns "{adapter}" static {dns1}',
        ]
        if dns2:
            cmds.append(f'netsh interface ip add dns "{adapter}" {dns2} index=2')
    elif system == "Darwin":
        cmds = [
            f'networksetup -setmanual "{adapter}" {ip} {subnet} {gateway}',
        ]
        dnses = " ".join([d for d in (dns1, dns2) if d])
        if dnses:
            cmds.append(f'networksetup -setdnsservers "{adapter}" {dnses}')
    else:
        messagebox.showerror("Unsupported OS", "Only Windows and macOS are supported.")
        return

    for c in cmds:
        result = subprocess.run(c, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            messagebox.showerror(
                "Command failed",
                f"Cmd: {c}\n\nStdout:\n{result.stdout}\nStderr:\n{result.stderr}",
            )
            break


# ---------------------------------------------------------------------------
# GUI classes
# ---------------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Network Profile Switcher")
        self.resizable(False, False)

        self.adapter_var = tk.StringVar()
        self.profile_list: List[Dict] = load_profiles()
        self.selected_profile_index: int | None = None

        self._build_widgets()
        self._populate_adapters()
        self._refresh_profile_list()

    # ---------------- GUI construction ----------------
    def _build_widgets(self):
        tk.Label(self, text="Adapter:").grid(row=0, column=0, sticky="e")
        self.adapter_menu = ttk.Combobox(self, textvariable=self.adapter_var, state="readonly", width=28)
        self.adapter_menu.grid(row=0, column=1, columnspan=2, padx=5, pady=5)

        self.listbox = tk.Listbox(self, height=8, width=40)
        self.listbox.grid(row=1, column=0, columnspan=3, padx=5, pady=5)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        ttk.Button(self, text="Add", command=self._add_profile).grid(row=2, column=0, sticky="ew", padx=2)
        ttk.Button(self, text="Edit", command=self._edit_profile).grid(row=2, column=1, sticky="ew", padx=2)
        ttk.Button(self, text="Delete", command=self._delete_profile).grid(row=2, column=2, sticky="ew", padx=2)

        ttk.Button(self, text="Apply", command=self._apply_selected).grid(row=3, column=0, columnspan=3, sticky="ew", padx=2, pady=4)
        ttk.Button(self, text="Import CSV", command=self._import_csv).grid(row=4, column=0, columnspan=3, sticky="ew", padx=2)

    def _populate_adapters(self):
        adapters = list_adapters()
        self.adapter_menu["values"] = adapters
        if adapters:
            self.adapter_var.set(adapters[0])

    # ---------------- Profile list helpers ----------------
    def _refresh_profile_list(self):
        self.listbox.delete(0, tk.END)
        for p in self.profile_list:
            self.listbox.insert(tk.END, p["ProfileName"])

    def _on_select(self, _):
        sel = self.listbox.curselection()
        self.selected_profile_index = sel[0] if sel else None

    # ---------------- Button actions ----------------
    def _add_profile(self):
        ProfileDialog(self, "Add Profile")

    def _edit_profile(self):
        if self.selected_profile_index is None:
            messagebox.showinfo("Select", "Please select a profile to edit.")
            return
        ProfileDialog(self, "Edit Profile", data=self.profile_list[self.selected_profile_index])

    def _delete_profile(self):
        if self.selected_profile_index is None:
            return
        if messagebox.askyesno("Delete", "Delete selected profile?"):
            del self.profile_list[self.selected_profile_index]
            save_profiles(self.profile_list)
            self._refresh_profile_list()

    def _apply_selected(self):
        if self.selected_profile_index is None:
            messagebox.showinfo("Select", "Please select a profile to apply.")
            return
        adapter = self.adapter_var.get()
        profile = self.profile_list[self.selected_profile_index]
        apply_profile(adapter, profile)

    def _import_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not path:
            return
        try:
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.profile_list.append(row)
            save_profiles(self.profile_list)
            self._refresh_profile_list()
            messagebox.showinfo("Imported", f"Imported profiles from {path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))


class ProfileDialog(tk.Toplevel):
    def __init__(self, master: App, title: str, data: Dict | None = None):
        super().__init__(master)
        self.master: App = master
        self.title(title)
        self.resizable(False, False)

        fields = ["ProfileName", "IP", "Subnet", "Gateway", "DNS1", "DNS2"]
        self.vars = {f: tk.StringVar(value=data.get(f, "") if data else "") for f in fields}

        for i, f in enumerate(fields):
            tk.Label(self, text=f + ":").grid(row=i, column=0, sticky="e")
            tk.Entry(self, textvariable=self.vars[f]).grid(row=i, column=1, padx=5, pady=2)

        ttk.Button(self, text="Save", command=self._save).grid(row=len(fields), column=0, columnspan=2, sticky="ew", pady=4)

    def _save(self):
        profile = {k: v.get() for k, v in self.vars.items()}
        if not profile["ProfileName"]:
            messagebox.showerror("Required", "ProfileName is required")
            return
        if self.title().startswith("Edit") and self.master.selected_profile_index is not None:
            self.master.profile_list[self.master.selected_profile_index] = profile
        else:
            self.master.profile_list.append(profile)
        save_profiles(self.master.profile_list)
        self.master._refresh_profile_list()
        self.destroy()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
if __name__ == "
