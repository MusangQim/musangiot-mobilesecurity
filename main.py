import os
import platform
import subprocess


# note: using adb.exe by auto locating the file after put folder in the repo
def get_adb_path():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    system_os = platform.system().lower()
    if system_os == "windows":
        adb_path = os.path.join(current_dir, "platform-tools", "adb.exe")
    elif system_os in ["darwin", "linux"]:
        adb_path = os.path.join(current_dir, "platform-tools", "adb")
    else:
        return None
    if system_os in ["darwin", "linux"] and os.path.exists(adb_path):
        try:
            subprocess.run(["chmod", "+x", adb_path], check=True)
        except Exception:
            pass

    return adb_path


# note: using tuple to standardize into (status, data)
def check_adb_connection():
    adb_path = get_adb_path()
    if not adb_path or not os.path.exists(adb_path):
        return ("ERROR", "'platform-tools' folder not found!\n"
                "Please download SDK PlatformTools and put in the repo folder")
    try:
        result = subprocess.run([adb_path, "devices"],
                                capture_output=True, text=True)
    except FileNotFoundError:
        return ("ERROR", "ADB binary corrupt or not executable")
    except Exception as e:
        return ("ERROR", f"Unexpected failure running ADB: {e}")
    lines = result.stdout.strip().splitlines()
    device_lines = [line.strip() for line in lines[1:]
                    if line.strip() and not line.startswith("*")]
# --- connection phone ---
    if len(device_lines) == 0:
        return ("ERROR", "No phone connected!")
    if len(device_lines) > 1:
        return ("ERROR", "Many device connected, specify one")
    try:
        device_id, status = device_lines[0].split()
    except ValueError:
        return ("ERROR", "Invalid ADB output format!")
# --- authorization and status ---
    if status == "unauthorized":
        return ("ERROR", "Phone unauthorize - check phone screen "
                "for allow prompt")
    if status != "device":
        return ("ERROR", f"Unknown device status: {status}")
    return ("OK", device_id)


def get_device_info(device_id):
    adb_path = get_adb_path()
    if not adb_path or not os.path.exists(adb_path):
        return ("ERROR", "'platform-tools' folder not found!\n"
                "Please download SDK PlatformTools and put in the repo folder")
# --- specific target ---
    target_keys = {
        "ro.product.model": "model",
        "ro.build.version.release": "android_version",
        "ro.build.version.security_patch": "security_patch",
        "ro.product.manufacturer": "manufacturer",
    }
# --- find getprop
    command = [adb_path, "-s", device_id, "shell", "getprop"]
    try:
        result = subprocess.run(command, capture_output=True, text=True)
    except FileNotFoundError:
        return ("ERROR", "No data")
    lines_info = result.stdout.strip().splitlines()
    device_info = {}
    for line in lines_info:
        if ": " in line:
            key_raw, val_raw = line.split(": ", 1)
            key = key_raw.strip("[]")
            val = val_raw.strip("[]")
            if key in target_keys:
                readable_name = target_keys[key]
                device_info[readable_name] = val
    return ("OK", device_info)


if __name__ == "__main__":
    status, data = check_adb_connection()
    print(f"[{status}] {data}")
