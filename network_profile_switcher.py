#!/usr/bin/env python3
"""
Network Profile Switcher
------------------------
Cross‑platform (Windows/macOS) Tkinter GUI to manage multiple static IP profiles
and apply them to a selected network adapter.

* View adapters
* Create / edit / delete profiles
* Import profiles from CSV
* Save profiles to profiles.json
* Apply a profile (uses netsh or networksetup)

Requires:
    pip install psutil
"""

import json, csv, os, platform, subprocess, sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import psutil

PROFILE_FILE = "profiles.json"

def load_profiles():
    if os.path.exists(PROFILE_FILE):
        try:
            with open(PROFILE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_profiles(data):
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def list_adapters():
    # psutil.net_if_addrs keys give adapter names
    return list(psutil.net_if_addrs().keys())

def apply_profile(adapter, profile):
    system = platform.system()
    ip = profile["IP"]
    subnet = profile["Subnet"]
    gateway = profile["Gateway"]
    dns1 = profile.get("DNS1")
    dns2 = profile.get("DNS2")
    if system == "Windows":
        cmds = [
            f'netsh interface ip set address "{adapter}" static {ip} {subnet} {gateway}',
            f'netsh interface ip set dns "{adapter}" static {dns1}'
        ]
        if dns2:
            cmds.append(f'netsh interface ip add dns "{adapter}" {dns2} index=2')
    elif system == "Darwin":
        cmds = [
            f'networksetup -setmanual "{adapter}" {ip} {subnet} {gateway}',
        ]
        dnses = " ".join([x for x in (dns1, dns2) if x])
        if dnses:
            cmds.append(f'networksetup -setdnsservers "{adapter}" {dnses}')
    else:
        messagebox.showerror("Unsupported OS", "Only Windows and macOS are supported.")
        return

    for c in cmds:
        print("Running:", c)
        subprocess.run(c, shell=True)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Network Profile Switcher")
        self.resizable(False, False)
        self.adapter_var = tk.StringVar()
        self.profile_list = load_profiles()
        self.selected_profile_index = None
        self.create_widgets()

    def create_widgets(self):
        adapters = list_adapters()
        tk.Label(self, text="Adapter: ").grid(row=0, column=0, sticky="e")
        self.adapter_menu = ttk.Combobox(self, textvariable=self.adapter_var, values=adapters, width=30, state="readonly")
        self.adapter_menu.grid(row=0, column=1, columnspan=2, padx=5, pady=5)
        if adapters:
            self.adapter_var.set(adapters[0])

        # Listbox
        self.listbox = tk.Listbox(self, height=8, width=40)
        self.listbox.grid(row=1, column=0, columnspan=3, padx=5, pady=5)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)
        self.refresh_list()

        # Buttons
        ttk.Button(self, text="Add", command=self.add_profile).grid(row=2, column=0, sticky="ew", padx=2)
        ttk.Button(self, text="Edit", command=self.edit_profile).grid(row=2, column=1, sticky="ew", padx=2)
        ttk.Button(self, text="Delete", command=self.delete_profile).grid(row=2, column=2, sticky="ew", padx=2)

        ttk.Button(self, text="Apply", command=self.apply_selected).grid(row=3, column=0, columnspan=3, sticky="ew", padx=2, pady=4)
        ttk.Button(self, text="Import CSV", command=self.import_csv).grid(row=4, column=0, columnspan=3, sticky="ew", padx=2)

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
        if self.selected_profile_index is None:
            return
        if messagebox.askyesno("Delete", "Delete selected profile?"):
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
        path = filedialog.askopenfilename(filetypes=[("CSV","*.csv")])
        if not path:
            return
        try:
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.profile_list.append(row)
            save_profiles(self.profile_list)
            self.refresh_list()
            messagebox.showinfo("Imported", f"Imported profiles from {path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

class ProfileDialog(tk.Toplevel):
    def __init__(self, master, title, data=None):
        super().__init__(master)
        self.master = master
        self.title(title)
        self.resizable(False, False)
        fields = ["ProfileName","IP","Subnet","Gateway","DNS1","DNS2"]
        self.vars = {f: tk.StringVar(value=data.get(f,"") if data else "") for f in fields}
        for i,f in enumerate(fields):
            tk.Label(self, text=f+":").grid(row=i, column=0, sticky="e")
            tk.Entry(self, textvariable=self.vars[f]).grid(row=i, column=1, padx=5, pady=2)
        ttk.Button(self, text="Save", command=self.save).grid(row=len(fields), column=0, columnspan=2, sticky="ew", pady=4)

    def save(self):
        profile = {k:v.get() for k,v in self.vars.items()}
        if not profile["ProfileName"]:
            messagebox.showerror("Required", "ProfileName is required")
            return
        if self.master.selected_profile_index is not None and self.title().startswith("Edit"):
            self.master.profile_list[self.master.selected_profile_index] = profile
        else:
            self.master.profile_list.append(profile)
        save_profiles(self.master.profile_list)
        self.master.refresh_list()
        self.destroy()

if __name__ == "__main__":
    App().mainloop()
