# Network Profile Switcher

A lightweight Tkinter GUI for saving and applying multiple IP / subnet / gateway
profiles on Windows or macOS. Profiles live in `profiles.json` and can be bulk‑imported
from a CSV.

## Quick start
```bash
pip install -r requirements.txt
python network_profile_switcher.py
```

## Build binaries
Tag a commit to trigger GitHub Actions and get platform executables.

```bash
git tag -a v1.0.0 -m "First packaged release"
git push origin v1.0.0
```
