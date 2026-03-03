from __future__ import annotations

from urllib.parse import urlparse

from pyautogui import confirm

from .base import PortalAdapter, PortalSessionState, FillResult, ReviewResult
from .common_fields import (
    detect_captcha,
    detect_login_required,
    maybe_pause_for_manual_auth,
    fill_common_fields,
    fill_unknown_fields_with_ai,
    upload_resume,
)


def _derive_portal_name(url: str) -> str:
    try:
        host = (urlparse(url).netloc or "").lower()
        host = host.replace("www.", "")
        if not host:
            return "generic"
        core = host.split(".")[0]
        return core if core else "generic"
    except Exception:
        return "generic"


class GenericExternalAdapter(PortalAdapter):
    portal_name = "generic"

    def __init__(self, url: str):
        self._url = url or ""
        self.portal_name = _derive_portal_name(self._url)

    def detect(self, url: str) -> bool:
        return True

    def prepare(self, driver, auth_mode: str = "manual_first_login") -> PortalSessionState:
        state = PortalSessionState(
            login_required=detect_login_required(driver),
            captcha_detected=detect_captcha(driver),
            notes=[],
        )
        if state.captcha_detected:
            state.notes.append("CAPTCHA detected")
        maybe_pause_for_manual_auth(driver, auth_mode, self.portal_name)
        return state

    def fill(self, driver, profile: dict, ai_client, job_context: dict) -> FillResult:
        filled_fields: list[str] = []
        unanswered_questions: list[str] = []
        notes: list[str] = []

        fill_common_fields(driver, profile, filled_fields)
        if upload_resume(driver, profile.get("resume_path", "")):
            filled_fields.append("resume_upload")

        fill_unknown_fields_with_ai(
            driver=driver,
            ai_client=ai_client,
            profile=profile,
            job_context=job_context,
            filled_fields=filled_fields,
            unanswered_questions=unanswered_questions,
            use_ai=bool(ai_client),
        )

        status = "filled" if filled_fields else "needs_manual"
        if unanswered_questions:
            status = "needs_manual"
            notes.append("Some fields need manual completion")
        if not filled_fields:
            notes.append("No standard fields found by generic adapter")

        return FillResult(
            status=status,
            filled_fields=filled_fields,
            unanswered_questions=unanswered_questions,
            portal_name=self.portal_name,
            final_url=driver.current_url,
            notes=notes,
        )

    def pause_for_review(self, driver) -> ReviewResult:
        decision = confirm(
            f"{self.portal_name} form autofill attempt completed.\nReview fields and submit manually.\nClick Continue after review.",
            "External Apply Review",
            ["Continue", "Mark Manual Needed"],
        )
        return ReviewResult(confirmed=(decision == "Continue"), note=decision or "")

