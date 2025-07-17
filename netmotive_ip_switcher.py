#!/usr/bin/env python3
"""
NetMotive IP Switcher (Auto-Elevating)
--------------------------------------
Tkinter GUI for managing multiple static IP profiles and applying them to a selected adapter.
"""

import os
import sys
import ctypes
import platform
import json
import csv
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import psutil

PROFILE_FILE = "profiles.json"

def elevate_if_needed():
    if platform.system() == "Windows":
        try:
            if not ctypes.windll.shell32.IsUserAnAdmin():
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", sys.executable, " ".join(sys.argv), None, 1)
                sys.exit()
        except:
            messagebox.showerror("Error", "Failed to check admin rights.")
            sys.exit(1)
    else:
        if os.geteuid() != 0:
            messagebox.showwarning(
                "Administrator Required",
                "Please run this script with sudo to change network settings."
            )
            sys.exit(1)

def load_profiles():
    if os.path.exists(PROFILE_FILE):
        with open(PROFILE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_profiles(data):
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def list_adapters():
    return list(psutil.net_if_addrs().keys())

def apply_profile(adapter, profile):
    system = platform.system()
    ip = profile["IP"]
    subnet = profile["Subnet"]
    gateway = profile["Gateway"]
    dns1 = profile.get("DNS1", "")
    dns2 = profile.get("DNS2", "")
    cmds = []

    if system == "Windows":
        cmds = [
            f'netsh interface ip set address name="{adapter}" static {ip} {subnet} {gateway}',
            f'netsh interface ip set dns name="{adapter}" static {dns1}'
        ]
        if dns2:
            cmds.append(f'netsh interface ip add dns name="{adapter}" {dns2} index=2')
    elif system == "Darwin":
        cmds = [
            f'networksetup -setmanual "{adapter}" {ip} {subnet} {gateway}'
        ]
        if dns1 or dns2:
            dns = " ".join(filter(None, [dns1, dns2]))
            cmds.append(f'networksetup -setdnsservers "{adapter}" {dns}')
    else:
        messagebox.showerror("Unsupported OS", "Only Windows and macOS are supported.")
        return

    for c in cmds:
        result = subprocess.run(c, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            messagebox.showerror("Command failed", f"Command: {c}\n\n{result.stderr.strip()}")
            break

def export_example_csv():
    path = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv")],
        title="Export Example CSV"
    )
    if not path:
        return
    headers = ["ProfileName", "IP", "Subnet", "Gateway", "DNS1", "DNS2"]
    example_row = {
        "ProfileName": "OfficeLAN",
        "IP": "192.168.1.100",
        "Subnet": "255.255.255.0",
        "Gateway": "192.168.1.1",
        "DNS1": "8.8.8.8",
        "DNS2": "1.1.1.1"
    }
    try:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerow(example_row)
        messagebox.showinfo("Exported", f"Example CSV saved to:\n{path}")
    except Exception as e:
        messagebox.showerror("Export failed", str(e))

def export_profiles_csv():
    if not App.profile_list:
        messagebox.showinfo("No Profiles", "There are no profiles to export.")
        return

    path = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv")],
        title="Export Profiles to CSV"
    )
    if not path:
        return
    headers = ["ProfileName", "IP", "Subnet", "Gateway", "DNS1", "DNS2"]
    try:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for row in App.profile_list:
                writer.writerow(row)
        messagebox.showinfo("Export Complete", f"Profiles exported to:\n{path}")
    except Exception as e:
        messagebox.showerror("Export Failed", str(e))

class App(tk.Tk):
    profile_list = []

    def __init__(self):
        super().__init__()
        self.title("NetMotive IP Switcher")
        self.resizable(False, False)
        self.adapter_var = tk.StringVar()
        App.profile_list = load_profiles()
        self.selected_profile_index = None
        self.create_menu()
        self.create_widgets()

    def create_menu(self):
        menu_bar = tk.Menu(self)
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Import CSV", command=self.import_csv)
        file_menu.add_command(label="Export Example CSV", command=export_example_csv)
        file_menu.add_command(label="Export Current Profiles", command=export_profiles_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        menu_bar.add_cascade(label="File", menu=file_menu)
        self.config(menu=menu_bar)

    def create_widgets(self):
        adapters = list_adapters()
        tk.Label(self, text="Adapter:").grid(row=0, column=0, sticky="e")
        self.adapter_menu = ttk.Combobox(self, textvariable=self.adapter_var, values=adapters, width=30, state="readonly")
        self.adapter_menu.grid(row=0, column=1, columnspan=2, padx=5, pady=5)
        if adapters:
            self.adapter_var.set(adapters[0])

        self.listbox = tk.Listbox(self, height=8, width=40)
        self.listbox.grid(row=1, column=0, columnspan=3, padx=5, pady=5)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)
        self.refresh_list()

        ttk.Button(self, text="Add", command=self.add_profile).grid(row=2, column=0, sticky="ew", padx=2)
        ttk.Button(self, text="Edit", command=self.edit_profile).grid(row=2, column=1, sticky="ew", padx=2)
        ttk.Button(self, text="Delete", command=self.delete_profile).grid(row=2, column=2, sticky="ew", padx=2)

        ttk.Button(self, text="Apply", command=self.apply_selected).grid(row=3, column=0, columnspan=3, sticky="ew", padx=2, pady=6)

    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        for p in self.profile_list:
            self.listbox.insert(tk.END, p["ProfileName"])

    def on_select(self, _):
        sel = self.listbox.curselection()
        self.selected_profile_index = sel[0] if sel else None

    def add_profile(self):
        ProfileDialog(self, title="Add Profile")

    def edit_profile(self):
        if self.selected_profile_index is None:
            messagebox.showinfo("Select", "Please select a profile to edit.")
            return
        ProfileDialog(self, title="Edit Profile", data=self.profile_list[self.selected_profile_index])

    def delete_profile(self):
        if self.selected_profile_index is not None:
            del self.profile_list[self.selected_profile_index]
            save_profiles(self.profile_list)
            self.refresh_list()

    def apply_selected(self):
        if self.selected_profile_index is None:
            messagebox.showinfo("Select", "Please select a profile to apply.")
            return
        adapter = self.adapter_var.get()
        profile = self.profile_list[self.selected_profile_index]
        apply_profile(adapter, profile)

    def import_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if not path:
            return
        try:
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.profile_list.append(row)
            save_profiles(self.profile_list)
            self.refresh_list()
            messagebox.showinfo("Import", "Profiles imported successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import CSV:\\n{e}")

class ProfileDialog(tk.Toplevel):
    def __init__(self, master, title, data=None):
        super().__init__(master)
        self.master = master
        self.title(title)
        self.resizable(False, False)
        self.vars = {key: tk.StringVar(value=(data.get(key) if data else "")) for key in ["ProfileName", "IP", "Subnet", "Gateway", "DNS1", "DNS2"]}
        for i, (key, var) in enumerate(self.vars.items()):
            tk.Label(self, text=key + ":").grid(row=i, column=0, sticky="e")
            tk.Entry(self, textvariable=var).grid(row=i, column=1, padx=5, pady=2)
        ttk.Button(self, text="Save", command=self.save).grid(row=6, column=0, columnspan=2, pady=5)

    def save(self):
        new_profile = {k: v.get() for k, v in self.vars.items()}
        if not new_profile["ProfileName"]:
            messagebox.showwarning("Input Error", "Profile name is required.")
            return
        if self.master.selected_profile_index is not None and self.title().startswith("Edit"):
            self.master.profile_list[self.master.selected_profile_index] = new_profile
        else:
            self.master.profile_list.append(new_profile)
        save_profiles(self.master.profile_list)
        self.master.refresh_list()
        self.destroy()

if __name__ == "__main__":
    elevate_if_needed()
    App().mainloop()# MAIN SCRIPT PLACEHOLDER
# (User should paste the final app code here or I can regenerate it again if needed.)
