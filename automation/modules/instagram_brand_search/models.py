from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class BloggerTarget:
    profile_url: str
    handle: str = ""
    niche_hint: str = ""
    notes: str = ""
    source_kind: str = "seed"
    source_blogger_handle: str = ""
    source_blogger_url: str = ""


@dataclass
class BloggerCheckpoint:
    profile_url: str
    current_post_url: str = ""
    current_post_date_iso: str = ""
    last_processed_shortcode: str = ""
    processed_posts_count: int = 0
    processed_post_urls: list[str] = field(default_factory=list)
    processed_candidate_keys: list[str] = field(default_factory=list)


@dataclass
class MentionCandidate:
    blogger_handle: str
    source_post_url: str
    candidate_handle: str
    source_post_date_iso: str = ""
    source_authors: list[str] = field(default_factory=list)
    visible_context: str = ""
    caption_text: str = ""
    source_type: str = ""
    ad_likelihood: str = ""
    ad_reasoning: str = ""


@dataclass
class BrandAssessment:
    handle: str
    profile_url: str
    is_brand: bool
    account_kind: str = ""
    outreach_fit: str = ""
    brand_likelihood: str = ""
    ad_likelihood: str = ""
    niche: str = ""
    confidence: str = ""
    reasoning: str = ""
    display_name: str = ""
    bio: str = ""
    category_label: str = ""
    posts_text: str = ""
    followers_text: str = ""
    external_link: str = ""
    screenshot_path: str = ""
    source_posts: list[str] = field(default_factory=list)


@dataclass
class PostSnapshot:
    post_url: str
    post_date: datetime | None
    post_date_iso: str = ""
    authors: list[str] = field(default_factory=list)
    caption_text: str = ""
    candidate_handles: list[str] = field(default_factory=list)
    ad_likelihood: str = ""
    ad_reasoning: str = ""


@dataclass
class BloggerRunStats:
    profile_url: str
    handle: str = ""
    scanned_posts: int = 0
    candidate_mentions: int = 0
    accepted_brand_handles: list[str] = field(default_factory=list)
    stopped_due_to_date: bool = False


@dataclass
class FollowingCandidate:
    source_blogger_handle: str
    source_blogger_url: str
    handle: str
    profile_url: str
    display_name: str = ""
    bio: str = ""
    category_label: str = ""
    followers_text: str = ""
    followers_count: int = 0
    external_link: str = ""
    screenshot_path: str = ""
    is_female_candidate: bool = False
    female_confidence: str = ""
    female_reasoning: str = ""
    is_brand_like: bool = False
    brand_confidence: str = ""
    brand_reasoning: str = ""
    matched_priority_niche: str = ""
    qualifies_followers_threshold: bool = False
    is_selected_target: bool = False
