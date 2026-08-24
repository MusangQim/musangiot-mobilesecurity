import os
import platform
import subprocess


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


def check_adb_connection():
    adb_path = get_adb_path()
    if not adb_path or not os.path.exists(adb_path):
        return ("Error: 'platform-tools' folder not found!\n"
                "Please download SDK PlatformTools and put in the repo folder")
    try:
        result = subprocess.run([adb_path, "devices"],
                                capture_output=True, text=True)
    except subprocess.CalledProcessError:
        return "Error: Failed to execute ADB Command!"
    lines = result.stdout.strip().splitlines()
    device_lines = [line.strip() for line in lines[1:]
                    if line.strip() and not line.startswith("*")]
    if len(device_lines) == 0:
        return "No Phone Connected!!"
    if len(device_lines) == 1:
        try:
            device_id, status = device_lines[0].split()
            if status == "unauthorized":
                return "Phone Unauthorize!!"
            if status == "device":
                return device_id, "OK"
            return f"Unknown Device Status: {status}"
        except ValueError:
            return "Invalid ADB Output Format!!"

    return "--Many Device Connected, Specify One Device Please--"


if __name__ == "__main__":
    print(check_adb_connection())
