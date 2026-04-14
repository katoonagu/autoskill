from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class PersonContact:
    """A named decision-maker or department contact."""

    full_name: str = ""
    position: str = ""
    department: str = ""  # "PR" | "Marketing" | "Leadership" | "HR" | "Other"
    email: str = ""
    phone: str = ""
    telegram: str = ""
    instagram: str = ""
    linkedin: str = ""
    source_url: str = ""
    confidence: float = 0.0


@dataclass
class CompanyCard:
    """Full enrichment result for one target company."""

    company_name: str = ""
    company_name_aliases: list[str] = field(default_factory=list)
    legal_entity: str = ""
    inn: str = ""
    industry: str = ""
    website: str = ""
    website_domain: str = ""
    website_confirmed: bool = False

    pr_emails: list[str] = field(default_factory=list)
    marketing_emails: list[str] = field(default_factory=list)
    partnership_emails: list[str] = field(default_factory=list)
    general_emails: list[str] = field(default_factory=list)
    deduced_emails: list[str] = field(default_factory=list)
    all_emails: list[str] = field(default_factory=list)

    phones: list[str] = field(default_factory=list)
    decision_makers: list[PersonContact] = field(default_factory=list)

    telegram: str = ""
    instagram: str = ""
    vk: str = ""

    hh_employer_url: str = ""
    hh_active_marketing_vacancies: int = 0
    hh_hr_contact_name: str = ""
    hh_hr_contact_email: str = ""
    hh_hr_contact_phone: str = ""

    rusprofile_url: str = ""
    ceo_name: str = ""

    sources: list[str] = field(default_factory=list)
    enrichment_steps_completed: list[int] = field(default_factory=list)
    enrichment_level: int = 0
    confidence: float = 0.0
    errors: list[str] = field(default_factory=list)

    recommended_entry_route: str = ""
    pitch_angle: str = ""
    company_video_needs: str = ""
    portfolio_match: str = ""

    created_at: str = ""
    last_updated: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.last_updated:
            self.last_updated = self.created_at


@dataclass
class EnrichmentTask:
    """Input for enriching one company."""

    company_name: str = ""
    aliases: list[str] = field(default_factory=list)
    sector: str = ""
    priority: str = "medium"
    note: str = ""
    steps_to_run: list[int] = field(default_factory=lambda: [1, 2, 3, 4, 5, 6])


DEPARTMENT_EMAIL_PREFIXES = [
    "pr",
    "press",
    "media",
    "marketing",
    "reklama",
    "adv",
    "advertising",
    "partnership",
    "sotrudnichestvo",
    "cooperation",
    "info",
    "hello",
    "office",
    "reception",
]

PR_EMAIL_PREFIXES = ("pr", "press", "media", "smi", "pressa")
MARKETING_EMAIL_PREFIXES = ("marketing", "reklama", "adv", "advertising", "brand")
PARTNERSHIP_EMAIL_PREFIXES = ("partnership", "sotrudnichestvo", "cooperation", "b2b", "sales")

CONTACT_PAGE_PATHS = (
    "/contacts",
    "/kontakty",
    "/contact",
    "/about",
    "/o-kompanii",
    "/press",
    "/press-center",
    "/press-centr",
    "/presscenter",
    "/dlya-smi",
    "/for-media",
    "/partners",
    "/sotrudnichestvo",
    "/cooperation",
    "/team",
    "/komanda",
    "/rukovodstvo",
    "/management",
    "/leadership",
    "/about/contacts",
    "/company/contacts",
)

DECISION_MAKER_POSITIONS_RU = (
    "директор по маркетингу",
    "директор по pr",
    "директор по коммуникациям",
    "руководитель отдела маркетинга",
    "руководитель pr",
    "руководитель пресс-службы",
    "начальник отдела маркетинга",
    "начальник отдела рекламы",
    "вице-президент по маркетингу",
    "вп по маркетингу",
    "head of marketing",
    "head of pr",
    "head of communications",
    "cmo",
    "chief marketing officer",
    "пресс-секретарь",
    "pr-менеджер",
    "pr менеджер",
    "бренд-менеджер",
    "бренд менеджер",
    "маркетинг-директор",
    "генеральный директор",
    "основатель",
    "сооснователь",
    "владелец",
    "учредитель",
)
