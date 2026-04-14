"""Email validation and pattern deduction.

Two capabilities:
1. SMTP validation -- check if email exists without sending
2. Pattern deduction -- if pr@domain.ru works, try marketing@domain.ru etc.
"""

from __future__ import annotations

import re
import smtplib
import socket

from .models import DEPARTMENT_EMAIL_PREFIXES


def validate_email_smtp(email: str, *, timeout: int = 10) -> str:
    """Check if an email address exists via SMTP RCPT TO.

    Returns:
        "valid"       -- mailbox exists (250 response)
        "invalid"     -- mailbox rejected (550 response)
        "unknown"     -- server didn't give a clear answer (greylisting, catch-all)
        "error"       -- connection/DNS failure
    """
    if not email or "@" not in email:
        return "invalid"

    domain = email.split("@", 1)[1]
    try:
        mx_records = _get_mx_hosts(domain)
    except Exception:
        return "error"

    if not mx_records:
        return "error"

    for mx_host in mx_records[:2]:
        try:
            with smtplib.SMTP(mx_host, 25, timeout=timeout) as smtp:
                smtp.ehlo("mail.example.com")
                code_from, _ = smtp.mail("test@example.com")
                if code_from >= 400:
                    continue
                code_rcpt, _ = smtp.rcpt(email)
                smtp.quit()
                if code_rcpt == 250:
                    return "valid"
                if code_rcpt == 550 or code_rcpt == 551 or code_rcpt == 553:
                    return "invalid"
                return "unknown"
        except (smtplib.SMTPException, socket.error, OSError):
            continue

    return "error"


def _get_mx_hosts(domain: str) -> list[str]:
    """Resolve MX records for a domain, sorted by priority."""
    import dns.resolver  # type: ignore[import-untyped]

    answers = dns.resolver.resolve(domain, "MX")
    mx_list = sorted(answers, key=lambda r: r.preference)
    return [str(r.exchange).rstrip(".") for r in mx_list]


def deduce_department_emails(known_email: str, *, validate: bool = False) -> list[dict]:
    """Given one email (e.g. pr@ozon.ru), generate sibling department emails.

    Returns list of {"email": "...", "prefix": "...", "status": "deduced"|"valid"|"invalid"}.
    """
    if not known_email or "@" not in known_email:
        return []

    domain = known_email.split("@", 1)[1]
    known_prefix = known_email.split("@", 1)[0].lower()
    results: list[dict] = []

    for prefix in DEPARTMENT_EMAIL_PREFIXES:
        if prefix == known_prefix:
            continue
        candidate = f"{prefix}@{domain}"
        status = "deduced"
        if validate:
            smtp_result = validate_email_smtp(candidate)
            status = smtp_result
        results.append({
            "email": candidate,
            "prefix": prefix,
            "status": status,
        })

    return results


def classify_email(email: str) -> str:
    """Classify an email into department category.

    Returns: "pr" | "marketing" | "partnership" | "general" | "personal" | "support"
    """
    if not email or "@" not in email:
        return "general"

    prefix = email.split("@", 1)[0].lower()

    if any(prefix.startswith(p) for p in ("pr", "press", "media", "smi")):
        return "pr"
    if any(prefix.startswith(p) for p in ("marketing", "reklama", "adv", "brand")):
        return "marketing"
    if any(prefix.startswith(p) for p in ("partner", "sotrudnich", "coop", "b2b", "sales")):
        return "partnership"
    if any(prefix.startswith(p) for p in ("support", "help", "service")):
        return "support"
    if any(prefix.startswith(p) for p in ("info", "hello", "office", "reception")):
        return "general"

    # If prefix looks like a person's name (contains dots or is short)
    if "." in prefix or len(prefix) <= 3:
        return "personal"

    return "general"
