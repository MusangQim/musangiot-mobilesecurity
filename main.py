import subprocess


def check_adb_connection():
    result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
    lines = result.stdout.strip().splitlines()
    device_lines = lines[1:]
    if len(device_lines) == 0:
        return "No Phone Connected!!"
    if len(device_lines) == 1:
        device_id, status = device_lines[0].split("\t")
        if status == "unauthorized":
            return "Phone Unauthorize!!"
        if status == "device":
            return device_id, "OK"

    return "--Many Device Connected, Specify One Device Please--"


if __name__ == "__main__":
    print(check_adb_connection())
