from __future__ import annotations

from typing import Any

from pyautogui import alert
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.select import Select

from modules.helpers import print_lg


def build_profile() -> dict[str, str]:
    import os
    from config.personals import first_name, middle_name, last_name, phone_number, current_city, street, state, zipcode, country
    from config.secrets import username
    from config.questions import (
        default_resume_path,
        years_of_experience,
        require_visa,
        website,
        linkedIn,
        desired_salary,
        current_ctc,
        notice_period,
        linkedin_summary,
        cover_letter,
        user_information_all,
    )

    full_name = f"{first_name.strip()} {middle_name.strip()} {last_name.strip()}".replace("  ", " ").strip()
    resume_path = default_resume_path.strip()
    if resume_path:
        resume_path = os.path.abspath(resume_path)

    return {
        "first_name": first_name.strip(),
        "middle_name": middle_name.strip(),
        "last_name": last_name.strip(),
        "full_name": full_name,
        "email": username.strip(),
        "phone": str(phone_number).strip(),
        "city": current_city.strip(),
        "street": street.strip(),
        "state": state.strip(),
        "zipcode": zipcode.strip(),
        "country": country.strip(),
        "resume_path": resume_path,
        "years_of_experience": str(years_of_experience).strip(),
        "require_visa": str(require_visa).strip(),
        "website": website.strip(),
        "linkedin": linkedIn.strip(),
        "desired_salary": str(desired_salary).strip(),
        "current_ctc": str(current_ctc).strip(),
        "notice_period": str(notice_period).strip(),
        "linkedin_summary": linkedin_summary.strip(),
        "cover_letter": cover_letter.strip(),
        "user_information_all": user_information_all.strip(),
    }


def detect_login_required(driver: Any) -> bool:
    page = (driver.page_source or "").lower()
    keywords = ["sign in", "log in", "create account", "continue with", "password"]
    return any(word in page for word in keywords)


def detect_captcha(driver: Any) -> bool:
    page = (driver.page_source or "").lower()
    return "captcha" in page or "i'm not a robot" in page or "recaptcha" in page


def maybe_pause_for_manual_auth(driver: Any, auth_mode: str, portal_name: str) -> bool:
    if auth_mode == "skip_auth_required":
        return False
    if detect_login_required(driver):
        if auth_mode == "manual_first_login":
            alert(
                f"{portal_name}: Login/account action is needed on this page.\nComplete it manually, then click OK to continue.",
                "External Portal Login Required",
                "Continue",
            )
            return True
    return True


def _visible_enabled(element: WebElement) -> bool:
    try:
        return element.is_displayed() and element.is_enabled()
    except Exception:
        return False


def _set_text(element: WebElement, value: str) -> bool:
    if not value:
        return False
    try:
        element.clear()
        element.send_keys(value)
        return True
    except Exception:
        return False


def _fill_by_css(driver: Any, css: str, value: str) -> bool:
    if not value:
        return False
    try:
        elements = driver.find_elements(By.CSS_SELECTOR, css)
        for ele in elements:
            if _visible_enabled(ele) and _set_text(ele, value):
                return True
    except Exception:
        return False
    return False


def _choose_select_option(select_ele: WebElement, value: str) -> bool:
    if not value:
        return False
    try:
        sel = Select(select_ele)
        for option in sel.options:
            if option.text.strip().lower() == value.strip().lower():
                sel.select_by_visible_text(option.text)
                return True
        for option in sel.options:
            if value.strip().lower() in option.text.strip().lower():
                sel.select_by_visible_text(option.text)
                return True
    except Exception:
        return False
    return False


def fill_common_fields(driver: Any, profile: dict[str, str], filled_fields: list[str]) -> None:
    mapping = [
        ("full_name", "input[name*='name' i], input[id*='name' i], input[autocomplete='name']"),
        ("first_name", "input[name*='first' i], input[id*='first' i], input[autocomplete='given-name']"),
        ("last_name", "input[name*='last' i], input[id*='last' i], input[autocomplete='family-name']"),
        ("email", "input[type='email'], input[name*='email' i], input[id*='email' i], input[autocomplete='email']"),
        ("phone", "input[type='tel'], input[name*='phone' i], input[id*='phone' i]"),
        ("city", "input[name*='city' i], input[id*='city' i]"),
        ("state", "input[name*='state' i], input[id*='state' i], input[name*='province' i]"),
        ("zipcode", "input[name*='zip' i], input[id*='zip' i], input[name*='postal' i]"),
        ("country", "input[name*='country' i], input[id*='country' i]"),
        ("website", "input[name*='website' i], input[id*='website' i], input[name*='portfolio' i]"),
        ("linkedin", "input[name*='linkedin' i], input[id*='linkedin' i]"),
        ("desired_salary", "input[name*='salary' i], input[id*='salary' i], input[name*='ctc' i]"),
        ("notice_period", "input[name*='notice' i], input[id*='notice' i]"),
        ("years_of_experience", "input[name*='experience' i], input[id*='experience' i]"),
    ]
    for key, css in mapping:
        if _fill_by_css(driver, css, profile.get(key, "")):
            filled_fields.append(key)

    # Common textarea fields.
    _fill_by_css(driver, "textarea[name*='summary' i], textarea[id*='summary' i]", profile.get("linkedin_summary", ""))
    _fill_by_css(driver, "textarea[name*='cover' i], textarea[id*='cover' i], textarea[name*='letter' i]", profile.get("cover_letter", ""))

    # Common yes/no selects.
    try:
        selects = driver.find_elements(By.TAG_NAME, "select")
        for select_ele in selects:
            if not _visible_enabled(select_ele):
                continue
            descriptor = (
                f"{select_ele.get_attribute('name')} {select_ele.get_attribute('id')} "
                f"{select_ele.get_attribute('aria-label')}"
            ).lower()
            if "sponsor" in descriptor or "visa" in descriptor:
                value = "No" if profile.get("require_visa", "No").lower() == "no" else "Yes"
                if _choose_select_option(select_ele, value):
                    filled_fields.append("require_visa")
            if "work authorization" in descriptor:
                value = "Yes" if profile.get("require_visa", "No").lower() == "no" else "No"
                if _choose_select_option(select_ele, value):
                    filled_fields.append("work_authorization")
    except Exception:
        pass


def upload_resume(driver: Any, resume_path: str) -> bool:
    if not resume_path:
        return False
    try:
        inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
        for file_input in inputs:
            if not _visible_enabled(file_input):
                continue
            file_input.send_keys(resume_path)
            return True
    except Exception as e:
        print_lg("Resume upload failed", e)
    return False


def _question_from_input(driver: Any, field: WebElement) -> str:
    text = (field.get_attribute("aria-label") or "").strip()
    if text:
        return text
    field_id = (field.get_attribute("id") or "").strip()
    if field_id:
        try:
            label = driver.find_element(By.CSS_SELECTOR, f"label[for='{field_id}']")
            if label and label.text.strip():
                return label.text.strip()
        except Exception:
            pass
    return (field.get_attribute("name") or field.get_attribute("placeholder") or "Unknown question").strip()


def fill_unknown_fields_with_ai(
    driver: Any,
    ai_client: Any,
    profile: dict[str, str],
    job_context: dict[str, str],
    filled_fields: list[str],
    unanswered_questions: list[str],
    use_ai: bool,
) -> None:
    candidates: list[WebElement] = []
    try:
        candidates.extend(driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input[type='email'], input[type='tel'], input[type='number']"))
        candidates.extend(driver.find_elements(By.CSS_SELECTOR, "textarea"))
    except Exception:
        return

    ai_fn = None
    if use_ai and ai_client:
        try:
            from modules.ai.openaiConnections import ai_answer_portal_question

            ai_fn = ai_answer_portal_question
        except Exception:
            ai_fn = None

    attempted = 0
    for field in candidates:
        if attempted >= 12:
            break
        if not _visible_enabled(field):
            continue
        try:
            existing = (field.get_attribute("value") or "").strip()
            if existing:
                continue
            question = _question_from_input(driver, field)
            if not question or question == "Unknown question":
                continue

            answer = ""
            if ai_fn:
                q_type = "textarea" if field.tag_name.lower() == "textarea" else "text"
                answer = ai_fn(
                    ai_client,
                    question,
                    question_type=q_type,
                    options=None,
                    user_information_all=profile.get("user_information_all"),
                    job_description=job_context.get("job_description"),
                    about_company=job_context.get("about_company"),
                )
                answer = str(answer).strip() if answer is not None else ""

            if not answer:
                unanswered_questions.append(question)
                continue

            if _set_text(field, answer):
                filled_fields.append(question)
            else:
                unanswered_questions.append(question)
            attempted += 1
        except Exception:
            continue
