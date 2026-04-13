from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from automation.modules.instagram_brand_search.recipe import canonical_handle, write_markdown_outputs, write_simple_xlsx
from automation.modules.instagram_brand_search.state import InstagramBrandSearchState


NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


@dataclass
class Snapshot:
    source_path: Path
    source_type: str
    label: str
    mtime: float
    sha256: str
    content_signature: str
    brands_count: int
    sources_count: int
    blogger_summary_count: int


def resolve_project_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def load_job_config() -> dict:
    job_path = PROJECT_ROOT / "automation" / "modules" / "instagram_brand_search" / "job.yaml"
    job = yaml.safe_load(job_path.read_text(encoding="utf-8"))
    job["state"]["state_file"] = str(resolve_project_path(job["state"]["state_file"]))
    for key, raw_path in list(job.get("outputs", {}).items()):
        job["outputs"][key] = str(resolve_project_path(raw_path))
    return job


def rebuild_live_exports() -> tuple[dict, InstagramBrandSearchState]:
    job = load_job_config()
    state_path = Path(job["state"]["state_file"])
    state = InstagramBrandSearchState.load(state_path)
    write_markdown_outputs(job, state)
    return job, state


def xlsx_sheet_rows(path: Path) -> dict[str, list[list[str]]]:
    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for si in shared_root.findall("a:si", NS):
                shared_strings.append("".join(text_node.text or "" for text_node in si.findall(".//a:t", NS)))
        result: dict[str, list[list[str]]] = {}
        for sheet in workbook.find("a:sheets", NS):
            name = sheet.attrib["name"]
            rel_id = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            raw_target = rel_map[rel_id]
            if raw_target.startswith("/"):
                target = raw_target.lstrip("/")
            elif raw_target.startswith("xl/"):
                target = raw_target
            else:
                target = "xl/" + raw_target
            root = ET.fromstring(archive.read(target))
            data = root.find("a:sheetData", NS)
            rows: list[list[str]] = []
            for row in data.findall("a:row", NS) if data is not None else []:
                values: list[str] = []
                for cell in row.findall("a:c", NS):
                    cell_type = cell.attrib.get("t", "")
                    if cell_type == "inlineStr":
                        text = "".join(text_node.text or "" for text_node in cell.findall(".//a:t", NS))
                        values.append(text)
                    elif cell_type == "s":
                        index_text = cell.findtext("a:v", default="", namespaces=NS).strip()
                        if index_text.isdigit() and int(index_text) < len(shared_strings):
                            values.append(shared_strings[int(index_text)])
                        else:
                            values.append(index_text)
                    else:
                        values.append(cell.findtext("a:v", default="", namespaces=NS))
                rows.append(values)
            result[name] = rows
        return result


def sheet_records(path: Path, sheet_name: str) -> list[dict[str, str]]:
    rows = xlsx_sheet_rows(path).get(sheet_name, [])
    if not rows:
        return []
    headers = rows[0]
    records: list[dict[str, str]] = []
    for row in rows[1:]:
        padded = row + [""] * max(0, len(headers) - len(row))
        records.append({headers[index]: padded[index] for index in range(len(headers))})
    return records


def sheet_rows(path: Path, sheet_name: str) -> list[list[str]]:
    return xlsx_sheet_rows(path).get(sheet_name, [])


def normalize_export_sheet_rows(sheet_name: str, rows: list[list[str]]) -> list[list[object]]:
    if not rows:
        return []
    if sheet_name != "Brands":
        return rows

    header = list(rows[0])
    body = [list(row) for row in rows[1:]]

    if "Sources Count" in header:
        header[header.index("Sources Count")] = "Source Posts Count"

    if "Followers Count" in header:
        idx = header.index("Followers Count")
        nonzero_found = False
        for row in body:
            value = row[idx] if idx < len(row) else ""
            if str(value).strip() not in {"", "0", "0.0"}:
                nonzero_found = True
                break
        if not nonzero_found:
            header.pop(idx)
            for row in body:
                if idx < len(row):
                    row.pop(idx)

    return [header] + body


def row_counts(path: Path) -> tuple[int, int, int]:
    sheets = xlsx_sheet_rows(path)
    return (
        max(len(sheets.get("Brands", [])) - 1, 0),
        max(len(sheets.get("Sources", [])) - 1, 0),
        max(len(sheets.get("Blogger Summary", [])) - 1, 0),
    )


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def workbook_content_signature(path: Path) -> str:
    sheets = xlsx_sheet_rows(path)
    payload = {
        "Brands": sheets.get("Brands", []),
        "Sources": sheets.get("Sources", []),
        "Blogger Summary": sheets.get("Blogger Summary", []),
    }
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sort_key_for_label(label: str, mtime: float) -> tuple[str, float]:
    match = re.match(r"^(\d{8}_\d{6})", label)
    return ((match.group(1) if match else f"{mtime:.6f}"), mtime)


def discover_snapshots(brands_dir: Path) -> list[Snapshot]:
    historical_candidates: list[tuple[Path, str, str]] = []

    backup_root = PROJECT_ROOT / "output" / "instagram_brand_search" / "_relaunch_backups"
    if backup_root.exists():
        for path in sorted(backup_root.glob("*/brands/brand_links.xlsx")):
            historical_candidates.append((path, "backup", path.parents[1].name))

    playwright_root = PROJECT_ROOT / "output" / "playwright"
    if playwright_root.exists():
        for path in sorted(playwright_root.glob("*/exports/brand_links.xlsx")):
            run_dir = path.parents[1].name
            if "manual_validation" in run_dir:
                continue
            label = run_dir.replace("_instagram_brand_search", "")
            historical_candidates.append((path, "playwright", label))

    candidates = list(historical_candidates)
    if not historical_candidates:
        current_live = brands_dir / "brand_links.xlsx"
        if current_live.exists():
            candidates.append((current_live, "current", "current_live"))

    grouped: dict[str, Snapshot] = {}
    priority = {"backup": 0, "playwright": 1, "current": 2}
    for path, source_type, label in candidates:
        sha = file_sha256(path)
        content_signature = workbook_content_signature(path)
        brands_count, sources_count, blogger_summary_count = row_counts(path)
        snapshot = Snapshot(
            source_path=path,
            source_type=source_type,
            label=label,
            mtime=path.stat().st_mtime,
            sha256=sha,
            content_signature=content_signature,
            brands_count=brands_count,
            sources_count=sources_count,
            blogger_summary_count=blogger_summary_count,
        )
        current = grouped.get(content_signature)
        if current is None or priority[source_type] < priority[current.source_type]:
            grouped[content_signature] = snapshot

    return sorted(grouped.values(), key=lambda item: sort_key_for_label(item.label, item.mtime))


def copy_if_exists(source: Path, target: Path) -> None:
    if not source.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def safe_int(value: str) -> int:
    try:
        return int(str(value).strip() or "0")
    except ValueError:
        return 0


def load_brand_dossier_metrics() -> dict[str, dict[str, int]]:
    dossiers_root = PROJECT_ROOT / "output" / "brand_intelligence"
    metrics: dict[str, dict[str, int]] = {}
    if not dossiers_root.exists():
        return metrics
    for dossier_path in sorted(dossiers_root.glob("*/brand_dossier.json")):
        try:
            payload = json.loads(dossier_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        handle = canonical_handle(str(payload.get("brand_handle") or dossier_path.parent.name))
        if not handle:
            continue
        profile = payload.get("instagram_profile") or {}
        metrics[handle] = {
            "followers": safe_int(profile.get("followers", 0)),
            "posts": safe_int(profile.get("posts", 0)),
        }
    return metrics


def load_live_profile_metrics(tables_dir: Path) -> dict[str, dict[str, int]]:
    cache_path = tables_dir / "live_profile_counts.json"
    if not cache_path.exists():
        return {}
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    metrics: dict[str, dict[str, int]] = {}
    if isinstance(payload, dict):
        for raw_handle, item in payload.items():
            canonical = canonical_handle(str(raw_handle))
            if not canonical or not isinstance(item, dict):
                continue
            metrics[canonical] = {
                "followers": safe_int(item.get("followers", 0)),
                "posts": safe_int(item.get("posts", 0)),
            }
    return metrics


def parse_run_sources(snapshot: Snapshot) -> list[dict[str, str]]:
    rows = sheet_records(snapshot.source_path, "Sources")
    normalized: list[dict[str, str]] = []
    for row in rows:
        normalized.append(
            {
                "Run Label": snapshot.label,
                "Run Number": "",
                "Brand Handle": row.get("Brand Handle", "").strip(),
                "Blogger Handle": row.get("Blogger Handle", "").strip(),
                "Post Date": row.get("Post Date", "").strip(),
                "Post URL": row.get("Post URL", "").strip(),
                "Ad Likelihood": row.get("Ad Likelihood", "").strip(),
                "Ad Reasoning": row.get("Ad Reasoning", "").strip(),
                "Caption Excerpt": row.get("Caption Excerpt", "").strip(),
            }
        )
    return normalized


def rewrite_workbook_from_existing(source_path: Path, target_path: Path, sheet_names: list[str]) -> None:
    sheets: list[tuple[str, list[list[object]]]] = []
    for sheet_name in sheet_names:
        rows = normalize_export_sheet_rows(sheet_name, sheet_rows(source_path, sheet_name))
        if rows:
            sheets.append((sheet_name, rows))
    if not sheets:
        return
    write_simple_xlsx(target_path, sheets)


def build_common_workbook(tables_dir: Path, snapshots: list[Snapshot], run_targets: list[Path]) -> dict[str, int]:
    run_number_map = {snapshot.label: index for index, snapshot in enumerate(snapshots, start=1)}
    dossier_metrics = load_brand_dossier_metrics()
    live_metrics = load_live_profile_metrics(tables_dir)
    merged_brands: dict[str, dict[str, object]] = {}
    merged_sources_by_brand: dict[str, dict[tuple[str, ...], dict[str, object]]] = {}
    all_source_rows: list[dict[str, str]] = []
    run_rows: list[list[object]] = [[
        "Run Number",
        "Run Label",
        "Source Type",
        "Brands Count",
        "Sources Count",
        "Blogger Summary Count",
        "Source Workbook",
        "Structured Folder",
    ]]

    for index, snapshot in enumerate(snapshots, start=1):
        run_rows.append(
            [
                index,
                snapshot.label,
                snapshot.source_type,
                snapshot.brands_count,
                snapshot.sources_count,
                snapshot.blogger_summary_count,
                str(snapshot.source_path),
                str(run_targets[index - 1]),
            ]
        )

        for row in sheet_records(snapshot.source_path, "Brands"):
            handle = row.get("Handle", "").strip().lstrip("@")
            canonical = canonical_handle(handle)
            if not canonical:
                continue
            current = merged_brands.get(canonical)
            if current is None:
                merged_brands[canonical] = {
                    "Handle": handle or canonical,
                    "Profile URL": row.get("Profile URL", "").strip(),
                    "Display Name": row.get("Display Name", "").strip(),
                    "Followers Count": safe_int(row.get("Followers Count", "")),
                    "Posts Count": safe_int(row.get("Posts Count", "")),
                    "Account Kind": row.get("Account Kind", "").strip(),
                    "Outreach Fit": row.get("Outreach Fit", "").strip(),
                    "Brand Likelihood": row.get("Brand Likelihood", "").strip(),
                    "Ad Likelihood": row.get("Ad Likelihood", "").strip(),
                    "Niche": row.get("Niche", "").strip(),
                    "Category Label": row.get("Category Label", "").strip(),
                    "External Link": row.get("External Link", "").strip(),
                    "run_labels": [snapshot.label],
                    "first_seen_run": snapshot.label,
                    "last_seen_run": snapshot.label,
                }
            else:
                if not current["Profile URL"] and row.get("Profile URL", "").strip():
                    current["Profile URL"] = row.get("Profile URL", "").strip()
                if not current["Display Name"] and row.get("Display Name", "").strip():
                    current["Display Name"] = row.get("Display Name", "").strip()
                if safe_int(row.get("Followers Count", "")) > int(current["Followers Count"]):
                    current["Followers Count"] = safe_int(row.get("Followers Count", ""))
                if safe_int(row.get("Posts Count", "")) > int(current["Posts Count"]):
                    current["Posts Count"] = safe_int(row.get("Posts Count", ""))
                for field in (
                    "Account Kind",
                    "Outreach Fit",
                    "Brand Likelihood",
                    "Ad Likelihood",
                    "Niche",
                    "Category Label",
                    "External Link",
                ):
                    if not current[field] and row.get(field, "").strip():
                        current[field] = row.get(field, "").strip()
                if snapshot.label not in current["run_labels"]:
                    current["run_labels"].append(snapshot.label)
                current["last_seen_run"] = snapshot.label

        for source in parse_run_sources(snapshot):
            source["Run Number"] = str(run_number_map[snapshot.label])
            handle = source.get("Brand Handle", "").strip().lstrip("@")
            canonical = canonical_handle(handle)
            if not canonical:
                continue
            merged_for_brand = merged_sources_by_brand.setdefault(canonical, {})
            key = (
                canonical,
                source["Blogger Handle"],
                source["Post Date"],
                source["Post URL"],
                source["Ad Likelihood"],
                source["Ad Reasoning"],
                source["Caption Excerpt"],
            )
            current_source = merged_for_brand.get(key)
            if current_source is None:
                merged_for_brand[key] = {
                    "First Seen Run": source["Run Label"],
                    "Last Seen Run": source["Run Label"],
                    "run_labels": [source["Run Label"]],
                    "Brand Handle": source["Brand Handle"],
                    "Blogger Handle": source["Blogger Handle"],
                    "Post Date": source["Post Date"],
                    "Post URL": source["Post URL"],
                    "Ad Likelihood": source["Ad Likelihood"],
                    "Ad Reasoning": source["Ad Reasoning"],
                    "Caption Excerpt": source["Caption Excerpt"],
                }
            else:
                if source["Run Label"] not in current_source["run_labels"]:
                    current_source["run_labels"].append(source["Run Label"])
                current_source["Last Seen Run"] = source["Run Label"]

    for canonical in sorted(merged_sources_by_brand):
        source_rows = list(merged_sources_by_brand[canonical].values())
        source_rows.sort(
            key=lambda row: (
                row.get("First Seen Run", ""),
                row.get("Post Date", ""),
                row.get("Blogger Handle", ""),
                row.get("Post URL", ""),
            )
        )
        all_source_rows.extend(source_rows)

    for canonical, current in merged_brands.items():
        metrics = dossier_metrics.get(canonical)
        if not metrics:
            metrics = {}
        combined = {
            "followers": max(
                int(current.get("Followers Count", 0) or 0),
                int(metrics.get("followers", 0) or 0),
                int((live_metrics.get(canonical) or {}).get("followers", 0) or 0),
            ),
            "posts": max(
                int(current.get("Posts Count", 0) or 0),
                int(metrics.get("posts", 0) or 0),
                int((live_metrics.get(canonical) or {}).get("posts", 0) or 0),
            ),
        }
        current["Followers Count"] = combined["followers"]
        current["Posts Count"] = combined["posts"]

    brand_headers = [
        "Handle",
        "Profile URL",
        "Display Name",
        "Followers Count",
        "Posts Count",
        "Account Kind",
        "Outreach Fit",
        "Brand Likelihood",
        "Ad Likelihood",
        "Niche",
        "Category Label",
        "External Link",
        "Unique Bloggers Count",
        "Source Bloggers",
        "Source Posts Count",
        "Latest Source Post",
        "First Seen Run",
        "Last Seen Run",
        "Runs Seen",
        "Run Labels",
    ]
    source_headers = [
        "First Seen Run",
        "Last Seen Run",
        "Runs Seen",
        "Run Labels",
        "Brand Handle",
        "Blogger Handle",
        "Post Date",
        "Post URL",
        "Ad Likelihood",
        "Ad Reasoning",
        "Caption Excerpt",
    ]

    brand_rows: list[list[object]] = [brand_headers]
    csv_rows: list[list[object]] = []
    for canonical in sorted(merged_brands):
        current = merged_brands[canonical]
        brand_sources = list(merged_sources_by_brand.get(canonical, {}).values())
        source_bloggers = sorted(
            {
                canonical_handle(source.get("Blogger Handle", ""))
                for source in brand_sources
                if canonical_handle(source.get("Blogger Handle", ""))
            }
        )
        latest_source_post = ""
        for source in reversed(brand_sources):
            if source.get("Post URL", "").strip():
                latest_source_post = source["Post URL"].strip()
                break
        row = [
            current["Handle"],
            current["Profile URL"],
            current["Display Name"],
            current["Followers Count"],
            current["Posts Count"],
            current["Account Kind"],
            current["Outreach Fit"],
            current["Brand Likelihood"],
            current["Ad Likelihood"],
            current["Niche"],
            current["Category Label"],
            current["External Link"],
            len(source_bloggers),
            ", ".join(source_bloggers),
            len(brand_sources),
            latest_source_post,
            current["first_seen_run"],
            current["last_seen_run"],
            len(current["run_labels"]),
            ", ".join(current["run_labels"]),
        ]
        brand_rows.append(row)
        csv_rows.append(row)

    source_rows: list[list[object]] = [source_headers]
    for source in all_source_rows:
        source_rows.append(
            [
                source.get("First Seen Run", ""),
                source.get("Last Seen Run", ""),
                len(source.get("run_labels", [])),
                ", ".join(source.get("run_labels", [])),
                source.get("Brand Handle", ""),
                source.get("Blogger Handle", ""),
                source.get("Post Date", ""),
                source.get("Post URL", ""),
                source.get("Ad Likelihood", ""),
                source.get("Ad Reasoning", ""),
                source.get("Caption Excerpt", ""),
            ]
        )

    workbook_path = tables_dir / "brand_links_common.xlsx"
    write_simple_xlsx(
        workbook_path,
        [
            ("Brands", brand_rows),
            ("Sources", source_rows),
            ("Runs", run_rows),
        ],
    )

    return {
        "brands": len(csv_rows),
        "sources": len(all_source_rows),
        "runs": len(snapshots),
    }


def write_tables_readme(tables_dir: Path, snapshots: list[Snapshot], common_stats: dict[str, int]) -> None:
    lines = [
        "# Brand Excel Tables",
        "",
        "All clean brand Excel files live here.",
        "",
        "## Files",
        "",
        "- `brand_links_common.xlsx` - common deduplicated table across all runs.",
        "- `brand_links_current.xlsx` - current live table.",
        "",
        "## Run Tables",
        "",
    ]
    if not snapshots:
        lines.append("- none")
    else:
        for index, snapshot in enumerate(snapshots, start=1):
            lines.append(
                f"- `brand_links_run_{index:02d}_{snapshot.label}.xlsx` - {snapshot.brands_count} brands, {snapshot.sources_count} sources"
            )
    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- Runs merged: {common_stats.get('runs', 0)}",
            f"- Unique brands: {common_stats.get('brands', 0)}",
            f"- Unique sources: {common_stats.get('sources', 0)}",
            "",
        ]
    )
    (tables_dir / "README.md").write_text("\n".join(lines), encoding="utf-8-sig")


def write_brands_readme(brands_dir: Path) -> None:
    lines = [
        "# Brand Outputs",
        "",
        "Main live markdown exports stay here.",
        "",
        "Excel tables are centralized in `tables/`.",
        "",
        "- Current live Excel: `tables/brand_links_current.xlsx`",
        "- Historical runs: `tables/brand_links_run_*.xlsx`",
        "- Combined table across all runs: `tables/brand_links_common.xlsx`",
        "",
    ]
    (brands_dir / "README.md").write_text("\n".join(lines), encoding="utf-8-sig")


def main() -> None:
    job, _state = rebuild_live_exports()

    brands_dir = Path(job["outputs"]["discovered_brand_links_md"]).parent
    tables_dir = brands_dir / "tables"
    live_cache_path = tables_dir / "live_profile_counts.json"
    live_cache_text = ""
    if live_cache_path.exists():
        try:
            live_cache_text = live_cache_path.read_text(encoding="utf-8")
        except Exception:
            live_cache_text = ""
    if tables_dir.exists():
        shutil.rmtree(tables_dir)
    tables_dir.mkdir(parents=True, exist_ok=True)
    if live_cache_text:
        live_cache_path.write_text(live_cache_text, encoding="utf-8")

    for legacy_dir in ("current", "master", "raw", "runs"):
        path = brands_dir / legacy_dir
        if path.exists():
            shutil.rmtree(path)

    rewrite_workbook_from_existing(
        brands_dir / "brand_links.xlsx",
        tables_dir / "brand_links_current.xlsx",
        ["Brands", "Sources", "Blogger Summary"],
    )

    snapshots = discover_snapshots(brands_dir)
    run_targets: list[Path] = []
    for index, snapshot in enumerate(snapshots, start=1):
        target = tables_dir / f"brand_links_run_{index:02d}_{snapshot.label}.xlsx"
        rewrite_workbook_from_existing(snapshot.source_path, target, ["Brands", "Sources", "Blogger Summary"])
        run_targets.append(target)

    common_stats = build_common_workbook(tables_dir, snapshots, run_targets)
    write_tables_readme(tables_dir, snapshots, common_stats)
    write_brands_readme(brands_dir)

    summary = {
        "tables_dir": str(tables_dir),
        "runs_organized": len(snapshots),
        "common_unique_brands": common_stats.get("brands", 0),
        "common_unique_sources": common_stats.get("sources", 0),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
