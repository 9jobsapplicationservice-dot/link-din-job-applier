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


# Imports
import os
import csv
import re
import time
import pyautogui
from urllib.parse import quote_plus, urlparse
from modules.helpers import safe_click

# Set CSV field size limit to prevent field size errors
csv.field_size_limit(1000000)  # Set to 1MB instead of default 131KB

from random import choice, shuffle, randint
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.select import Select
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, NoSuchWindowException, ElementNotInteractableException, WebDriverException, StaleElementReferenceException

from config.personals import *
from config.questions import *
from config.search import *
from config.secrets import use_AI, username, password, ai_provider
from config.settings import *

from modules.open_chrome import *
import modules.open_chrome as open_chrome_module
from modules.helpers import *
from modules.clickers_and_finders import *
from modules.validator import validate_config
from modules.portals import ExternalApplyOutcome, detect_portal_adapter
from modules.portals.common_fields import build_profile

if use_AI:
    from modules.ai.openaiConnections import ai_create_openai_client, ai_extract_skills, ai_answer_question, ai_close_openai_client
    from modules.ai.deepseekConnections import deepseek_create_client, deepseek_extract_skills, deepseek_answer_question
    from modules.ai.geminiConnections import gemini_create_client, gemini_extract_skills, gemini_answer_question

from typing import Literal


pyautogui.FAILSAFE = False
# if use_resume_generator:    from resume_generator import is_logged_in_GPT, login_GPT, open_resume_chat, create_custom_resume


#< Global Variables and logics

if run_in_background == True:
    pause_at_failed_question = False
    pause_before_submit = False
    run_non_stop = False

first_name = first_name.strip()
middle_name = middle_name.strip()
last_name = last_name.strip()
full_name = first_name + " " + middle_name + " " + last_name if middle_name else first_name + " " + last_name

useNewResume = True
randomly_answered_questions = set()

tabs_count = 1
easy_applied_count = 0
external_jobs_count = 0
failed_count = 0
skip_count = 0
dailyEasyApplyLimitReached = False

re_experience = re.compile(r'[(]?\s*(\d+)\s*[)]?\s*[-to]*\s*\d*[+]*\s*year[s]?', re.IGNORECASE)

desired_salary_lakhs = str(round(desired_salary / 100000, 2))
desired_salary_monthly = str(round(desired_salary/12, 2))
desired_salary = str(desired_salary)

current_ctc_lakhs = str(round(current_ctc / 100000, 2))
current_ctc_monthly = str(round(current_ctc/12, 2))
current_ctc = str(current_ctc)

notice_period_months = str(notice_period//30)
notice_period_weeks = str(notice_period//7)
notice_period = str(notice_period)

aiClient = None
##> ------ Dheeraj Deshwal : dheeraj9811 Email:dheeraj20194@iiitd.ac.in/dheerajdeshwal9811@gmail.com - Feature ------
about_company_for_ai = None # TODO extract about company for AI
##<

#>


#< Login Functions
def is_logged_in_LN() -> bool:
    '''
    Function to check if user is logged-in in LinkedIn
    * Returns: `True` if user is logged-in or `False` if not
    '''
    if driver.current_url == "https://www.linkedin.com/feed/": return True
    if try_linkText(driver, "Sign in"): return False
    if try_xp(driver, '//button[@type="submit" and contains(text(), "Sign in")]'):  return False
    if try_linkText(driver, "Join now"): return False
    print_lg("Didn't find Sign in link, so assuming user is logged in!")
    return True


def login_LN() -> None:
    '''
    Function to login for LinkedIn
    * Tries to login using given `username` and `password` from `secrets.py`
    * If failed, tries to login using saved LinkedIn profile button if available
    * If both failed, asks user to login manually
    '''
    # Find the username and password fields and fill them with user credentials
    driver.get("https://www.linkedin.com/login")
    if username == "username@example.com" and password == "example_password":
        pyautogui.alert("User did not configure username and password in secrets.py, hence can't login automatically! Please login manually!", "Login Manually","Okay")
        print_lg("User did not configure username and password in secrets.py, hence can't login automatically! Please login manually!")
        manual_login_retry(is_logged_in_LN, 2)
        return
    try:
        wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Forgot password?")))
        try:
            text_input_by_ID(driver, "username", username, 1)
        except Exception as e:
            print_lg("Couldn't find username field.")
            # print_lg(e)
        try:
            text_input_by_ID(driver, "password", password, 1)
        except Exception as e:
            print_lg("Couldn't find password field.")
            # print_lg(e)
        # Find the login submit button and click it
        driver.find_element(By.XPATH, '//button[@type="submit" and contains(text(), "Sign in")]').click()
    except Exception as e1:
        try:
            profile_button = find_by_class(driver, "profile__details")
            safe_click(profile_button, reason="profile_button")
        except Exception as e2:
            # print_lg(e1, e2)
            print_lg("Couldn't Login!")

    try:
        # Wait until successful redirect, indicating successful login
        wait.until(EC.url_to_be("https://www.linkedin.com/feed/")) # wait.until(EC.presence_of_element_located((By.XPATH, '//button[normalize-space(.)="Start a post"]')))
        return print_lg("Login successful!")
    except Exception as e:
        print_lg("Seems like login attempt failed! Possibly due to wrong credentials or already logged in! Try logging in manually!")
        # print_lg(e)
        manual_login_retry(is_logged_in_LN, 2)
#>



def get_applied_job_ids() -> set[str]:
    '''
    Function to get a `set` of applied job's Job IDs
    * Returns a set of Job IDs from existing applied jobs history csv file
    '''
    job_ids: set[str] = set()
    try:
        with open(file_name, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                job_ids.add(row[0])
    except FileNotFoundError:
        print_lg(f"The CSV file '{file_name}' does not exist.")
    return job_ids



def find_first_by_xpaths(xpaths: list[str], timeout: float = 3.0) -> WebElement | None:
    '''
    Return the first element found from given XPaths, else `None`.
    '''
    for xpath in xpaths:
        try:
            return WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
        except Exception:
            continue
    return None


def click_first_by_xpaths(xpaths: list[str], reason: str, timeout: float = 3.0, root: WebDriver | WebElement | None = None) -> bool:
    '''
    Try clicking the first clickable element matching any xpath.
    '''
    search_root = root if root is not None else driver
    for xpath in xpaths:
        try:
            if search_root == driver:
                element = WebDriverWait(driver, timeout).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
            else:
                end_time = time.time() + timeout
                element = None
                while time.time() < end_time:
                    try:
                        candidate = search_root.find_element(By.XPATH, xpath)
                        if candidate.is_displayed() and candidate.is_enabled():
                            element = candidate
                            break
                    except Exception:
                        pass
                    sleep(0.2)
                if element is None:
                    raise Exception(f"Not clickable in root for xpath: {xpath}")
            safe_click(element, reason=reason)
            return True
        except Exception:
            continue
    return False


def wait_multi_select(driver: WebDriver, texts: list[str], actions: ActionChains = None, timeout: float = 3.0) -> None:
    '''
    Wait-aware multi-select helper for dynamic filter options.
    '''
    for text in texts:
        lower_text = text.lower()
        option_xpaths = [
            f'.//span[normalize-space(.)="{text}"]',
            f'.//*[self::span or self::label or self::button][normalize-space(.)="{text}"]',
            f'.//*[self::span or self::label or self::button][contains(translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "{lower_text}")]',
        ]
        clicked = click_first_by_xpaths(option_xpaths, reason=f"wait_multi_select:{text}", timeout=timeout)
        if not clicked:
            if actions:
                company_search_click(driver, actions, text)
            else:
                print_lg(f"Click Failed! Didn't find '{text}'")


def normalize_hr_value(value: str | None) -> str:
    '''
    Normalize HR text values for CSV output.
    '''
    normalized = str(value).strip() if value is not None else ""
    return normalized if normalized else "Unknown"


def is_valid_http_url(url: str | None) -> bool:
    '''
    Returns True only for valid absolute http(s) URLs.
    '''
    if not url:
        return False
    candidate = str(url).strip()
    if not candidate or candidate.lower() == "unknown":
        return False
    try:
        parsed = urlparse(candidate)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except Exception:
        return False


def is_valid_linkedin_person_url(url: str | None) -> bool:
    '''
    Returns True only for LinkedIn person profile URLs (/in/...), not company/school pages.
    '''
    return normalize_linkedin_person_url(url) != "Unknown"


def normalize_linkedin_person_url(url: str | None) -> str:
    '''
    Convert LinkedIn profile links to canonical absolute form and reject non-person URLs.
    '''
    if not url:
        return "Unknown"
    candidate = str(url).strip()
    if not candidate or candidate.lower() == "unknown":
        return "Unknown"
    if candidate.startswith("/in/"):
        candidate = "https://www.linkedin.com" + candidate
    if candidate.startswith("www.linkedin.com/in/"):
        candidate = "https://" + candidate
    if not is_valid_http_url(candidate):
        return "Unknown"
    try:
        parsed = urlparse(candidate)
        netloc = (parsed.netloc or "").lower()
        path = (parsed.path or "").strip()
        if "linkedin.com" not in netloc:
            return "Unknown"
        if not path.lower().startswith("/in/"):
            return "Unknown"
        normalized_path = path.rstrip("/")
        return f"{parsed.scheme}://{parsed.netloc}{normalized_path}"
    except Exception:
        return "Unknown"


def is_probable_person_name(name: str | None) -> bool:
    '''
    Basic guard to reject non-person labels like employee counts and generic CTA words.
    '''
    cleaned = normalize_hr_value(name)
    if cleaned == "Unknown":
        return False
    lowered = cleaned.lower()
    blocked_tokens = {
        "employees",
        "employee",
        "followers",
        "connections",
        "hiring team",
        "message",
        "connect",
        "follow",
        "view profile",
        "company",
    }
    if any(token in lowered for token in blocked_tokens):
        return False
    if re.search(r"\b\d+\s*-\s*\d+\b", lowered):
        return False
    alpha_count = sum(1 for c in cleaned if c.isalpha())
    if alpha_count < 3:
        return False
    return True


def infer_name_from_linkedin_url(url: str | None) -> str:
    '''
    Best-effort person name from LinkedIn /in/ URL slug when visible name is missing.
    '''
    normalized = normalize_linkedin_person_url(url)
    if normalized == "Unknown":
        return "Unknown"
    try:
        slug = normalized.split("/in/", 1)[1].strip("/")
        slug = re.sub(r"[-_]+", " ", slug)
        slug = re.sub(r"\d+", "", slug).strip()
        if not slug:
            return "Unknown"
        inferred = " ".join(part.capitalize() for part in slug.split() if part)
        return inferred if is_probable_person_name(inferred) else "Unknown"
    except Exception:
        return "Unknown"


def extract_hr_info() -> tuple[str, str]:
    '''
    Extract HR name/link from available recruiter/hiring cards with fallbacks.
    '''
    card_xpaths = [
        '//div[contains(@class, "hirer-card__hirer-information")]',
        '//div[contains(@class, "hirer-card")]',
        '//section[contains(@class, "jobs-poster")]',
        '//section[contains(@class, "jobs-company")]',
    ]
    seen_cards: set[str] = set()
    candidate_cards: list[WebElement] = []

    for xpath in card_xpaths:
        try:
            for card in driver.find_elements(By.XPATH, xpath):
                key = card.get_attribute("outerHTML")
                if key and key not in seen_cards:
                    seen_cards.add(key)
                    candidate_cards.append(card)
        except Exception:
            continue

    for card in candidate_cards:
        hr_link = "Unknown"
        hr_name = "Unknown"

        try:
            link_element = None
            prioritized_link_xpaths = [
                './/a[contains(@href, "/in/")]',
                './/a[contains(@href, "linkedin.com/in/")]',
            ]
            for link_xpath in prioritized_link_xpaths:
                found = card.find_elements(By.XPATH, link_xpath)
                if found:
                    link_element = found[0]
                    break

            if link_element is not None:
                raw_link = (link_element.get_attribute("href") or "").strip()
                normalized_link = normalize_linkedin_person_url(raw_link)
                if normalized_link != "Unknown":
                    hr_link = normalized_link

                for text_candidate in [
                    link_element.text,
                    link_element.get_attribute("aria-label"),
                ]:
                    normalized = normalize_hr_value(text_candidate)
                    if is_probable_person_name(normalized):
                        hr_name = normalized
                        break

            if hr_name == "Unknown" and hr_link != "Unknown":
                name_candidates = card.find_elements(
                    By.XPATH,
                    './/span[normalize-space()] | .//h3[normalize-space()] | .//strong[normalize-space()]',
                )
                for elem in name_candidates:
                    text = normalize_hr_value(elem.text)
                    if not is_probable_person_name(text):
                        continue
                    hr_name = text
                    break
        except Exception:
            continue

        hr_name = normalize_hr_value(hr_name)
        hr_link = normalize_hr_value(hr_link)
        if is_valid_linkedin_person_url(hr_link):
            if not is_probable_person_name(hr_name):
                hr_name = infer_name_from_linkedin_url(hr_link)
            return hr_name, hr_link

    # Fallback: scan visible job detail area for any LinkedIn person profile link.
    fallback_link_xpaths = [
        '//div[contains(@class,"jobs-unified-top-card")]//a[contains(@href,"/in/")]',
        '//section[contains(@class,"jobs-poster")]//a[contains(@href,"/in/")]',
        '//main//a[contains(@href,"/in/")]',
        '//a[contains(@href,"linkedin.com/in/")]',
    ]
    seen_links: set[str] = set()
    for xpath in fallback_link_xpaths:
        try:
            anchors = driver.find_elements(By.XPATH, xpath)
        except Exception:
            continue
        for anchor in anchors:
            try:
                normalized_link = normalize_linkedin_person_url(anchor.get_attribute("href"))
                if normalized_link == "Unknown" or normalized_link in seen_links:
                    continue
                seen_links.add(normalized_link)
                candidate_names = [
                    normalize_hr_value(anchor.text),
                    normalize_hr_value(anchor.get_attribute("aria-label")),
                    infer_name_from_linkedin_url(normalized_link),
                ]
                hr_name = "Unknown"
                for candidate_name in candidate_names:
                    if is_probable_person_name(candidate_name):
                        hr_name = candidate_name
                        break
                if hr_name != "Unknown":
                    return hr_name, normalized_link
            except Exception:
                continue

    print_lg("HR extraction fallback did not find any usable LinkedIn person profile link.")

    return "Unknown", "Unknown"


def is_filter_selected(text: str) -> bool:
    '''
    Checks if a filter chip/toggle is already selected.
    '''
    if not text:
        return False
    lower_text = text.lower()
    checks = [
        f'//button[contains(translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "{lower_text}") and (contains(@class, "selected") or @aria-pressed="true" or @aria-checked="true")]',
        f'//label[contains(translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "{lower_text}") and contains(@class, "selected")]',
    ]
    for xp in checks:
        try:
            selected = driver.find_element(By.XPATH, xp)
            if selected and selected.is_displayed():
                return True
        except Exception:
            pass
    return False


def has_easy_apply_button(context: WebDriver | WebElement = driver) -> bool:
    '''
    Checks if currently selected job has Easy Apply CTA visible.
    '''
    xpaths = [
        './/button[contains(@class,"jobs-apply-button") and contains(translate(@aria-label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "easy")]',
        './/button[contains(@class,"jobs-apply-button") and contains(translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "easy apply")]',
        './/button[.//span[contains(translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "easy apply")]]',
    ]
    for xp in xpaths:
        try:
            btn = context.find_element(By.XPATH, xp)
            if btn and btn.is_displayed():
                return True
        except Exception:
            pass
    return False


def ensure_easy_apply_filter() -> bool:
    '''
    Ensures Easy Apply filter is enabled across LinkedIn UI variants.
    '''
    if is_filter_selected("easy apply"):
        return True

    # Variant 1: top chip button
    if click_first_by_xpaths([
        '//button[contains(translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "easy apply")]',
        '//button[contains(translate(@aria-label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "easy apply")]',
    ], reason="easy_apply_chip", timeout=3):
        return True

    # Variant 2: boolean switch in filter modal
    boolean_button_click(driver, actions, "Easy Apply")
    return is_filter_selected("easy apply")


def set_search_location() -> bool:
    '''
    Function to set search location
    '''
    if not search_location.strip():
        return True

    print_lg(f'Setting search location as: "{search_location.strip()}"')
    location_input_xpaths = [
        './/input[contains(translate(@aria-label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "city, state, or zip code") and not(@disabled)]',
        './/input[contains(translate(@aria-label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "location") and not(@disabled)]',
        './/input[contains(@id, "jobs-search-box-location-id") and not(@disabled)]',
        './/input[@role="combobox" and not(@disabled) and contains(translate(@aria-label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "location")]',
        './/input[@role="combobox" and not(@disabled) and contains(translate(@placeholder, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "location")]',
    ]

    search_location_ele = find_first_by_xpaths(location_input_xpaths, timeout=3)
    if search_location_ele:
        try:
            search_location_ele.click()
            search_location_ele.send_keys(Keys.CONTROL + "a")
            search_location_ele.send_keys(search_location.strip())
            sleep(1)
            actions.send_keys(Keys.ENTER).perform()
            return True
        except Exception as e:
            print_lg("Direct location input failed, trying keyboard fallback!", e)

    try:
        click_first_by_xpaths([
            './/label[contains(@for, "jobs-search-box-location-id")]',
            './/label[contains(@class, "jobs-search-box__input-icon")]',
            './/button[contains(translate(@aria-label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "location")]',
        ], reason="open_location_box", timeout=2)
        actions.send_keys(Keys.TAB, Keys.TAB).perform()
        actions.key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).perform()
        actions.send_keys(search_location.strip()).perform()
        sleep(1)
        actions.send_keys(Keys.ENTER).perform()
        try_xp(driver, ".//button[@aria-label='Cancel']")
        return True
    except Exception as e:
        try_xp(driver, ".//button[@aria-label='Cancel']")
        print_lg("Failed to update search location, continuing with default location!", e)
        return False


def apply_filters() -> dict[str, bool]:
    '''
    Function to apply job search filters
    '''
    location_updated = set_search_location()
    all_filters_clicked = False
    show_results_clicked = False
    show_results_required = False
    modal_is_open = False

    try:
        recommended_wait = 1 if click_gap < 1 else 0

        all_filters_clicked = click_first_by_xpaths([
            '//button[normalize-space()="All filters"]',
            '//button[contains(translate(@aria-label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "all filters")]',
            '//button[contains(translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "all filters")]',
        ], reason="all_filters_button", timeout=12)
        if not all_filters_clicked:
            print_lg("Failed to open All filters panel.")
            return {
                "location_updated": location_updated,
                "all_filters_clicked": all_filters_clicked,
                "modal_is_open": modal_is_open,
                "show_results_required": show_results_required,
                "show_results_clicked": show_results_clicked,
                "filters_applied": False,
            }

        buffer(recommended_wait)

        wait_multi_select(driver, [sort_by] if sort_by else [], timeout=2)
        wait_multi_select(driver, [date_posted] if date_posted else [], timeout=2)
        buffer(recommended_wait)

        wait_multi_select(driver, experience_level, timeout=2)
        wait_multi_select(driver, companies, actions, timeout=2)
        if experience_level or companies: buffer(recommended_wait)

        wait_multi_select(driver, job_type, timeout=2)
        wait_multi_select(driver, on_site, timeout=2)
        if job_type or on_site: buffer(recommended_wait)

        if easy_apply_only:
            easy_apply_set = ensure_easy_apply_filter()
            if not easy_apply_set:
                print_lg("Easy Apply filter could not be confirmed as selected.")
        
        wait_multi_select(driver, location, timeout=2)
        wait_multi_select(driver, industry, timeout=2)
        if location or industry: buffer(recommended_wait)

        wait_multi_select(driver, job_function, timeout=2)
        wait_multi_select(driver, job_titles, timeout=2)
        if job_function or job_titles: buffer(recommended_wait)

        if under_10_applicants: boolean_button_click(driver, actions, "Under 10 applicants")
        if in_your_network: boolean_button_click(driver, actions, "In your network")
        if fair_chance_employer: boolean_button_click(driver, actions, "Fair Chance Employer")

        wait_multi_select(driver, [salary] if salary else [], timeout=2)
        buffer(recommended_wait)
        
        wait_multi_select(driver, benefits, timeout=2)
        wait_multi_select(driver, commitments, timeout=2)
        if benefits or commitments: buffer(recommended_wait)

        filter_modal = find_first_by_xpaths([
            '//div[@role="dialog" and (contains(@class,"artdeco-modal") or contains(@class,"jobs-search"))]',
            '//div[contains(@class,"artdeco-modal") and .//button[contains(translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "show") and contains(translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "result")]]',
        ], timeout=1.5)
        modal_is_open = filter_modal is not None
        show_results_required = modal_is_open

        if show_results_required and filter_modal:
            show_results_clicked = click_first_by_xpaths([
                './/button[contains(translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "show") and contains(translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "result")]',
                './/button[contains(translate(@aria-label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "show") and contains(translate(@aria-label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "result")]',
                './/footer//button[contains(@class, "artdeco-button--primary")]',
            ], reason="show_results_button", timeout=4, root=filter_modal)
            if not show_results_clicked:
                print_lg("Failed to click Show results in filter modal.")
        else:
            # New LinkedIn chips UI often auto-applies filters without a modal-level submit button.
            show_results_clicked = True


        global pause_after_filters
        if pause_after_filters and "Turn off Pause after search" == pyautogui.confirm("These are your configured search results and filter. It is safe to change them while this dialog is open, any changes later could result in errors and skipping this search run.", "Please check your results", ["Turn off Pause after search", "Look's good, Continue"]):
            pause_after_filters = False

    except Exception as e:
        print_lg("Setting the preferences failed!")
        pyautogui.confirm(
            text=f"Faced error while applying filters. Please make sure correct filters are selected, click on show results and click on any button of this dialog, I know it sucks. Can't turn off Pause after search when error occurs! ERROR: {e}",
            title="Filter Preference Error",
            buttons=["Doesn't look good, but Continue XD", "Look's good, Continue"]
        )
        return {
            "location_updated": location_updated,
            "all_filters_clicked": all_filters_clicked,
            "modal_is_open": modal_is_open,
            "show_results_required": show_results_required,
            "show_results_clicked": show_results_clicked,
            "filters_applied": False,
        }

    filters_applied = location_updated and all_filters_clicked and (not show_results_required or show_results_clicked)
    print_lg(
        f"Filter apply status -> location_updated={location_updated}, "
        f"all_filters_clicked={all_filters_clicked}, modal_is_open={modal_is_open}, "
        f"show_results_required={show_results_required}, show_results_clicked={show_results_clicked}, "
        f"filters_applied={filters_applied}"
    )
    return {
        "location_updated": location_updated,
        "all_filters_clicked": all_filters_clicked,
        "modal_is_open": modal_is_open,
        "show_results_required": show_results_required,
        "show_results_clicked": show_results_clicked,
        "filters_applied": filters_applied,
    }



def get_page_info() -> tuple[WebElement | None, int | None]:
    '''
    Function to get pagination element and current page number
    '''
    try:
        pagination_element = try_find_by_classes(driver, ["jobs-search-pagination__pages", "artdeco-pagination", "artdeco-pagination__pages"])
        scroll_to_view(driver, pagination_element)
        current_page = int(pagination_element.find_element(By.XPATH, "//button[contains(@class, 'active')]").text)
    except Exception as e:
        print_lg("Failed to find Pagination element, hence couldn't scroll till end!")
        pagination_element = None
        current_page = None
        print_lg(e)
    return pagination_element, current_page


def is_no_matching_jobs_state() -> bool:
    '''
    Returns `True` when LinkedIn page shows "No matching jobs found..." banner.
    '''
    try:
        banner = driver.find_element(By.XPATH, '//*[contains(translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "no matching jobs found")]')
        return banner.is_displayed()
    except Exception:
        return False



def get_job_main_details(job: WebElement, blacklisted_companies: set, rejected_jobs: set) -> tuple[str, str, str, str, str, bool]:
    '''
    # Function to get job main details.
    Returns a tuple of (job_id, title, company, work_location, work_style, skip)
    * job_id: Job ID
    * title: Job title
    * company: Company name
    * work_location: Work location of this job
    * work_style: Work style of this job (Remote, On-site, Hybrid)
    * skip: A boolean flag to skip this job
    '''
    skip = False
    job_id = job.get_dom_attribute('data-occludable-job-id') or "Unknown"
    title = "Unknown"
    company = "Unknown"
    work_location = "Unknown"
    work_style = ""

    try:
        job_details_button = job.find_element(By.TAG_NAME, 'a')  # job.find_element(By.CLASS_NAME, "job-card-list__title")
    except NoSuchElementException:
        print_lg(f"Skipping a non-standard listing card (missing title link). Job ID: {job_id}!")
        return (job_id, title, company, work_location, work_style, True)

    scroll_to_view(driver, job_details_button, True)
    title_text = (job_details_button.text or "").strip()
    title = title_text.split("\n")[0].strip() if title_text else "Unknown"

    try:
        company = job.find_element(By.CLASS_NAME, 'artdeco-entity-lockup__subtitle').text.strip()
    except Exception:
        company = "Unknown"

    try:
        work_location = job.find_element(By.CLASS_NAME, "artdeco-entity-lockup__caption").text.strip()
    except Exception:
        work_location = "Unknown"

        # Fallback when subtitle packs company and location together.
    if (work_location == "Unknown" or not work_location) and company != "Unknown":
        parts = re.split(r"\s*(?:\||-)\s*", company)
        if len(parts) >= 2:
            company = parts[0].strip()
            work_location = parts[1].strip()

    if work_location and "(" in work_location and ")" in work_location:
        try:
            work_style = work_location[work_location.rfind('(')+1:work_location.rfind(')')].strip()
            work_location = work_location[:work_location.rfind('(')].strip()
        except Exception:
            work_style = ""

    # Skip if previously rejected due to blacklist or already applied
    if company in blacklisted_companies:
        print_lg(f'Skipping "{title} | {company}" job (Blacklisted Company). Job ID: {job_id}!')
        skip = True
    elif job_id in rejected_jobs:
        print_lg(f'Skipping previously rejected "{title} | {company}" job. Job ID: {job_id}!')
        skip = True
    try:
        if job.find_element(By.CLASS_NAME, "job-card-container__footer-job-state").text == "Applied":
            skip = True
            print_lg(f'Already applied to "{title} | {company}" job. Job ID: {job_id}!')
    except:
        pass
    try:
        if not skip:
            safe_click(job_details_button, reason="job_details_button")
    except ElementClickInterceptedException as e:
        print_lg(f'Click intercepted for "{title} | {company}" job. Retrying once with JS click. Job ID: {job_id}!')
        try:
            scroll_to_view(driver, job_details_button, True)
            buffer(1)
            driver.execute_script("arguments[0].click();", job_details_button)
        except Exception:
            print_lg(f'Skipping "{title} | {company}" job due to repeated click interception. Job ID: {job_id}!')
            try:
                discard_job()
            except Exception:
                pass
            skip = True
    except Exception as e:
        print_lg(f'Failed to click "{title} | {company}" job on details button. Job ID: {job_id}!')
        try:
            discard_job()
        except Exception:
            pass
        skip = True
    buffer(click_gap)
    return (job_id, title, company, work_location, work_style, skip)


def normalize_title_text(text: str) -> list[str]:
    '''
    Normalize text into lowercase word tokens for title matching.
    '''
    normalized = re.sub(r'[^a-z0-9]+', ' ', text.lower())
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    if not normalized:
        return []
    return normalized.split(' ')


def title_matches_any_search_term(title: str, search_terms: list[str]) -> tuple[bool, str | None]:
    '''
    Returns `(True, matched_term)` if title contains all words from at least one search term.
    Matching is case-insensitive and order-independent.
    '''
    title_tokens = set(normalize_title_text(title))
    if len(title_tokens) == 0:
        return (False, None)
    optional_tokens = set(
        token.strip().lower()
        for token in search_term_optional_tokens
        if isinstance(token, str) and token.strip()
    )
    for term in search_terms:
        term_tokens = set(normalize_title_text(term))
        if optional_tokens:
            term_tokens = {tok for tok in term_tokens if tok not in optional_tokens}
        if len(term_tokens) == 0:
            continue
        if term_tokens.issubset(title_tokens):
            return (True, term)
    return (False, None)


def title_matches_with_overlap_fallback(
    title: str,
    current_search_term: str,
    all_search_terms: list[str],
) -> tuple[bool, str | None, str]:
    '''
    Returns `(matched, matched_term, match_mode)` where:
    - `match_mode="full"` for strict all-token term match.
    - `match_mode="overlap"` for current-term token overlap fallback.
    '''
    matched, matched_term = title_matches_any_search_term(title, all_search_terms)
    if matched:
        return (True, matched_term, "full")

    if min_title_token_overlap <= 0:
        return (False, None, "none")

    title_tokens = set(normalize_title_text(title))
    optional_tokens = set(
        token.strip().lower()
        for token in search_term_optional_tokens
        if isinstance(token, str) and token.strip()
    )
    term_tokens = set(normalize_title_text(current_search_term))
    if optional_tokens:
        term_tokens = {tok for tok in term_tokens if tok not in optional_tokens}
    if len(term_tokens) == 0:
        return (False, None, "none")

    overlap = term_tokens.intersection(title_tokens)
    if len(overlap) >= min_title_token_overlap:
        return (True, current_search_term, "overlap")
    return (False, None, "none")


def normalize_location_text(text: str) -> set[str]:
    '''
    Normalize location text into lowercase token set.
    '''
    normalized = re.sub(r'[^a-z0-9]+', ' ', text.lower())
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    if not normalized:
        return set()
    return set(normalized.split(' '))


def get_primary_target_location_tokens(search_location_text: str, location_filters: list[str]) -> tuple[set[str], str]:
    '''
    Resolve primary target location tokens from search_location, or fallback to first location filter.
    '''
    if search_location_text.strip():
        primary_segment = search_location_text.split(',')[0].strip()
        tokens = normalize_location_text(primary_segment)
        if tokens:
            return (tokens, primary_segment)
    if location_filters:
        fallback = location_filters[0].strip()
        tokens = normalize_location_text(fallback)
        if tokens:
            return (tokens, fallback)
    return (set(), "")


def job_matches_target_location(work_location: str, search_location_text: str, location_filters: list[str]) -> bool:
    '''
    True if the job work_location includes all tokens of the primary target location.
    '''
    target_tokens, _ = get_primary_target_location_tokens(search_location_text, location_filters)
    if len(target_tokens) == 0:
        return True
    work_location_tokens = normalize_location_text(work_location)
    return target_tokens.issubset(work_location_tokens)


def log_skip_reason(reason: str, title: str, company: str, job_id: str, extra: str = "") -> None:
    '''
    Standardized skip-reason logging for observability.
    '''
    suffix = f" | {extra}" if extra else ""
    print_lg(f'SKIP[{reason}] "{title} | {company}" Job ID: {job_id}{suffix}')


# Function to check for Blacklisted words in About Company
def check_blacklist(rejected_jobs: set, job_id: str, company: str, blacklisted_companies: set) -> tuple[set, set, WebElement] | ValueError:
    jobs_top_card = try_find_by_classes(driver, ["job-details-jobs-unified-top-card__primary-description-container","job-details-jobs-unified-top-card__primary-description","jobs-unified-top-card__primary-description","jobs-details__main-content"])
    about_company_org = find_by_class(driver, "jobs-company__box")
    scroll_to_view(driver, about_company_org)
    about_company_org = about_company_org.text
    about_company = about_company_org.lower()
    skip_checking = False
    for word in about_company_good_words:
        if word.lower() in about_company:
            print_lg(f'Found the word "{word}". So, skipped checking for blacklist words.')
            skip_checking = True
            break
    if not skip_checking:
        for word in about_company_bad_words: 
            if word.lower() in about_company: 
                rejected_jobs.add(job_id)
                blacklisted_companies.add(company)
                raise ValueError(f'\n"{about_company_org}"\n\nContains "{word}".')
    buffer(click_gap)
    scroll_to_view(driver, jobs_top_card)
    return rejected_jobs, blacklisted_companies, jobs_top_card



# Function to extract years of experience required from About Job
def extract_years_of_experience(text: str) -> int:
    # Extract all patterns like '10+ years', '5 years', '3-5 years', etc.
    matches = re.findall(re_experience, text)
    if len(matches) == 0: 
        print_lg(f'\n{text}\n\nCouldn\'t find experience requirement in About the Job!')
        return 0
    return max([int(match) for match in matches if int(match) <= 12])



def get_job_description(
) -> tuple[
    str | Literal['Unknown'],
    int | Literal['Unknown'],
    bool,
    str | None,
    str | None
    ]:
    '''
    # Job Description
    Function to extract job description from About the Job.
    ### Returns:
    - `jobDescription: str | 'Unknown'`
    - `experience_required: int | 'Unknown'`
    - `skip: bool`
    - `skipReason: str | None`
    - `skipMessage: str | None`
    '''
    ##> ------ Dheeraj Deshwal : dheeraj9811 Email:dheeraj20194@iiitd.ac.in/dheerajdeshwal9811@gmail.com - Feature ------
    jobDescription = "Unknown"
    ##<
    experience_required = "Unknown"
    skip = False
    skipReason = None
    skipMessage = None
    try:
        found_masters = 0
        jobDescription = find_by_class(driver, "jobs-box__html-content").text
        jobDescriptionLow = jobDescription.lower()
        for word in bad_words:
            if word.lower() in jobDescriptionLow:
                skipMessage = f'\n{jobDescription}\n\nContains bad word "{word}". Skipping this job!\n'
                skipReason = "Found a Bad Word in About Job"
                skip = True
                break
        if not skip and security_clearance == False and ('polygraph' in jobDescriptionLow or 'clearance' in jobDescriptionLow or 'secret' in jobDescriptionLow):
            skipMessage = f'\n{jobDescription}\n\nFound "Clearance" or "Polygraph". Skipping this job!\n'
            skipReason = "Asking for Security clearance"
            skip = True
        if not skip:
            if did_masters and 'master' in jobDescriptionLow:
                print_lg(f'Found the word "master" in \n{jobDescription}')
                found_masters = 2
            experience_required = extract_years_of_experience(jobDescription)
            if current_experience > -1 and experience_required > current_experience + found_masters:
                skipMessage = (
                    f'\n{jobDescription}\n\n'
                    f'Experience required {experience_required} > Current Experience {current_experience + found_masters}. '
                    'Skipping this job!\n'
                    'Tip: set current_experience = -1 in config/search.py to disable this skip gate.\n'
                )
                skipReason = "Required experience is high"
                skip = True
    except Exception as e:
        if jobDescription == "Unknown":    print_lg("Unable to extract job description!")
        else:
            experience_required = "Error in extraction"
            print_lg("Unable to extract years of experience required!")
            # print_lg(e)
    return jobDescription, experience_required, skip, skipReason, skipMessage
        


# Function to upload resume
def upload_resume(modal: WebElement, resume: str) -> tuple[bool, str]:
    try:
        modal.find_element(By.NAME, "file").send_keys(os.path.abspath(resume))
        return True, os.path.basename(default_resume_path)
    except: return False, "Previous resume"

# Function to answer common questions for Easy Apply
def answer_common_questions(label: str, answer: str) -> str:
    if 'sponsorship' in label or 'visa' in label: answer = require_visa
    return answer


# Function to answer the questions for Easy Apply
def answer_questions(modal: WebElement, questions_list: set, work_location: str, job_description: str | None = None ) -> set:
    # Get all questions from the page
     
    all_questions = modal.find_elements(By.XPATH, ".//div[@data-test-form-element]")
    # all_questions = modal.find_elements(By.CLASS_NAME, "jobs-easy-apply-form-element")
    # all_list_questions = modal.find_elements(By.XPATH, ".//div[@data-test-text-entity-list-form-component]")
    # all_single_line_questions = modal.find_elements(By.XPATH, ".//div[@data-test-single-line-text-form-component]")
    # all_questions = all_questions + all_list_questions + all_single_line_questions

    for Question in all_questions:
        # Check if it's a select Question
        select = try_xp(Question, ".//select", False)
        if select:
            label_org = "Unknown"
            try:
                label = Question.find_element(By.TAG_NAME, "label")
                label_org = label.find_element(By.TAG_NAME, "span").text
            except: pass
            answer = 'Yes'
            label = label_org.lower()
            select = Select(select)
            selected_option = select.first_selected_option.text
            optionsText = []
            options = '"List of phone country codes"'
            if label != "phone country code":
                optionsText = [option.text for option in select.options]
                options = "".join([f' "{option}",' for option in optionsText])
            prev_answer = selected_option
            if overwrite_previous_answers or selected_option == "Select an option":
                ##> ------ WINDY_WINDWARD Email:karthik.sarode23@gmail.com - Added fuzzy logic to answer location based questions ------
                if 'email' in label or 'phone' in label: 
                    answer = prev_answer
                elif 'gender' in label or 'sex' in label: 
                    answer = gender
                elif 'disability' in label: 
                    answer = disability_status
                elif 'proficiency' in label: 
                    answer = 'Professional'
                # Add location handling
                elif any(loc_word in label for loc_word in ['location', 'city', 'state', 'country']):
                    if 'country' in label:
                        answer = country 
                    elif 'state' in label:
                        answer = state
                    elif 'city' in label:
                        answer = current_city if current_city else work_location
                    else:
                        answer = work_location
                else: 
                    answer = answer_common_questions(label,answer)
                try: 
                    select.select_by_visible_text(answer)
                except NoSuchElementException as e:
                    # Define similar phrases for common answers
                    possible_answer_phrases = []
                    if answer == 'Decline':
                        possible_answer_phrases = ["Decline", "not wish", "don't wish", "Prefer not", "not want"]
                    elif 'yes' in answer.lower():
                        possible_answer_phrases = ["Yes", "Agree", "I do", "I have"]
                    elif 'no' in answer.lower():
                        possible_answer_phrases = ["No", "Disagree", "I don't", "I do not"]
                    else:
                        # Try partial matching for any answer
                        possible_answer_phrases = [answer]
                        # Add lowercase and uppercase variants
                        possible_answer_phrases.append(answer.lower())
                        possible_answer_phrases.append(answer.upper())
                        # Try without special characters
                        possible_answer_phrases.append(''.join(c for c in answer if c.isalnum()))
                    ##<
                    foundOption = False
                    for phrase in possible_answer_phrases:
                        for option in optionsText:
                            # Check if phrase is in option or option is in phrase (bidirectional matching)
                            if phrase.lower() in option.lower() or option.lower() in phrase.lower():
                                select.select_by_visible_text(option)
                                answer = option
                                foundOption = True
                                break
                    if not foundOption:
                        #TODO: Use AI to answer the question need to be implemented logic to extract the options for the question
                        print_lg(f'Failed to find an option with text "{answer}" for question labelled "{label_org}", answering randomly!')
                        select.select_by_index(randint(1, len(select.options)-1))
                        answer = select.first_selected_option.text
                        randomly_answered_questions.add((f'{label_org} [ {options} ]',"select"))
            questions_list.add((f'{label_org} [ {options} ]', answer, "select", prev_answer))
            continue
        
        # Check if it's a radio Question
        radio = try_xp(Question, './/fieldset[@data-test-form-builder-radio-button-form-component="true"]', False)
        if radio:
            prev_answer = None
            label = try_xp(radio, './/span[@data-test-form-builder-radio-button-form-component__title]', False)
            try: label = find_by_class(label, "visually-hidden", 2.0)
            except: pass
            label_org = label.text if label else "Unknown"
            answer = 'Yes'
            label = label_org.lower()

            label_org += ' [ '
            options = radio.find_elements(By.TAG_NAME, 'input')
            options_labels = []
            
            for option in options:
                id = option.get_attribute("id")
                option_label = try_xp(radio, f'.//label[@for="{id}"]', False)
                options_labels.append( f'"{option_label.text if option_label else "Unknown"}"<{option.get_attribute("value")}>' ) # Saving option as "label <value>"
                if option.is_selected(): prev_answer = options_labels[-1]
                label_org += f' {options_labels[-1]},'

            if overwrite_previous_answers or prev_answer is None:
                if 'citizenship' in label or 'employment eligibility' in label: answer = us_citizenship
                elif 'veteran' in label or 'protected' in label: answer = veteran_status
                elif 'disability' in label or 'handicapped' in label: 
                    answer = disability_status
                else: answer = answer_common_questions(label,answer)
                foundOption = try_xp(radio, f".//label[normalize-space()='{answer}']", False)
                if foundOption: 
                    actions.move_to_element(foundOption).click().perform()
                else:    
                    possible_answer_phrases = ["Decline", "not wish", "don't wish", "Prefer not", "not want"] if answer == 'Decline' else [answer]
                    ele = options[0]
                    answer = options_labels[0]
                    for phrase in possible_answer_phrases:
                        for i, option_label in enumerate(options_labels):
                            if phrase in option_label:
                                foundOption = options[i]
                                ele = foundOption
                                answer = f'Decline ({option_label})' if len(possible_answer_phrases) > 1 else option_label
                                break
                        if foundOption: break
                    # if answer == 'Decline':
                    #     answer = options_labels[0]
                    #     for phrase in ["Prefer not", "not want", "not wish"]:
                    #         foundOption = try_xp(radio, f".//label[normalize-space()='{phrase}']", False)
                    #         if foundOption:
                    #             answer = f'Decline ({phrase})'
                    #             ele = foundOption
                    #             break
                    actions.move_to_element(ele).click().perform()
                    if not foundOption: randomly_answered_questions.add((f'{label_org} ]',"radio"))
            else: answer = prev_answer
            questions_list.add((label_org+" ]", answer, "radio", prev_answer))
            continue
        
        # Check if it's a text question
        text = try_xp(Question, ".//input[@type='text']", False)
        if text: 
            do_actions = False
            label = try_xp(Question, ".//label[@for]", False)
            try: label = label.find_element(By.CLASS_NAME,'visually-hidden')
            except: pass
            label_org = label.text if label else "Unknown"
            answer = "" # years_of_experience
            label = label_org.lower()

            prev_answer = text.get_attribute("value")
            if not prev_answer or overwrite_previous_answers:
                if 'experience' in label or 'years' in label: answer = years_of_experience
                elif 'phone' in label or 'mobile' in label: answer = phone_number
                elif 'street' in label: answer = street
                elif 'city' in label or 'location' in label or 'address' in label:
                    answer = current_city if current_city else work_location
                    do_actions = True
                elif 'signature' in label: answer = full_name # 'signature' in label or 'legal name' in label or 'your name' in label or 'full name' in label: answer = full_name     # What if question is 'name of the city or university you attend, name of referral etc?'
                elif 'name' in label:
                    if 'full' in label: answer = full_name
                    elif 'first' in label and 'last' not in label: answer = first_name
                    elif 'middle' in label and 'last' not in label: answer = middle_name
                    elif 'last' in label and 'first' not in label: answer = last_name
                    elif 'employer' in label: answer = recent_employer
                    else: answer = full_name
                elif 'notice' in label:
                    if 'month' in label:
                        answer = notice_period_months
                    elif 'week' in label:
                        answer = notice_period_weeks
                    else: answer = notice_period
                elif 'salary' in label or 'compensation' in label or 'ctc' in label or 'pay' in label: 
                    if 'current' in label or 'present' in label:
                        if 'month' in label:
                            answer = current_ctc_monthly
                        elif 'lakh' in label:
                            answer = current_ctc_lakhs
                        else:
                            answer = current_ctc
                    else:
                        if 'month' in label:
                            answer = desired_salary_monthly
                        elif 'lakh' in label:
                            answer = desired_salary_lakhs
                        else:
                            answer = desired_salary
                elif 'linkedin' in label: answer = linkedIn
                elif 'website' in label or 'blog' in label or 'portfolio' in label or 'link' in label: answer = website
                elif 'scale of 1-10' in label: answer = confidence_level
                elif 'headline' in label: answer = linkedin_headline
                elif ('hear' in label or 'come across' in label) and 'this' in label and ('job' in label or 'position' in label): answer = "https://github.com/GodsScion/Auto_job_applier_linkedIn"
                elif 'state' in label or 'province' in label: answer = state
                elif 'zip' in label or 'postal' in label or 'code' in label: answer = zipcode
                elif 'country' in label: answer = country
                else: answer = answer_common_questions(label,answer)
                ##> ------ Yang Li : MARKYangL - Feature ------
                if answer == "":
                    if use_AI and aiClient:
                        try:
                            if ai_provider.lower() == "openai":
                                answer = ai_answer_question(aiClient, label_org, question_type="text", job_description=job_description, user_information_all=user_information_all)
                            elif ai_provider.lower() == "deepseek":
                                answer = deepseek_answer_question(aiClient, label_org, options=None, question_type="text", job_description=job_description, about_company=None, user_information_all=user_information_all)
                            elif ai_provider.lower() == "gemini":
                                answer = gemini_answer_question(aiClient, label_org, options=None, question_type="text", job_description=job_description, about_company=None, user_information_all=user_information_all)
                            else:
                                randomly_answered_questions.add((label_org, "text"))
                                answer = years_of_experience
                            if answer and isinstance(answer, str) and len(answer) > 0:
                                print_lg(f'AI Answered received for question "{label_org}" \nhere is answer: "{answer}"')
                            else:
                                randomly_answered_questions.add((label_org, "text"))
                                answer = years_of_experience
                        except Exception as e:
                            print_lg("Failed to get AI answer!", e)
                            randomly_answered_questions.add((label_org, "text"))
                            answer = years_of_experience
                    else:
                        randomly_answered_questions.add((label_org, "text"))
                        answer = years_of_experience
                ##<
                text.clear()
                text.send_keys(answer)
                if do_actions:
                    sleep(2)
                    actions.send_keys(Keys.ARROW_DOWN)
                    actions.send_keys(Keys.ENTER).perform()
            questions_list.add((label, text.get_attribute("value"), "text", prev_answer))
            continue

        # Check if it's a textarea question
        text_area = try_xp(Question, ".//textarea", False)
        if text_area:
            label = try_xp(Question, ".//label[@for]", False)
            label_org = label.text if label else "Unknown"
            label = label_org.lower()
            answer = ""
            prev_answer = text_area.get_attribute("value")
            if not prev_answer or overwrite_previous_answers:
                if 'summary' in label: answer = linkedin_summary
                elif 'cover' in label: answer = cover_letter
                if answer == "":
                ##> ------ Yang Li : MARKYangL - Feature ------
                    if use_AI and aiClient:
                        try:
                            if ai_provider.lower() == "openai":
                                answer = ai_answer_question(aiClient, label_org, question_type="textarea", job_description=job_description, user_information_all=user_information_all)
                            elif ai_provider.lower() == "deepseek":
                                answer = deepseek_answer_question(aiClient, label_org, options=None, question_type="textarea", job_description=job_description, about_company=None, user_information_all=user_information_all)
                            elif ai_provider.lower() == "gemini":
                                answer = gemini_answer_question(aiClient, label_org, options=None, question_type="textarea", job_description=job_description, about_company=None, user_information_all=user_information_all)
                            else:
                                randomly_answered_questions.add((label_org, "textarea"))
                                answer = ""
                            if answer and isinstance(answer, str) and len(answer) > 0:
                                print_lg(f'AI Answered received for question "{label_org}" \nhere is answer: "{answer}"')
                            else:
                                randomly_answered_questions.add((label_org, "textarea"))
                                answer = ""
                        except Exception as e:
                            print_lg("Failed to get AI answer!", e)
                            randomly_answered_questions.add((label_org, "textarea"))
                            answer = ""
                    else:
                        randomly_answered_questions.add((label_org, "textarea"))
            text_area.clear()
            text_area.send_keys(answer)
            if do_actions:
                    sleep(2)
                    actions.send_keys(Keys.ARROW_DOWN)
                    actions.send_keys(Keys.ENTER).perform()
            questions_list.add((label, text_area.get_attribute("value"), "textarea", prev_answer))
            ##<
            continue

        # Check if it's a checkbox question
        checkbox = try_xp(Question, ".//input[@type='checkbox']", False)
        if checkbox:
            label = try_xp(Question, ".//span[@class='visually-hidden']", False)
            label_org = label.text if label else "Unknown"
            label = label_org.lower()
            answer = try_xp(Question, ".//label[@for]", False)  # Sometimes multiple checkboxes are given for 1 question, Not accounted for that yet
            answer = answer.text if answer else "Unknown"
            prev_answer = checkbox.is_selected()
            checked = prev_answer
            if not prev_answer:
                try:
                    actions.move_to_element(checkbox).click().perform()
                    checked = True
                except Exception as e: 
                    print_lg("Checkbox click failed!", e)
                    pass
            questions_list.add((f'{label} ([X] {answer})', checked, "checkbox", prev_answer))
            continue


    # Select todays date
    try_xp(driver, "//button[contains(@aria-label, 'This is today')]")

    # Collect important skills
    # if 'do you have' in label and 'experience' in label and ' in ' in label -> Get word (skill) after ' in ' from label
    # if 'how many years of experience do you have in ' in label -> Get word (skill) after ' in '

    return questions_list




def external_apply(
    pagination_element: WebElement,
    job_id: str,
    job_link: str,
    resume: str,
    date_listed,
    application_link: str,
    screenshot_name: str,
    job_description: str = "Unknown"
) -> tuple[bool, ExternalApplyOutcome, int]:
    '''
    Function to open external apply page, run portal adapter autofill and return structured outcome.
    '''
    global tabs_count, dailyEasyApplyLimitReached
    outcome = ExternalApplyOutcome(application_link=application_link)
    if easy_apply_only:
        try:
            if "exceeded the daily application limit" in driver.find_element(By.CLASS_NAME, "artdeco-inline-feedback__message").text: dailyEasyApplyLimitReached = True
        except: pass
        print_lg("Easy Apply only mode is enabled. Skipping external application flow.")
        outcome.apply_status = "saved_link_only"
        outcome.notes = "Easy Apply only mode; external skipped"
        return True, outcome, tabs_count
    try:
        wait.until(EC.element_to_be_clickable((By.XPATH, ".//button[contains(@class,'jobs-apply-button') and contains(@class, 'artdeco-button--3')]"))).click() # './/button[contains(span, "Apply") and not(span[contains(@class, "disabled")])]'
        wait_span_click(driver, "Continue", 1, True, False)
        windows = driver.window_handles
        tabs_count = len(windows)
        driver.switch_to.window(windows[-1])
        application_link = driver.current_url
        outcome.application_link = application_link
        print_lg('Got the external application link "{}"'.format(application_link))

        if not enable_external_apply_ai:
            outcome.apply_status = "saved_link_only"
            outcome.notes = "External portal automation disabled in config"
        else:
            adapter = detect_portal_adapter(application_link)
            if not adapter:
                outcome.apply_status = "saved_link_only"
                outcome.portal_name = "unknown"
                outcome.notes = "Unsupported external portal adapter"
            else:
                profile = build_profile()
                session = adapter.prepare(driver, auth_mode=external_auth_mode)
                fill_result = adapter.fill(
                    driver=driver,
                    profile=profile,
                    ai_client=aiClient if use_AI else None,
                    job_context={"job_description": job_description, "about_company": about_company_for_ai},
                )
                outcome.portal_name = fill_result.portal_name
                outcome.application_link = fill_result.final_url or application_link
                outcome.filled_fields = fill_result.filled_fields
                outcome.unanswered_questions = fill_result.unanswered_questions

                notes = []
                if session.notes:
                    notes.extend(session.notes)
                if fill_result.notes:
                    notes.extend(fill_result.notes)

                if external_apply_pause_before_submit:
                    review = adapter.pause_for_review(driver)
                    if not review.confirmed:
                        fill_result.status = "needs_manual"
                    if review.note:
                        notes.append(review.note)

                if fill_result.status == "filled":
                    outcome.apply_status = "filled_pending_submit"
                elif fill_result.status == "needs_manual":
                    outcome.apply_status = "manual_needed"
                else:
                    outcome.apply_status = "failed"
                outcome.notes = "; ".join([n for n in notes if n])

        if close_tabs and driver.current_window_handle != linkedIn_tab:
            driver.close()
        driver.switch_to.window(linkedIn_tab)
        return False, outcome, tabs_count
    except Exception as e:
        # print_lg(e)
        print_lg("Failed to apply!")
        failed_job(job_id, job_link, resume, date_listed, "Probably didn't find Apply button or unable to switch tabs.", e, application_link, screenshot_name)
        outcome.apply_status = "failed"
        outcome.notes = "Probably didn't find Apply button or unable to switch tabs."
        global failed_count
        failed_count += 1
        try:
            driver.switch_to.window(linkedIn_tab)
        except Exception:
            pass
        return True, outcome, tabs_count



def follow_company(modal: WebDriver = driver) -> None:
    '''
    Function to follow or un-follow easy applied companies based om `follow_companies`
    '''
    try:
        follow_checkbox_input = try_xp(modal, ".//input[@id='follow-company-checkbox' and @type='checkbox']", False)
        if follow_checkbox_input and follow_checkbox_input.is_selected() != follow_companies:
            try_xp(modal, ".//label[@for='follow-company-checkbox']")
    except Exception as e:
        print_lg("Failed to update follow companies checkbox!", e)
    


#< Failed attempts logging
def failed_job(job_id: str, job_link: str, resume: str, date_listed, error: str, exception: Exception, application_link: str, screenshot_name: str) -> None:
    '''
    Function to update failed jobs list in excel
    '''
    try:
        with open(failed_file_name, 'a', newline='', encoding='utf-8') as file:
            fieldnames = ['Job ID', 'Job Link', 'Resume Tried', 'Date listed', 'Date Tried', 'Assumed Reason', 'Stack Trace', 'External Job link', 'Screenshot Name']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            if file.tell() == 0: writer.writeheader()
            writer.writerow({'Job ID':truncate_for_csv(job_id), 'Job Link':truncate_for_csv(job_link), 'Resume Tried':truncate_for_csv(resume), 'Date listed':truncate_for_csv(date_listed), 'Date Tried':datetime.now(), 'Assumed Reason':truncate_for_csv(error), 'Stack Trace':truncate_for_csv(exception), 'External Job link':truncate_for_csv(application_link), 'Screenshot Name':truncate_for_csv(screenshot_name)})
            file.close()
    except Exception as e:
        print_lg("Failed to update failed jobs list!", e)
        pyautogui.alert("Failed to update the excel of failed jobs!\nProbably because of 1 of the following reasons:\n1. The file is currently open or in use by another program\n2. Permission denied to write to the file\n3. Failed to find the file", "Failed Logging")


def screenshot(driver: WebDriver, job_id: str, failedAt: str) -> str:
    '''
    Function to to take screenshot for debugging
    - Returns screenshot name as String
    '''
    screenshot_name = "{} - {} - {}.png".format( job_id, failedAt, str(datetime.now()) )
    path = logs_folder_path+"/screenshots/"+screenshot_name.replace(":",".")
    # special_chars = {'*', '"', '\\', '<', '>', ':', '|', '?'}
    # for char in special_chars:  path = path.replace(char, '-')
    driver.save_screenshot(path.replace("//","/"))
    return screenshot_name
#>


def submitted_jobs(job_id: str, title: str, company: str, work_location: str, work_style: str, description: str,
                   experience_required: int | Literal['Unknown', 'Error in extraction'],
                   skills: list[str] | Literal['In Development'], hr_name: str | Literal['Unknown'],
                   hr_link: str | Literal['Unknown'], resume: str,
                   reposted: bool, date_listed: datetime | Literal['Unknown'],
                   date_applied: datetime | Literal['Pending'],
                   job_link: str, application_link: str,
                   questions_list: set | None, connect_request: Literal['In Development'],
                   external_outcome: ExternalApplyOutcome | None = None) -> None:
    '''
    Function to create or update the Applied jobs CSV file, once the application is submitted successfully.
    '''
    try:
        fieldnames = [
            'Job ID', 'Title', 'Company', 'Work Location', 'Work Style', 'About Job',
            'Experience required', 'Skills required', 'HR Name', 'HR Link', 'HR Link Collected',
            'Resume', 'Re-posted', 'Date Posted', 'Date Applied', 'Job Link', 'External Job link',
            'Questions Found', 'Connect Request', 'Apply Type', 'External Portal',
            'External Apply Status', 'External Notes'
        ]
        normalized_hr_name = normalize_hr_value(hr_name)
        normalized_hr_link = normalize_linkedin_person_url(hr_link)
        hr_link_collected = is_valid_linkedin_person_url(normalized_hr_link)
        if not hr_link_collected:
            normalized_hr_link = "Unknown"
        elif normalized_hr_name == "Unknown":
            normalized_hr_name = infer_name_from_linkedin_url(normalized_hr_link)

        if os.path.exists(file_name) and os.path.getsize(file_name) > 0:
            with open(file_name, mode='r', newline='', encoding='utf-8') as existing_csv:
                existing_header = next(csv.reader(existing_csv), [])
            if existing_header and existing_header != fieldnames:
                error_msg = (
                    f"Applied CSV header mismatch in '{file_name}'. "
                    "Expected simplified HR columns near 'HR Link' (HR Link Collected only). "
                    "Please migrate or rename the existing file before running."
                )
                print_lg(error_msg)
                raise ValueError(error_msg)

        is_easy_applied = str(application_link).strip().lower() == "easy applied"
        is_external = bool(application_link and (not is_easy_applied) and ("linkedin.com" not in application_link.lower()))
        apply_type = "External" if is_external else "LinkedIn Easy Apply"
        external_portal = "unknown"
        external_status = ""
        external_notes = ""

        if is_external:
            date_applied = "Pending (External Apply)"
            if external_outcome:
                external_portal = external_outcome.portal_name or "unknown"
                external_status = external_outcome.apply_status or "saved_link_only"
                external_notes = external_outcome.notes or ""
            else:
                external_status = "saved_link_only"

        with open(file_name, mode='a', newline='', encoding='utf-8') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            if csv_file.tell() == 0:
                writer.writeheader()

            writer.writerow({
                'Job ID': str(job_id),
                'Title': truncate_for_csv(title),
                'Company': truncate_for_csv(company),
                'Work Location': truncate_for_csv(work_location),
                'Work Style': truncate_for_csv(work_style),
                'About Job': truncate_for_csv(description),
                'Experience required': truncate_for_csv(experience_required),
                'Skills required': truncate_for_csv(skills),
                'HR Name': truncate_for_csv(normalized_hr_name),
                'HR Link': truncate_for_csv(normalized_hr_link),
                'HR Link Collected': hr_link_collected,
                'Resume': truncate_for_csv(resume),
                'Re-posted': truncate_for_csv(reposted),
                'Date Posted': truncate_for_csv(date_listed),
                'Date Applied': truncate_for_csv(date_applied),
                'Job Link': truncate_for_csv(job_link),
                'External Job link': truncate_for_csv(application_link),
                'Questions Found': truncate_for_csv(questions_list),
                'Connect Request': truncate_for_csv(connect_request),
                'Apply Type': truncate_for_csv(apply_type),
                'External Portal': truncate_for_csv(external_portal),
                'External Apply Status': truncate_for_csv(external_status),
                'External Notes': truncate_for_csv(external_notes),
            })

        csv_file.close()

        if is_external:
            print_lg(f"[EXTERNAL SAVED] {title} | {company} | {application_link}")
        else:
            print_lg(f"[APPLIED SAVED] {title} | {company}")

    except Exception as e:
        print_lg("Failed to update submitted jobs list!", e)
        pyautogui.alert(
            "Failed to update the excel of applied jobs!\nProbably because of 1 of the following reasons:\n"
            "1. The file is currently open or in use by another program\n"
            "2. Permission denied to write to the file\n"
            "3. Failed to find the file",
            "Failed Logging"
        )

# Function to discard the job application
def discard_job() -> None:
    actions.send_keys(Keys.ESCAPE).perform()
    wait_span_click(driver, 'Discard', 2)


def build_linkedin_search_url(searchTerm: str, include_location: bool = True, include_easy_apply: bool = True) -> str:
    '''
    Build LinkedIn jobs search URL with optional location and Easy Apply query params.
    '''
    encoded_term = quote_plus(searchTerm)
    query_parts = [f"keywords={encoded_term}"]
    if include_location and search_location.strip():
        query_parts.append(f"location={quote_plus(search_location.strip())}")
    if include_easy_apply and easy_apply_only:
        query_parts.append("f_AL=true")
    return "https://www.linkedin.com/jobs/search/?" + "&".join(query_parts)


def reset_top_filters_if_present() -> None:
    '''
    Best-effort reset for top chip filters before relaxed retry.
    '''
    click_first_by_xpaths([
        '//button[normalize-space()="Reset"]',
        '//a[normalize-space()="Reset"]',
        '//button[contains(translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "reset")]',
    ], reason="reset_top_filters", timeout=2)






# Function to apply to jobs
def apply_to_jobs(search_terms: list[str]) -> None:
    applied_jobs = get_applied_job_ids()
    rejected_jobs = set()
    blacklisted_companies = set()
    global current_city, failed_count, skip_count, easy_applied_count, external_jobs_count, tabs_count, pause_before_submit, pause_at_failed_question, useNewResume
    current_city = current_city.strip()

    if randomize_search_order:  shuffle(search_terms)
    for searchTerm in search_terms:
        driver.get(build_linkedin_search_url(searchTerm, include_location=True, include_easy_apply=True))
        print_lg("\n________________________________________________________________________________________________________________________\n")
        print_lg(f'\n>>>> Now searching for "{searchTerm}" <<<<\n\n')

        filter_status = apply_filters()
        filters_applied = filter_status.get("filters_applied", False)
        target_location_tokens, target_location_text = get_primary_target_location_tokens(search_location, location)
        location_skip_count_this_search = 0
        print_lg(
            f'Location guard target -> "{target_location_text}" '
            f'(tokens: {sorted(list(target_location_tokens)) if target_location_tokens else []})'
        )
        print_lg(
            "Filter status summary -> "
            f"modal_is_open={filter_status.get('modal_is_open', False)}, "
            f"show_results_required={filter_status.get('show_results_required', False)}, "
            f"show_results_clicked={filter_status.get('show_results_clicked', False)}, "
            f"filters_applied={filters_applied}"
        )
        if strict_filter_apply_required and not filters_applied:
            print_lg(
                f'Skipping search term "{searchTerm}" because strict_filter_apply_required=True '
                f'and filter application did not fully succeed.'
            )
            continue
        if is_no_matching_jobs_state():
            print_lg(
                f'No matching jobs found for "{searchTerm}" with strict filters. '
                f'Retrying once with relaxed filters (location + easy apply only).'
            )
            reset_top_filters_if_present()
            driver.get(build_linkedin_search_url(searchTerm, include_location=True, include_easy_apply=True))
            buffer(2)
            if is_no_matching_jobs_state():
                print_lg(
                    f'No matching jobs found for "{searchTerm}" even after relaxed retry. '
                    f'Skipping recommendation cards for this term.'
                )
                continue
            print_lg(f'Relaxed retry found results for "{searchTerm}". Proceeding to apply flow.')

        current_count = 0
        try:
            while current_count < switch_number:
                # Wait until job listings are loaded
                wait.until(EC.presence_of_all_elements_located((By.XPATH, "//li[@data-occludable-job-id]")))

                pagination_element, current_page = get_page_info()

                # Find all job listings in current page
                buffer(3)
                job_listings = driver.find_elements(By.XPATH, "//li[@data-occludable-job-id]")  

            
                for job in job_listings:
                    if keep_screen_awake: pyautogui.press('shiftright')
                    if current_count >= switch_number: break
                    print_lg("\n-@-\n")

                    try:
                        job_id,title,company,work_location,work_style,skip = get_job_main_details(job, blacklisted_companies, rejected_jobs)
                    except StaleElementReferenceException as e:
                        print_lg("Stale listing card encountered. Skipping this card and continuing.", e)
                        continue
                    
                    if skip: continue

                    if enforce_search_term_title_match:
                        matched_title, matched_term, match_mode = title_matches_with_overlap_fallback(
                            title,
                            searchTerm,
                            search_terms,
                        )
                        if not matched_title:
                            log_skip_reason(
                                "title_mismatch",
                                title,
                                company,
                                job_id,
                                "No search-term token-complete match",
                            )
                            skip_count += 1
                            continue
                        print_lg(
                            f'Title matched search term "{matched_term}" for "{title}" '
                            f'(mode={match_mode}). Job ID: {job_id}!'
                        )

                    if enforce_target_location_match and not job_matches_target_location(work_location, search_location, location):
                        log_skip_reason(
                            "location_mismatch",
                            title,
                            company,
                            job_id,
                            f'job="{work_location}", target="{target_location_text}"',
                        )
                        skip_count += 1
                        location_skip_count_this_search += 1
                        continue

                    # Redundant fail safe check for applied jobs!
                    try:
                        if job_id in applied_jobs or find_by_class(driver, "jobs-s-apply__application-link", 2):
                            print_lg(f'Already applied to "{title} | {company}" job. Job ID: {job_id}!')
                            continue
                    except Exception as e:
                        print_lg(f'Trying to Apply to "{title} | {company}" job. Job ID: {job_id}')

                    if easy_apply_only and not has_easy_apply_button(driver):
                        log_skip_reason("not_easy_apply", title, company, job_id, "easy_apply_only=True")
                        skip_count += 1
                        continue

                    job_link = "https://www.linkedin.com/jobs/view/"+job_id
                    application_link = "Easy Applied"
                    external_outcome = None
                    date_applied = "Pending"
                    hr_link = "Unknown"
                    hr_name = "Unknown"
                    connect_request = "In Development" # Still in development
                    date_listed = "Unknown"
                    skills = "Needs an AI" # Still in development
                    resume = "Pending"
                    reposted = False
                    questions_list = None
                    screenshot_name = "Not Available"
                    jobs_top_card = None

                    try:
                        rejected_jobs, blacklisted_companies, jobs_top_card = check_blacklist(rejected_jobs,job_id,company,blacklisted_companies)
                    except ValueError as e:
                        print_lg(e, 'Skipping this job!\n')
                        log_skip_reason("blacklist", title, company, job_id)
                        failed_job(job_id, job_link, resume, date_listed, "Found Blacklisted words in About Company", e, "Skipped", screenshot_name)
                        skip_count += 1
                        continue
                    except Exception as e:
                        print_lg("Failed to scroll to About Company!")
                        # print_lg(e)



                    # Hiring Manager info
                    try:
                        hr_name, hr_link = extract_hr_info()
                        # if connect_hr:
                        #     driver.switch_to.new_window('tab')
                        #     driver.get(hr_link)
                        #     wait_span_click("More")
                        #     wait_span_click("Connect")
                        #     wait_span_click("Add a note")
                        #     message_box = driver.find_element(By.XPATH, "//textarea")
                        #     message_box.send_keys(connect_request_message)
                        #     if close_tabs: driver.close()
                        #     driver.switch_to.window(linkedIn_tab) 
                        # def message_hr(hr_info_card):
                        #     if not hr_info_card: return False
                        #     hr_info_card.find_element(By.XPATH, ".//span[normalize-space()='Message']").click()
                        #     message_box = driver.find_element(By.XPATH, "//div[@aria-label='Write a messageÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦']")
                        #     message_box.send_keys()
                        #     try_xp(driver, "//button[normalize-space()='Send']")        
                    except Exception:
                        hr_name = "Unknown"
                        hr_link = "Unknown"
                        print_lg(f'HR info extraction failed for "{title}" with Job ID: {job_id}!')


                    # Calculation of date posted
                    try:
                        # try: time_posted_text = find_by_class(driver, "jobs-unified-top-card__posted-date", 2).text
                        # except: 
                        if jobs_top_card:
                            time_posted_text = jobs_top_card.find_element(By.XPATH, './/span[contains(normalize-space(), " ago")]').text
                        else:
                            time_posted_text = find_by_class(driver, "jobs-unified-top-card__posted-date", 2).text
                        print("Time Posted: " + time_posted_text)
                        if time_posted_text.__contains__("Reposted"):
                            reposted = True
                            time_posted_text = time_posted_text.replace("Reposted", "")
                        date_listed = calculate_date_posted(time_posted_text.strip())
                    except Exception as e:
                        print_lg("Failed to calculate the date posted!",e)


                    description, experience_required, skip, reason, message = get_job_description()
                    if skip:
                        log_skip_reason("description_gate", title, company, job_id, str(reason))
                        print_lg(message)
                        failed_job(job_id, job_link, resume, date_listed, reason, message, "Skipped", screenshot_name)
                        rejected_jobs.add(job_id)
                        skip_count += 1
                        continue

                    
                    if use_AI and description != "Unknown":
                        ##> ------ Yang Li : MARKYangL - Feature ------
                        try:
                            if ai_provider.lower() == "openai":
                                skills = ai_extract_skills(aiClient, description)
                            elif ai_provider.lower() == "deepseek":
                                skills = deepseek_extract_skills(aiClient, description)
                            elif ai_provider.lower() == "gemini":
                                skills = gemini_extract_skills(aiClient, description)
                            else:
                                skills = "In Development"
                            print_lg(f"Extracted skills using {ai_provider} AI")
                        except Exception as e:
                            print_lg("Failed to extract skills:", e)
                            skills = "Error extracting skills"
                        ##<

                    uploaded = False
                    # Case 1: Easy Apply Button
                    if has_easy_apply_button(driver):
                        try:
                            errored = ""
                            submitted = False
                            questions_list = set()
                            easy_apply_clicked = click_first_by_xpaths(
                                [
                                    './/button[contains(@class,"jobs-apply-button") and contains(translate(@aria-label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "easy")]',
                                    './/button[contains(@class,"jobs-apply-button") and .//span[contains(translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "easy apply")]]',
                                    './/button[.//span[contains(translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "easy apply")]]',
                                ],
                                reason="easy_apply_button_open_modal",
                                timeout=3,
                            )
                            print_lg(f"APPLY_STEP easy_apply_button_clicked={easy_apply_clicked} job_id={job_id}")
                            if not easy_apply_clicked:
                                raise NoSuchElementException("Easy Apply button detected but could not be clicked.")

                            modal = None
                            for _ in range(2):
                                try:
                                    modal = WebDriverWait(driver, 5).until(
                                        EC.presence_of_element_located((By.CLASS_NAME, "jobs-easy-apply-modal"))
                                    )
                                    break
                                except Exception:
                                    click_first_by_xpaths(
                                        [
                                            './/button[contains(@class,"jobs-apply-button") and contains(translate(@aria-label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "easy")]',
                                            './/button[.//span[contains(translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "easy apply")]]',
                                        ],
                                        reason="easy_apply_button_retry",
                                        timeout=2,
                                    )
                            if modal is None:
                                raise NoSuchElementException("Easy Apply modal did not open.")
                            print_lg(f"APPLY_STEP modal_opened=True job_id={job_id}")

                            resume = "Previous resume"
                            next_counter = 0
                            while next_counter < 15:
                                next_counter += 1
                                questions_list = answer_questions(modal, questions_list, work_location, job_description=description)
                                if useNewResume and not uploaded:
                                    uploaded, resume = upload_resume(modal, default_resume_path)

                                submit_btn = try_xp(modal, './/button[.//span[normalize-space(.)="Submit application"]]', False)
                                if submit_btn:
                                    print_lg(f"APPLY_STEP step_submit job_id={job_id}")
                                    cur_pause_before_submit = pause_before_submit
                                    if cur_pause_before_submit:
                                        decision = pyautogui.confirm(
                                            '1. Please verify your information.\n2. If you edited something, please return to this final screen.\n3. DO NOT CLICK "Submit Application".\n\n\n\n\nYou can turn off "Pause before submit" setting in config.py\nTo TEMPORARILY disable pausing, click "Disable Pause"',
                                            "Confirm your information",
                                            ["Disable Pause", "Discard Application", "Submit Application"]
                                        )
                                        if decision == "Discard Application":
                                            raise Exception("Job application discarded by user!")
                                        pause_before_submit = False if "Disable Pause" == decision else True
                                    follow_company(modal)
                                    safe_click(submit_btn, reason="submit_application_button")
                                    date_applied = datetime.now()
                                    submitted = True
                                    print_lg(f"APPLY_STEP submitted_success=True job_id={job_id}")
                                    if not wait_span_click(driver, "Done", 2):
                                        actions.send_keys(Keys.ESCAPE).perform()
                                    break

                                review_btn = try_xp(modal, './/button[.//span[normalize-space(.)="Review"]]', False)
                                if review_btn:
                                    print_lg(f"APPLY_STEP step_review job_id={job_id}")
                                    safe_click(review_btn, reason="review_button")
                                    buffer(click_gap)
                                    continue

                                next_btn = try_xp(modal, './/button[.//span[normalize-space(.)="Next"]]', False)
                                if next_btn:
                                    print_lg(f"APPLY_STEP step_next job_id={job_id}")
                                    safe_click(next_btn, reason="next_button")
                                    buffer(click_gap)
                                    continue

                                break

                            if not submitted:
                                errored = "submit_not_reached"
                                if next_counter >= 15:
                                    errored = "stuck"
                                    if pause_at_failed_question:
                                        screenshot(driver, job_id, "Needed manual intervention for failed question")
                                        pyautogui.alert("Couldn't answer one or more questions.\nPlease click \"Continue\" once done.\nDO NOT CLICK Back, Next or Review button in LinkedIn.\n\n\n\n\nYou can turn off \"Pause at failed question\" setting in config.py", "Help Needed", "Continue")
                                raise Exception(f"Could not complete Easy Apply flow ({errored}).")

                            if questions_list:
                                print_lg("Answered the following questions...", questions_list)
                                print("\n\n" + "\n".join(str(question) for question in questions_list) + "\n\n")

                        except Exception as e:
                            print_lg("Failed to Easy apply!")
                            log_skip_reason("apply_modal_failed", title, company, job_id, str(e))
                            critical_error_log("Somewhere in Easy Apply process", e)
                            failed_job(job_id, job_link, resume, date_listed, "Problem in Easy Applying", e, application_link, screenshot_name)
                            failed_count += 1
                            discard_job()
                            continue
                    else:
                        # Case 2: Apply externally
                        skip, external_outcome, tabs_count = external_apply(
                            pagination_element,
                            job_id,
                            job_link,
                            resume,
                            date_listed,
                            application_link,
                            screenshot_name,
                            job_description=description,
                        )
                        if dailyEasyApplyLimitReached:
                            print_lg("\n###############  Daily application limit for Easy Apply is reached!  ###############\n")
                            return
                        if skip: continue
                        application_link = external_outcome.application_link if external_outcome else application_link

                    submitted_jobs(
                        job_id,
                        title,
                        company,
                        work_location,
                        work_style,
                        description,
                        experience_required,
                        skills,
                        hr_name,
                        hr_link,
                        resume,
                        reposted,
                        date_listed,
                        date_applied,
                        job_link,
                        application_link,
                        questions_list,
                        connect_request,
                        external_outcome=external_outcome,
                    )
                    if uploaded:   useNewResume = False

                    print_lg(f'Successfully saved "{title} | {company}" job. Job ID: {job_id} info')
                    current_count += 1
                    if application_link == "Easy Applied": easy_applied_count += 1
                    else:   external_jobs_count += 1
                    applied_jobs.add(job_id)



                # Switching to next page
                if pagination_element == None:
                    print_lg("Couldn't find pagination element, probably at the end page of results!")
                    break
                try:
                    pagination_element.find_element(By.XPATH, f"//button[@aria-label='Page {current_page+1}']").click()
                    print_lg(f"\n>-> Now on Page {current_page+1} \n")
                except NoSuchElementException:
                    print_lg(f"\n>-> Didn't find Page {current_page+1}. Probably at the end page of results!\n")
                    break

            print_lg(
                f'Completed search term "{searchTerm}" with location_guard_skips={location_skip_count_this_search} '
                f'and filters_applied={filters_applied}.'
            )

        except StaleElementReferenceException as e:
            print_lg("Stale element encountered while processing jobs. Refreshing list and continuing.", e)
            continue
        except NoSuchElementException as e:
            print_lg("Encountered a non-standard/partial job card while processing listings. Continuing with next search term.", e)
            continue
        except (NoSuchWindowException, WebDriverException) as e:
            print_lg("Browser window closed or session is invalid. Ending application process.", e)
            raise e # Re-raise to be caught by main
        except Exception as e:
            print_lg("Failed to find Job listings!")
            critical_error_log("In Applier", e)
            try:
                print_lg(driver.page_source, pretty=True)
            except Exception as page_source_error:
                print_lg(f"Failed to get page source, browser might have crashed. {page_source_error}")
            # print_lg(e)

        
def run(total_runs: int) -> int:
    if dailyEasyApplyLimitReached:
        return total_runs
    print_lg("\n########################################################################################################################\n")
    print_lg(f"Date and Time: {datetime.now()}")
    print_lg(f"Cycle number: {total_runs}")
    print_lg(f"Currently looking for jobs posted within '{date_posted}' and sorting them by '{sort_by}'")
    print_lg(
        "Run config -> "
        f"easy_apply_only={easy_apply_only}, "
        f"current_experience={current_experience}, "
        f"enforce_search_term_title_match={enforce_search_term_title_match}, "
        f"enforce_target_location_match={enforce_target_location_match}, "
        f"search_location='{search_location}'"
    )
    if current_experience > -1:
        print_lg(
            "Experience gate is ON. Jobs requiring more years than your current_experience "
            "will be skipped. Set current_experience = -1 in config/search.py to apply without this restriction."
        )
    apply_to_jobs(search_terms)
    print_lg("########################################################################################################################\n")
    if not dailyEasyApplyLimitReached:
        print_lg("Sleeping for 10 min...")
        sleep(300)
        print_lg("Few more min... Gonna start with in next 5 min...")
        sleep(300)
    buffer(3)
    return total_runs + 1



chatGPT_tab = False
linkedIn_tab = False

def main() -> None:
    pyautogui.alert("Please consider sponsoring this project at:\n\nhttps://github.com/sponsors/GodsScion\n\n", "Support the project", "Okay")
    total_runs = 1
    try:
        global linkedIn_tab, tabs_count, useNewResume, aiClient, driver
        alert_title = "Error Occurred. Closing Browser!"
        validate_config()
        print_lg("HR enrichment disabled: using LinkedIn HR extraction only (HR Name/HR Link).")
        
        if not os.path.exists(default_resume_path):
            pyautogui.alert(text='Your default resume "{}" is missing! Please update it\'s folder path "default_resume_path" in config.py\n\nOR\n\nAdd a resume with exact name and path (check for spelling mistakes including cases).\n\n\nFor now the bot will continue using your previous upload from LinkedIn!'.format(default_resume_path), title="Missing Resume", button="OK")
            useNewResume = False
        
        # Login to LinkedIn
        tabs_count = len(driver.window_handles)
        driver.get("https://www.linkedin.com/login")
        if not is_logged_in_LN(): login_LN()
        
        linkedIn_tab = driver.current_window_handle

        # # Login to ChatGPT in a new tab for resume customization
        # if use_resume_generator:
        #     try:
        #         driver.switch_to.new_window('tab')
        #         driver.get("https://chat.openai.com/")
        #         if not is_logged_in_GPT(): login_GPT()
        #         open_resume_chat()
        #         global chatGPT_tab
        #         chatGPT_tab = driver.current_window_handle
        #     except Exception as e:
        #         print_lg("Opening OpenAI chatGPT tab failed!")
        if use_AI:
            if ai_provider == "openai":
                aiClient = ai_create_openai_client()
            ##> ------ Yang Li : MARKYangL - Feature ------
            # Create DeepSeek client
            elif ai_provider == "deepseek":
                aiClient = deepseek_create_client()
            elif ai_provider == "gemini":
                aiClient = gemini_create_client()
            ##<

            try:
                about_company_for_ai = " ".join([word for word in (first_name+" "+last_name).split() if len(word) > 3])
                print_lg(f"Extracted about company info for AI: '{about_company_for_ai}'")
            except Exception as e:
                print_lg("Failed to extract about company info!", e)
        
        # Start applying to jobs
        driver.switch_to.window(linkedIn_tab)
        total_runs = run(total_runs)
        while(run_non_stop):
            if cycle_date_posted:
                date_options = ["Any time", "Past month", "Past week", "Past 24 hours"]
                global date_posted
                date_posted = date_options[date_options.index(date_posted)+1 if date_options.index(date_posted)+1 > len(date_options) else -1] if stop_date_cycle_at_24hr else date_options[0 if date_options.index(date_posted)+1 >= len(date_options) else date_options.index(date_posted)+1]
            if alternate_sortby:
                global sort_by
                sort_by = "Most recent" if sort_by == "Most relevant" else "Most relevant"
                total_runs = run(total_runs)
                sort_by = "Most recent" if sort_by == "Most relevant" else "Most relevant"
            total_runs = run(total_runs)
            if dailyEasyApplyLimitReached:
                break
        

    except (NoSuchWindowException, WebDriverException) as e:
        print_lg("Browser window closed or session is invalid. Exiting.", e)
    except KeyboardInterrupt:
        print_lg("Execution interrupted by user (KeyboardInterrupt). Exiting gracefully.")

    except Exception as e:
        critical_error_log("In Applier Main", e)
        # pyautogui.alert expects strings, not Exception objects
        pyautogui.alert(f"{alert_title}\n\n{str(e)}", alert_title, button="OK")

    finally:
        # your existing finally code continues here...
        summary = "Total runs: {}\nJobs Easy Applied: {}\nExternal job links collected: {}\nTotal applied or collected: {}\nFailed jobs: {}\nIrrelevant jobs skipped: {}\n".format(total_runs,easy_applied_count,external_jobs_count,easy_applied_count + external_jobs_count,failed_count,skip_count)
        print_lg(summary)
        print_lg("\n\nTotal runs:                     {}".format(total_runs))
        print_lg("Jobs Easy Applied:              {}".format(easy_applied_count))
        print_lg("External job links collected:   {}".format(external_jobs_count))
        print_lg("                              ----------")
        print_lg("Total applied or collected:     {}".format(easy_applied_count + external_jobs_count))
        print_lg("\nFailed jobs:                    {}".format(failed_count))
        print_lg("Irrelevant jobs skipped:        {}\n".format(skip_count))
        if randomly_answered_questions: print_lg("\n\nQuestions randomly answered:\n  {}  \n\n".format(";\n".join(str(question) for question in randomly_answered_questions)))
        quotes = choice([
            "Never quit. You're one step closer than before. - Sai Vignesh Golla", 
            "All the best with your future interviews, you've got this. - Sai Vignesh Golla", 
            "Keep up with the progress. You got this. - Sai Vignesh Golla", 
            "If you're tired, learn to take rest but never give up. - Sai Vignesh Golla",
            "Success is not final, failure is not fatal, It is the courage to continue that counts. - Winston Churchill (Not a sponsor)",
            "Believe in yourself and all that you are. Know that there is something inside you that is greater than any obstacle. - Christian D. Larson (Not a sponsor)",
            "Every job is a self-portrait of the person who does it. Autograph your work with excellence. - Jessica Guidobono (Not a sponsor)",
            "The only way to do great work is to love what you do. If you haven't found it yet, keep looking. Don't settle. - Steve Jobs (Not a sponsor)",
            "Opportunities don't happen, you create them. - Chris Grosser (Not a sponsor)",
            "The road to success and the road to failure are almost exactly the same. The difference is perseverance. - Colin R. Davis (Not a sponsor)",
            "Obstacles are those frightful things you see when you take your eyes off your goal. - Henry Ford (Not a sponsor)",
            "The only limit to our realization of tomorrow will be our doubts of today. - Franklin D. Roosevelt (Not a sponsor)",
            ])
        sponsors = "Be the first to have your name here!"
        timeSaved = (easy_applied_count * 80) + (external_jobs_count * 20) + (skip_count * 10)
        timeSavedMsg = ""
        if timeSaved > 0:
            timeSaved += 60
            timeSavedMsg = f"In this run, you saved approx {round(timeSaved/60)} mins ({timeSaved} secs), please consider supporting the project."
        msg = f"{quotes}\n\n\n{timeSavedMsg}\nYou can also get your quote and name shown here, or prioritize your bug reports by supporting the project at:\n\nhttps://github.com/sponsors/GodsScion\n\n\nSummary:\n{summary}\n\n\nBest regards,\nSai Vignesh Golla\nhttps://www.linkedin.com/in/saivigneshgolla/\n\nTop Sponsors:\n{sponsors}"
        pyautogui.alert(msg, "Exiting..")
        print_lg(msg,"Closing the browser...")
        if tabs_count >= 10:
            msg = "NOTE: IF YOU HAVE MORE THAN 10 TABS OPENED, PLEASE CLOSE OR BOOKMARK THEM!\n\nOr it's highly likely that application will just open browser and not do anything next time!" 
            pyautogui.alert(msg,"Info")
            print_lg("\n"+msg)
        ##> ------ Yang Li : MARKYangL - Feature ------
        if use_AI and aiClient:
            try:
                if ai_provider.lower() == "openai":
                    ai_close_openai_client(aiClient)
                elif ai_provider.lower() == "deepseek":
                    ai_close_openai_client(aiClient)
                elif ai_provider.lower() == "gemini":
                    pass # Gemini client does not need to be closed
                print_lg(f"Closed {ai_provider} AI client.")
            except Exception as e:
                print_lg("Failed to close AI client:", e)
        ##<
        try:
            if driver:
                driver.quit()
                driver = None
                open_chrome_module.driver = None
        except WebDriverException as e:
            print_lg("Browser already closed.", e)
        except Exception as e: 
            critical_error_log("When quitting...", e)


if __name__ == "__main__":
    main()



