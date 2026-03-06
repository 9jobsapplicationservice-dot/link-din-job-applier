'''
Author:     Sai Vignesh Golla
LinkedIn:   https://www.linkedin.com/in/saivigneshgolla/

Copyright (C) 2024 Sai Vignesh Golla

License:    GNU Affero General Public License
            https://www.gnu.org/licenses/agpl-3.0.en.html
            
GitHub:     https://github.com/GodsScion/Auto_job_applier_linkedIn

Support me: https://github.com/sponsors/GodsScion

version:    26.01.20.5.08
'''

import os
import re
import shutil
import pathlib
import subprocess
from datetime import datetime
from random import randint

from modules.helpers import get_default_temp_profile, make_directories
from config.settings import run_in_background, stealth_mode, disable_extensions, safe_mode, file_name, failed_file_name, logs_folder_path, generated_resume_path
from config.questions import default_resume_path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import SessionNotCreatedException

from modules.helpers import find_default_profile_directory, critical_error_log, print_lg

if stealth_mode:
    import undetected_chromedriver as uc


def patch_uc_del() -> None:
    '''
    Guard UC destructor to avoid noisy WinError 6 on partially initialized instances.
    '''
    if not stealth_mode:
        return
    try:
        original_del = uc.Chrome.__del__

        def safe_del(self):
            try:
                original_del(self)
            except Exception:
                pass

        uc.Chrome.__del__ = safe_del
    except Exception:
        pass


def extract_browser_major_from_error(message: str) -> int | None:
    '''
    Extract local browser major version from Selenium mismatch message.
    Example: "Current browser version is 145.0.7632.117"
    '''
    match = re.search(r'Current browser version is\s+(\d+)', message, re.IGNORECASE)
    if not match:
        return None
    try:
        return int(match.group(1))
    except Exception:
        return None


def detect_local_chrome_version() -> str:
    '''
    Best-effort local Chrome version detection for diagnostics.
    '''
    if not stealth_mode:
        return "not-applicable (stealth_mode=False)"
    try:
        chrome_executable = uc.find_chrome_executable()
        if not chrome_executable:
            return "unknown (chrome executable not found)"
        process = subprocess.run(
            [chrome_executable, "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        version = (process.stdout or process.stderr or "").strip()
        return version if version else "unknown"
    except Exception as e:
        return f"unknown ({type(e).__name__})"


def detect_local_chrome_major() -> int | None:
    '''
    Parse the major version from local Chrome version output.
    '''
    version_text = detect_local_chrome_version()
    match = re.search(r'(\d+)\.', version_text)
    if not match:
        return None
    try:
        return int(match.group(1))
    except Exception:
        return None


def create_unique_temp_profile_path() -> str:
    '''
    Create a unique temp profile path per run to avoid DevTools/Singleton lock collisions.
    '''
    base_path = pathlib.Path(get_default_temp_profile())
    prune_old_temp_profiles(base_path, keep_latest=5)
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + f"-{randint(1000, 9999)}"
    return str(base_path / f"run-{run_id}")


def is_temp_profile_path(profile_path: str) -> bool:
    '''
    Check whether profile path is under our managed temp profile base path.
    '''
    try:
        base = pathlib.Path(get_default_temp_profile()).resolve()
        target = pathlib.Path(profile_path).resolve()
        return os.path.commonpath([str(base), str(target)]) == str(base)
    except Exception:
        return False


def cleanup_profile_locks(profile_path: str) -> None:
    '''
    Best-effort cleanup for stale lock/devtools files in managed temp profiles.
    '''
    if not is_temp_profile_path(profile_path):
        return
    transient_files = ["DevToolsActivePort", "SingletonLock", "SingletonCookie", "SingletonSocket"]
    for file_name in transient_files:
        try:
            file_path = pathlib.Path(profile_path) / file_name
            if file_path.exists():
                file_path.unlink()
        except Exception:
            pass


def prune_old_temp_profiles(base_path: pathlib.Path, keep_latest: int = 5) -> None:
    '''
    Keep only latest temp profile directories to avoid silent disk exhaustion.
    '''
    try:
        base_path.mkdir(parents=True, exist_ok=True)
        dirs = [p for p in base_path.iterdir() if p.is_dir() and p.name.startswith("run-")]
        dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        for stale_dir in dirs[keep_latest:]:
            try:
                shutil.rmtree(stale_dir, ignore_errors=True)
            except Exception:
                pass
    except Exception:
        pass


def build_options(use_uc: bool, profile_path: str, profile_label: str) -> Options:
    '''
    Build Chrome options with profile and startup-stability flags.
    '''
    options = uc.ChromeOptions() if use_uc else Options()

    if run_in_background:
        options.add_argument("--headless")
    if disable_extensions:
        options.add_argument("--disable-extensions")

    # Conservative startup flags for reliability.
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--remote-allow-origins=*")

    print_lg("IF YOU HAVE MORE THAN 10 TABS OPENED, PLEASE CLOSE OR BOOKMARK THEM! Or it's highly likely that application will just open browser and not do anything!")
    if profile_label == "guest":
        print_lg("Will login with a guest profile, browsing history will not be saved in the browser!")
    else:
        print_lg("Will login using existing Chrome profile directory.")
    print_lg(f"Using Chrome user-data-dir: {profile_path}")
    options.add_argument(f"--user-data-dir={profile_path}")

    return options


def create_uc_session(options: Options, forced_major: int | None = None):
    '''
    Create UC Chrome session, optionally forcing driver major.
    '''
    print_lg("Downloading Chrome Driver... This may take some time. Undetected mode requires download every run!")
    if forced_major:
        print_lg(f"Trying undetected-chromedriver with forced major {forced_major}.")
        return uc.Chrome(options=options, version_main=forced_major)
    return uc.Chrome(options=options)


def create_standard_session(options: Options):
    '''
    Create standard Selenium Chrome session.
    '''
    print_lg("Starting standard Selenium ChromeDriver session (fallback mode).")
    return webdriver.Chrome(options=options)


def createChromeSession(profile_path: str, profile_label: str, use_uc: bool = True, forced_major: int | None = None):
    '''
    Create chrome session with selected backend.
    '''
    make_directories([file_name, failed_file_name, logs_folder_path + "/screenshots", default_resume_path, generated_resume_path + "/temp"])
    make_directories([profile_path])
    cleanup_profile_locks(profile_path)

    options = build_options(use_uc, profile_path, profile_label)
    if use_uc:
        driver = create_uc_session(options, forced_major)
    else:
        driver = create_standard_session(options)

    driver.maximize_window()
    wait = WebDriverWait(driver, 5)
    actions = ActionChains(driver)
    return options, driver, actions, wait


def start_chrome_with_fallback():
    '''
    UC startup order:
    1) auto-major with normal profile policy
    2) forced major (from error/local detection) with same retry mode
    3) auto-major guest retry
    4) forced major guest retry
    5) fallback to standard Selenium ChromeDriver (guest retry)
    '''
    detected_version = detect_local_chrome_version() if stealth_mode else "not-applicable (stealth_mode=False)"
    detected_major = detect_local_chrome_major() if stealth_mode else None
    if stealth_mode:
        print_lg(f"Local Chrome detected: {detected_version}")

    if stealth_mode:
        last_uc_error = None
        default_profile_dir = find_default_profile_directory()
        use_default_profile = bool(default_profile_dir and not safe_mode)
        primary_profile_path = default_profile_dir if use_default_profile else create_unique_temp_profile_path()
        primary_profile_label = "default" if use_default_profile else "guest"
        attempts = [
            (primary_profile_path, primary_profile_label),
            (create_unique_temp_profile_path(), "guest"),
        ]
        forced_major = None

        for profile_path, profile_label in attempts:
            try:
                return createChromeSession(profile_path=profile_path, profile_label=profile_label, use_uc=True, forced_major=forced_major)
            except SessionNotCreatedException as e:
                last_uc_error = e
                error_text = str(e)
                parsed_major = extract_browser_major_from_error(error_text)
                if parsed_major:
                    forced_major = parsed_major
                elif detected_major:
                    forced_major = detected_major

                if forced_major:
                    try:
                        return createChromeSession(profile_path=profile_path, profile_label=profile_label, use_uc=True, forced_major=forced_major)
                    except Exception as forced_error:
                        last_uc_error = forced_error
                        print_lg(
                            f"UC forced-major attempt failed (profile={profile_label}, major={forced_major}). "
                            f"Reason: {forced_error}"
                        )
                else:
                    print_lg(f"UC auto attempt failed (profile={profile_label}). Reason: {e}")
            except Exception as e:
                last_uc_error = e
                print_lg(f"UC startup attempt failed (profile={profile_label}). Reason: {e}")

        print_lg("UC failed after retries; falling back to standard ChromeDriver.")
        if last_uc_error:
            critical_error_log("UC startup failure summary", last_uc_error)

        return createChromeSession(
            profile_path=create_unique_temp_profile_path(),
            profile_label="guest",
            use_uc=False
        )

    default_profile_dir = find_default_profile_directory()
    use_default_profile = bool(default_profile_dir and not safe_mode)
    profile_path = default_profile_dir if use_default_profile else create_unique_temp_profile_path()
    profile_label = "default" if use_default_profile else "guest"
    return createChromeSession(profile_path=profile_path, profile_label=profile_label, use_uc=False)


patch_uc_del()

try:
    options, driver, actions, wait = start_chrome_with_fallback()
except Exception as e:
    msg = 'Failed to start browser session. Please ensure Google Chrome is up to date and no stale background Chrome processes are blocking startup. If this persists, set stealth_mode = False in config/settings.py and retry.'
    print_lg(msg)
    critical_error_log("In Opening Chrome", e)
    from pyautogui import alert
    alert(msg, "Error in opening chrome")
    try:
        driver.quit()
    except Exception:
        pass
    exit()
