import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import os
import winreg

def _script_path():
    return Path(__file__).resolve().parent / "main.py"

def _pythonw_path():
    return sys.executable.replace("python.exe", "pythonw.exe")

def install_startup():
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    script = _script_path()
    pythonw = _pythonw_path()
    if not os.path.exists(pythonw):
        pythonw = sys.executable
    cmd = f'"{pythonw}" "{script}"'
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "WatchfulEye", 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)
        return True
    except WindowsError:
        return False

def uninstall_startup():
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, "WatchfulEye")
        winreg.CloseKey(key)
        return True
    except WindowsError:
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--uninstall":
        uninstall_startup()
        print("Removed from startup.")
    else:
        install_startup()
        print("Installed to startup (HKCU\\Run).")
