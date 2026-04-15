from __future__ import annotations

import argparse
import re
from pathlib import Path


SECTION_RE = re.compile(r"^## @(?P<handle>[A-Za-z0-9._]+)\s*$", re.MULTILINE)
FOLLOWERS_RE = re.compile(r"^- Followers:\s*(?P<followers>\d+)\s*$", re.MULTILINE)
PROFILE_RE = re.compile(r"^- Profile:\s*\[@(?P<handle>[A-Za-z0-9._]+)\]\((?P<url>https://www\.instagram\.com/[^)]+)\)\s*$", re.MULTILINE)


def parse_sections(markdown: str) -> list[dict]:
    matches = list(SECTION_RE.finditer(markdown))
    sections: list[dict] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        block = markdown[start:end].strip()
        followers_match = FOLLOWERS_RE.search(block)
        profile_match = PROFILE_RE.search(block)
        if not followers_match or not profile_match:
            continue
        sections.append(
            {
                "handle": match.group("handle"),
                "followers": int(followers_match.group("followers")),
                "url": profile_match.group("url"),
                "block": block,
            }
        )
    return sections


def rebuild_markdown(sections: list[dict], min_followers: int, max_followers: int) -> str:
    lines = [
        "# Shortlisted Bloggers For Phase 1",
        "",
        f"- Total shortlisted bloggers in follower range: {len(sections)}",
        f"- Follower range: {min_followers} to {max_followers if max_followers else 'unbounded'}",
        "- Source: following discovery shortlist, deduplicated across all seed bloggers",
        "",
    ]
    if not sections:
        lines.append("No shortlisted bloggers in the configured follower range yet.")
        lines.append("")
        return "\n".join(lines).strip() + "\n"

    for section in sections:
        lines.append(section["block"])
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def filter_sections(sections: list[dict], min_followers: int, max_followers: int) -> list[dict]:
    filtered = [
        section
        for section in sections
        if section["followers"] >= min_followers and (not max_followers or section["followers"] <= max_followers)
    ]
    filtered.sort(key=lambda item: (-item["followers"], item["handle"]))
    return filtered


def main() -> int:
    parser = argparse.ArgumentParser(description="Filter shortlisted following bloggers by follower range.")
    parser.add_argument(
        "--md",
        default="artifacts/instagram_brand_search/following/shortlisted_bloggers_for_phase1.md",
        help="Path to shortlisted markdown file.",
    )
    parser.add_argument(
        "--txt",
        default="artifacts/instagram_brand_search/following/shortlisted_bloggers_for_phase1.txt",
        help="Path to output txt file with profile URLs.",
    )
    parser.add_argument("--min-followers", type=int, default=300000)
    parser.add_argument("--max-followers", type=int, default=800000)
    args = parser.parse_args()

    md_path = Path(args.md)
    txt_path = Path(args.txt)
    markdown = md_path.read_text(encoding="utf-8-sig")
    sections = parse_sections(markdown)
    filtered = filter_sections(sections, args.min_followers, args.max_followers)

    md_path.write_text(
        rebuild_markdown(filtered, args.min_followers, args.max_followers),
        encoding="utf-8-sig",
    )
    txt_path.write_text(
        "\n".join(section["url"] for section in filtered).strip() + ("\n" if filtered else ""),
        encoding="utf-8-sig",
    )

    print(
        {
            "input_sections": len(sections),
            "filtered_sections": len(filtered),
            "min_followers": args.min_followers,
            "max_followers": args.max_followers,
            "md": str(md_path),
            "txt": str(txt_path),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())



