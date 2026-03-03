from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PortalSessionState:
    login_required: bool = False
    captcha_detected: bool = False
    notes: list[str] = field(default_factory=list)


@dataclass
class FillResult:
    status: str
    filled_fields: list[str] = field(default_factory=list)
    unanswered_questions: list[str] = field(default_factory=list)
    portal_name: str = "unknown"
    final_url: str = ""
    notes: list[str] = field(default_factory=list)


@dataclass
class ReviewResult:
    confirmed: bool
    note: str = ""


@dataclass
class ExternalApplyOutcome:
    application_link: str
    portal_name: str = "unknown"
    apply_type: str = "External"
    apply_status: str = "saved_link_only"
    notes: str = ""
    filled_fields: list[str] = field(default_factory=list)
    unanswered_questions: list[str] = field(default_factory=list)


class PortalAdapter(ABC):
    portal_name: str = "unknown"

    @abstractmethod
    def detect(self, url: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def prepare(self, driver: Any, auth_mode: str = "manual_first_login") -> PortalSessionState:
        raise NotImplementedError

    @abstractmethod
    def fill(self, driver: Any, profile: dict, ai_client: Any, job_context: dict) -> FillResult:
        raise NotImplementedError

    @abstractmethod
    def pause_for_review(self, driver: Any) -> ReviewResult:
        raise NotImplementedError

