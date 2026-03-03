'''
Author:     Sai Vignesh Golla
LinkedIn:   https://www.linkedin.com/in/saivigneshgolla/

Modified by: Mayank Sodhi (Human delay added)

version:    26.01.20.5.08
'''

# Imports
import os
import sys
import json
import pathlib

from time import sleep
from random import randint, uniform
from datetime import datetime, timedelta
from pyautogui import alert
from pprint import pprint

from config.settings import logs_folder_path


###############################################################
# ✅ NEW HUMAN WAIT FUNCTION (MAIN ADDITION)
###############################################################

def step_wait(base: float = 1.2, jitter: float = 0.6, reason: str = "") -> None:
    """
    Human-like delay
    default: 1.2 sec (+/- 0.6 sec)
    So total wait: ~0.6 to 1.8 sec
    """
    try:
        wait_time = uniform(max(0, base - jitter), base + jitter)

        if reason:
            print_lg(f"[WAITING {round(wait_time,2)} sec] : {reason}")
        else:
            print_lg(f"[WAITING {round(wait_time,2)} sec]")

        sleep(wait_time)

    except Exception:
        sleep(base)


###############################################################
# ✅ SAFE CLICK FUNCTION (USE THIS EVERYWHERE)
###############################################################

def safe_click(
    element,
    base: float = 1.2,
    jitter: float = 0.6,
    reason: str = "Clicking button"
) -> None:
    """
    Click with human delay
    """
    step_wait(base, jitter, reason)
    element.click()


###############################################################
#### Common functions ####
###############################################################

#< Directories related
def make_directories(paths: list[str]) -> None:
    '''
    Function to create missing directories
    '''
    for path in paths:
        path = os.path.expanduser(path)  # Expands ~ to user's home directory
        path = path.replace("//", "/")

        # If path looks like a file path, get the directory part
        if '.' in os.path.basename(path):
            path = os.path.dirname(path)

        if not path:  # Handle cases where path is empty after dirname
            continue

        try:
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)  # exist_ok=True avoids race condition
        except Exception as e:
            print(f'Error while creating directory "{path}": ', e)


def get_default_temp_profile() -> str:
    home = pathlib.Path.home()
    if sys.platform.startswith('win'):
        return r"C:\temp\auto-job-apply-profile"
    elif sys.platform.startswith('linux'):
        return str(home / ".auto-job-apply-profile")
    return str(home / "Library" / "Application Support" / "Google" / "Chrome" / "auto-job-apply-profile")


def find_default_profile_directory() -> str | None:
    '''
    Dynamically finds the default Google Chrome 'User Data' directory path
    across Windows, macOS, and Linux, regardless of OS version.

    Returns the absolute path as a string, or None if the path is not found.
    '''
    home = pathlib.Path.home()

    # Windows
    if sys.platform.startswith('win'):
        paths = [
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data"),
            os.path.expandvars(r"%USERPROFILE%\AppData\Local\Google\Chrome\User Data"),
            os.path.expandvars(r"%USERPROFILE%\Local Settings\Application Data\Google\Chrome\User Data")
        ]
    # Linux
    elif sys.platform.startswith('linux'):
        paths = [
            str(home / ".config" / "google-chrome"),
            str(home / ".var" / "app" / "com.google.Chrome" / "data" / ".config" / "google-chrome"),
        ]
    else:
        return None

    # Check each potential path and return the first one that exists
    for path_str in paths:
        if os.path.exists(path_str):
            return path_str

    return None
#>


#< Logging related
def get_log_path():
    '''
    Function to replace '//' with '/' for logs path
    '''
    try:
        path = logs_folder_path + "/log.txt"
        return path.replace("//", "/")
    except Exception:
        return "logs/log.txt"


__logs_file_path = get_log_path()


def print_lg(*msgs: str | dict, end: str = "\n", pretty: bool = False, flush: bool = False, from_critical: bool = False) -> None:
    '''
    Function to log and print. **Note that, `end` and `flush` parameters are ignored if `pretty = True`**
    '''
    try:
        for message in msgs:
            pprint(message) if pretty else print(message, end=end, flush=flush)
            with open(__logs_file_path, 'a+', encoding="utf-8") as file:
                file.write(str(message) + end)
    except Exception as e:
        trail = f'Skipped saving this message: "{message}" to log.txt!' if from_critical else "We'll try one more time to log..."
        alert(f"log.txt in {logs_folder_path} is open or is occupied by another program! Please close it! {trail}", "Failed Logging")
        if not from_critical:
            critical_error_log("Log.txt is open or is occupied by another program!", e)


def critical_error_log(possible_reason: str, stack_trace: Exception) -> None:
    '''
    Function to log and print critical errors along with datetime stamp
    (Required by modules/open_chrome.py)
    '''
    try:
        print_lg(possible_reason, stack_trace, datetime.now(), from_critical=True)
    except Exception:
        # Fallback: never crash while logging a critical error
        print(possible_reason)
        print(stack_trace)
        print(datetime.now())
#>


def buffer(speed: int = 0) -> None:
    '''
    Function to wait within a period of selected random range.
    * Will not wait if input `speed <= 0`
    * Will wait within a random range of
      - `0.6 to 1.0 secs` if `1 <= speed < 2`
      - `1.0 to 1.8 secs` if `2 <= speed < 3`
      - `1.8 to speed secs` if `3 <= speed`
    '''
    if speed <= 0:
        return
    elif speed < 2:
        return sleep(randint(6, 10) * 0.1)
    elif speed < 3:
        return sleep(randint(10, 18) * 0.1)
    else:
        return sleep(randint(18, round(speed) * 10) * 0.1)


def manual_login_retry(is_logged_in: callable, limit: int = 2) -> None:
    '''
    Function to ask and validate manual login
    '''
    count = 0
    while not is_logged_in():
        print_lg("Seems like you're not logged in!")
        button = "Confirm Login"
        message = 'After you successfully Log In, please click "{}" button below.'.format(button)
        if count > limit:
            button = "Skip Confirmation"
            message = 'If you\'re seeing this message even after you logged in, Click "{}". Seems like auto login confirmation failed!'.format(button)
        count += 1
        if alert(message, "Login Required", button) and count > limit:
            return


def calculate_date_posted(time_string: str) -> datetime | None | ValueError:
    '''
    Function to calculate date posted from string.
    Returns datetime object | None if unable to calculate | ValueError if time_string is invalid
    '''
    import re
    time_string = time_string.strip()
    now = datetime.now()

    match = re.search(r'(\d+)\s+(second|minute|hour|day|week|month|year)s?\s+ago', time_string, re.IGNORECASE)

    if match:
        try:
            value = int(match.group(1))
            unit = match.group(2).lower()

            if 'second' in unit:
                return now - timedelta(seconds=value)
            elif 'minute' in unit:
                return now - timedelta(minutes=value)
            elif 'hour' in unit:
                return now - timedelta(hours=value)
            elif 'day' in unit:
                return now - timedelta(days=value)
            elif 'week' in unit:
                return now - timedelta(weeks=value)
            elif 'month' in unit:
                return now - timedelta(days=value * 30)  # Approximation
            elif 'year' in unit:
                return now - timedelta(days=value * 365)  # Approximation
        except (ValueError, IndexError):
            pass

    return None


def convert_to_json(data) -> dict:
    '''
    Function to convert data to JSON, if unsuccessful, returns error dict
    '''
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return {"error": "Unable to parse the response as JSON", "data": data}


def truncate_for_csv(data, max_length: int = 131000, suffix: str = "...[TRUNCATED]") -> str:
    """
    CSV field size limit errors avoid karne ke liye long text truncate karta hai.
    """
    try:
        str_data = str(data) if data is not None else ""
        if len(str_data) <= max_length:
            return str_data
        return str_data[:max_length - len(suffix)] + suffix
    except Exception as e:
        return f"[ERROR CONVERTING DATA: {e}]"
