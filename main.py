import os
import sys
import json
import platform
import subprocess
from datetime import datetime
known_bad_list = {"com.fake.virus", "com.malware.sample"}


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


# note: getting device info for model, verse, security, manufacturer
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
        "ro.boot.flash.locked": "is_bootloader_locked",
        "ro.boot.verifiedbootstate": "boot_state",
        "ro.crypto.state": "storage_encryption",
        "ro.build.tags": "build_tags",
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


# note: usb debug checking
def check_usb_debugging(device_id):
    adb_path = get_adb_path()
    if not adb_path or not os.path.exists(adb_path):
        return ("ERROR", "'platform-tools' folder not found!\n"
                "Please download SDK PlatformTools and put in the repo folder")
    command_usbdebug = [adb_path, "-s", device_id, "shell", "settings", "get",
                        "global", "adb_enabled"]
    try:
        result_usbdebug = subprocess.run(command_usbdebug,
                                         capture_output=True, text=True)
    except FileNotFoundError:
        return ("ERROR", "NO Data")
    output_usbdebug = result_usbdebug.stdout.strip()
    if output_usbdebug == "1":
        return ("OK", True)
    elif output_usbdebug == "0":
        return ("OK", False)
    else:
        return ("ERROR", "Unexpected output")


# note: finding security patch within 3 to 6 months
def check_security_patch(device_info):
    patch_date_raw = device_info.get("security_patch")
    if patch_date_raw is None:
        return ("ERROR", "Security patch info not available")
    try:
        patch_date = datetime.fromisoformat(patch_date_raw)
    except ValueError:
        return ("ERROR", "Invalid patch date format")
    today = datetime.now()
    days_old = (today - patch_date).days
    if days_old <= 90:
        risk = "LOW"
    elif days_old <= 180:
        risk = "MEDIUM"
    else:
        risk = "HIGH"
    return ("OK", {"days_old": days_old, "risk": risk})


# note: check for unknow source apps in the phone
def check_unknown_sources(device_id, device_info):
    adb_path = get_adb_path()
    if not adb_path or not os.path.exists(adb_path):
        return ("ERROR", "'platform-tools' folder not found!\n"
                "Please download SDK PlatformTools and put in the repo folder")
# --- get raw version and convert to integer
    raw_version = device_info.get("android_version")
    if raw_version is None:
        return ("ERROR", "Android version unknown.")
    android_version = int(raw_version)
# --- checking under version 8 (different method to finding out)
    if android_version < 8:
        command_findsource = [adb_path, "-s", device_id, "shell",
                              "settings", "get",
                              "secure", "install_non_market_apps"]
        try:
            result_source = subprocess.run(command_findsource,
                                           capture_output=True, text=True)
        except FileNotFoundError:
            return ("ERROR", "No data")
        output_source = result_source.stdout.strip()
        return ("OK", output_source == "1")
    else:
        command_findpackage = [adb_path, "-s", device_id, "shell",
                               "dumpsys", "package", "|", "grep",
                               "REQUESTED_INSTALL_PACKAGES"]
        try:
            result_package = subprocess.run(command_findpackage,
                                            capture_output=True, text=True)
        except FileNotFoundError:
            return ("ERROR", "No data")
        output_package = result_package.stdout
        permission_package = "REQUESTED_INSTALL_PACKAGES" in output_package
        return ("OK", permission_package)


def check_sideloaded_app(device_id):
    adb_path = get_adb_path()
    if not adb_path or not os.path.exists(adb_path):
        return ("ERROR", "'platform-tools' folder not found!\n"
                "Please download SDK PlatformTools and put in the repo folder")
    command_installpackage = [adb_path, "-s", device_id, "shell",
                              "pm", "list", "packages", "-3"]
    try:
        result_installpackage = subprocess.run(command_installpackage,
                                               capture_output=True, text=True)
    except FileNotFoundError:
        return ("ERROR", "No data")
    output_installpackage = result_installpackage.stdout.strip().splitlines()
    package_list = [line.replace("Package:", "")
                    for line in output_installpackage if line.strip()]
    flagged_apps = []
    for package_name in package_list:
        command_dumpsys = [adb_path, "-s", device_id, "shell",
                           "dumpsys", "package", package_name]
        try:
            result_dumpsys = subprocess.run(command_dumpsys,
                                            capture_output=True, text=True)
        except FileNotFoundError:
            continue
        output = result_dumpsys.stdout
        installer = None
        for line in output.splitlines():
            if "installerPackageName=" in line:
                installer = line.split("=", 1)[1].strip()
                break
        is_sideloaded = (installer is None or installer == "null"
                         or installer == "")
        is_known_bad = package_name in known_bad_list
        if is_sideloaded or is_known_bad:
            flagged_apps.append({
                "package": package_name,
                "installer": installer,
                "sideloaded": is_sideloaded,
                "known_bad": is_known_bad
            })
    return ("OK", flagged_apps)


def check_root_status(device_id, device_info):
    adb_path = get_adb_path()
    if not adb_path or not os.path.exists(adb_path):
        return ("ERROR", "'platform-tools' folder not found!\n"
                "Please download SDK PlatformTools and put in the repo folder")
    signals = []
    build_tags = device_info.get("build_tags", "")
    if "test-keys" in build_tags:
        signals.append("build_tags")
    command_checksu = [adb_path, "-s", device_id, "shell",
                       "which", "su"]
    try:
        result_checksu = subprocess.run(command_checksu,
                                        capture_output=True, text=True)
    except FileNotFoundError:
        return ("ERROR", "No data")
    if result_checksu.stdout.strip():
        signals.append("su_binary_found")
    command_checkexecsu = [adb_path, "-s", device_id, "shell",
                           "su", "-c", "id"]
    try:
        result_checkexecsu = subprocess.run(command_checkexecsu,
                                            capture_output=True, text=True)
    except FileNotFoundError:
        return ("ERROR", "No data")
    if result_checkexecsu.returncode == 0:
        signals.append("su_executeable")
    is_rooted = len(signals) > 0
    return ("OK", {"rooted": is_rooted, "signals": signals})


def calculate_score(usb_result, patch_result, unknown_src_result,
                    sideload_result, root_result):
    score = 100
    deductions = []
    # USB DEBUGGING
    status, is_usb_on = usb_result
    if status == "OK" and is_usb_on:
        score -= 15
        deductions.append("USB debugging enabled (-15)")
    # SECURITY PATCH AGE
    status, patch_data = patch_result
    if status == "OK":
        if patch_data["risk"] == "MEDIUM":
            score -= 10
            deductions.append("Security patch outdated - medium risk (-10)")
        elif patch_data["risk"] == "HIGH":
            score -= 25
            deductions.append("Security patch outdated - high risk (-25)")
    # UNKNOWN SOURCES
    status, unknown_data = unknown_src_result
    if status == "OK" and unknown_data:
        score -= 15
        deductions.append("Unknown sources or sideload "
                          "permission enabled (-15)")
    # SIDELOADED APPS FLAGGED
    status, flagged_list = sideload_result
    if status == "OK" and len(flagged_list) > 0:
        known_bad_count = 0
        for app in flagged_list:
            if app["known_bad"]:
                known_bad_count += 1
        if known_bad_count > 0:
            score -= 30
            deductions.append("Known-bad app detected (-30)")
        else:
            score -= 10
            deductions.append("Sideloaded apps present (-10)")
    # ROOT STATUS
    status, root_data = root_result
    if status == "OK" and root_data["rooted"]:
        score -= 20
        deductions.append("Device rooted (-20)")
    score = max(score, 0)
    return ("OK", {"score": score, "deductions": deductions})


def generate_report(device_info, score_result):
    score = score_result["score"]
    deductions = score_result["deductions"]

    report_lines = []
    report_lines.append("=" * 40)
    report_lines.append("MOBILE SECURITY CHECK REPORT")
    report_lines.append("=" * 40)
    report_lines.append(f"Model: {device_info.get('model', 'N/A')}")
    report_lines.append(f"Manufacturer: {device_info.get('manufacturer',
                                                         'N/A')}")
    report_lines.append(f"Android Version: {device_info.get('android_version',
                                                            'N/A')}")
    report_lines.append("-" * 40)
    report_lines.append(f"SECURITY SCORE: {score}/100")
    report_lines.append("-" * 40)
    if not deductions:
        report_lines.append("No issues found. Device looks good!")
    else:
        report_lines.append("Issues found:")
        for item in deductions:
            report_lines.append(f" - {item}")
    report_lines.append("=" * 40)
    full_report = "\n".join(report_lines)
    with open("report.txt", "w") as f:
        f.write(full_report)
    return ("OK", full_report)


def main():
    status, data = check_adb_connection()
    if status == "ERROR":
        print(data)
        sys.exit()
    device_id = data
    status, device_info = get_device_info(device_id)
    if status == "ERROR":
        print(device_info)
        sys.exit()
    print(json.dumps(device_info, indent=2))
    print(check_usb_debugging(device_id))
    print(check_security_patch(device_info))
    print(check_unknown_sources(device_id, device_info))
    status, flagged = check_sideloaded_app(device_id)
    print(json.dumps(flagged, indent=2))
    print(check_root_status(device_id, device_info))


if __name__ == "__main__":
    main()
