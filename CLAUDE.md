# CLAUDE.md -- Autoskill: NSX Production B2B Outreach Automation

## Who We Are

**NSX Production** -- B2B video production company (Moscow).
- Services: music videos, snippets, mood-videos, image videos, ads, video courses, music production, films, photo shoots
- Team: Georgiy (director, 7 yrs), Danil (director/VFX/SFX, 6 yrs), Sergey (producer, B2B, ex-diplomat)
- Portfolio PDF: `C:\Users\User\Downloads\Telegram Desktop\NSX.pdf`
- Proven cases: Aeroflot, Dior, Hugo, MTS, Honor, OMODA, Jetour, Changan, Coffeemania, Fonbet x KHL, Klava Koka, Snezhnaya Koroleva, and 10+ more

## Project Purpose

Two independent pipelines in one repo:
1. **Influencer Brand Discovery** (existing, production) -- discovers brands via Instagram bloggers, scores them, sends DMs on behalf of influencer Farida Shirinova (629K followers)
2. **Company Contacts Enrichment** (new module, in development) -- takes a ready list of target companies, finds decision-makers (PR dept, Marketing dept, C-level), collects contacts, and prepares personalized outreach for NSX Production's B2B video services

## Architecture Overview

```
tesett/
  automation/
    modules/
      instagram_brand_search/   # Pipeline 1: Instagram discovery
      brand_intelligence/       # Pipeline 1: web research + contacts
      brand_arbiter/            # Pipeline 1: scoring & verdict
      media_intelligence/       # Pipeline 1: media analysis
      outreach_planning/        # Pipeline 1: outreach decision
      conversation/             # Pipeline 1: message sending
      feedback_validation/      # Pipeline 1: validation
      company_contacts_enrichment/  # Pipeline 2 (NEW): B2B contact finder
    control_plane/              # Task orchestration, profiles, routing
    agents/contracts/           # task_types.yaml, routing_rules.yaml
    policies/                   # Creator policies (farida_shirinova.yaml)
    llm/                        # LLM clients (OpenAI, Gemini, KIE)
    config.py                   # AdsPower + Instagram DM settings
    adspower.py                 # Browser profile management API
    browser.py                  # Playwright CDP connection
  scripts/                      # Entry points (run_*.py)
  output/                       # Generated evidence, dossiers, reports
  knowledge/llm_wiki/           # Shared memory across agents
  inputs/                       # Runtime input files
```

## Pipeline 1: Influencer Brand Discovery (Existing)

DO NOT modify unless explicitly asked. Stable, tested, production-ready.

Flow: Instagram Discovery -> Brand Intelligence -> Brand Arbiter -> Outreach Planning -> Conversation
- Policy: `automation/policies/farida_shirinova.yaml`
- Task routing: `automation/agents/contracts/routing_rules.yaml`
- Task types: `automation/agents/contracts/task_types.yaml`
- Browser profiles: 353 (discovery), 345 (research), 337 (outbound DM)

## Pipeline 2: Company Contacts Enrichment (NEW MODULE)

### Business Context

NSX Production (video production) needs to find contacts at ~100+ Russian companies to pitch B2B video production services. The goal is to find **decision-makers**: PR department, Marketing department heads, or company leadership who approve video production budgets.

### Target Contacts (Priority Order)

1. PR department email/phone (pr@, press@, media@)
2. Marketing department email/phone (marketing@, reklama@, adv@)
3. Partnership/collaboration contacts (partnership@, sotrudnichestvo@)
4. Named decision-makers: CMO, VP Marketing, PR Director, Brand Manager
5. Company owners/founders (for smaller companies)
6. General company contacts as fallback

### Email Pattern Deduction Hack

When one departmental email is found (e.g., `pr@ozon.ru`), generate and validate sibling patterns:
- `marketing@`, `press@`, `media@`, `adv@`, `reklama@`, `partnership@`, `sotrudnichestvo@`, `info@`, `hello@`
This works reliably for large Russian corporations.

### Data Collection Pipeline (6 Steps)

```
Step 1: Domain Resolution
  Source: Web search (Bing RSS -> DuckDuckGo fallback) + Rusprofile
  Output: company domain, legal entity name, INN
  Tool: Firecrawl search -> WebFetch fallback -> Playwright (AdsPower) fallback

Step 2: Corporate Site Deep Crawl
  Target pages: /contacts, /kontakty, /about, /o-kompanii, /press, /press-center,
                /dlya-smi, /partners, /sotrudnichestvo, /team, /komanda, /rukovodstvo
  Extract: all emails, phones, contact forms, department-specific contacts
  Tool: Firecrawl crawl -> WebFetch fallback -> Playwright (AdsPower) fallback

Step 3: HH.ru Company Intelligence
  Strategy: Search "{company_name}" on hh.ru to find employer page
  What HH gives: company structure via job titles (reveals marketing dept size),
                  HR manager name/email/phone as entry point
  NOT for: finding specific people directly
  Tool: Firecrawl search -> WebFetch fallback

Step 4: People Search (OSINT)
  Queries: "{company} PR director", "{company} marketing director",
           "{company} head of marketing", "{company} CMO"
  Sources: vc.ru articles (author = company employee), cossa.ru,
           sostav.ru conference speakers, LinkedIn (limited without login)
  Extract: Full name, position, social profiles, article links
  Tool: Firecrawl search -> WebFetch fallback

Step 5: LLM Synthesis
  Input: All collected data from steps 1-4
  Output: Structured company card with:
    - Best contact path recommendation ("entry route")
    - Personalized pitch angle (based on company industry + NSX portfolio match)
    - Confidence score per contact
  Model: brain_model (high reasoning) via automation/llm/clients.py

Step 6: Email Validation
  Method: SMTP check without sending (RCPT TO verification)
  Also: email pattern deduction from found emails (see hack above)
  Fallback: mark as "unverified" if SMTP check unavailable
```

### Fetcher Strategy: Firecrawl + Fallbacks

```python
# Priority order for web fetching:
# 1. Firecrawl (via CLI skill) -- best quality, handles JS, clean markdown
# 2. WebFetch (built-in tool) -- no JS rendering, but free and unlimited
# 3. Playwright via AdsPower -- for sites requiring login (rusprofile, etc.)
#
# Use Playwright/AdsPower for:
#   - rusprofile.ru (needs login for full data)
#   - yandex maps (dynamic JS content)
#   - Any site with anti-bot protection
#
# AdsPower profile for research: profile 345 (browser_research capability)
```

### HH.ru Strategy Explained

HH.ru is NOT a people database -- it's a job board. But it's valuable because:
1. **Employer pages** show company description, size, industry
2. **Active job postings** reveal organizational structure (if hiring "Head of Video Content" -- they need video!)
3. **HR contact info** in job postings = real phone/email of someone inside the company
4. **Job titles** reveal which departments exist and their hierarchy
5. **Recently closed positions** hint at current team composition

Search pattern: `https://hh.ru/search/vacancy?text={company_name}&search_field=company_name`

### Instagram Person Search

After finding a decision-maker's name, optionally search Instagram:
- Search by full name in Instagram search
- Check if person's bio mentions the target company
- If found -- can send DM directly as alternative channel

### Data Model

```python
@dataclass
class CompanyCard:
    # Identity
    company_name: str              # "OZON"
    company_name_aliases: list     # ["Озон", "OZON", "ozon.ru"]
    legal_entity: str              # 'ООО "Интернет Решения"'
    inn: str                       # "7704217370"
    industry: str                  # "e-commerce"
    website: str                   # "ozon.ru"

    # Department contacts
    pr_emails: list[str]           # ["pr@ozon.ru", "press@ozon.ru"]
    marketing_emails: list[str]    # ["marketing@ozon.ru"]
    partnership_emails: list[str]  # ["partnership@ozon.ru"]
    general_emails: list[str]     # ["info@ozon.ru"]
    phones: list[str]             # ["+7 495 ..."]

    # Decision makers
    decision_makers: list[PersonContact]

    # Social
    telegram: str
    instagram: str
    vk: str

    # Meta
    hh_employer_url: str
    rusprofile_url: str
    sources: list[str]            # URLs where data was found
    enrichment_level: int         # 1-6 (which steps completed)
    confidence: float             # 0.0-1.0
    recommended_entry_route: str  # LLM recommendation
    pitch_angle: str              # Why NSX is relevant to this company
    last_updated: str             # ISO datetime

@dataclass
class PersonContact:
    full_name: str                # "Иванов Сергей Петрович"
    position: str                 # "Директор по маркетингу"
    department: str               # "Маркетинг" | "PR" | "Руководство"
    email: str
    phone: str
    telegram: str
    instagram: str
    linkedin: str
    source_url: str               # where we found this person
    confidence: float
```

### Target Companies List

~100 companies provided as input. Stored in `inputs/target_companies.yaml`.
Mix of sectors: FMCG, banking, telecom, retail, tech, energy, pharma, logistics.

### Output Structure

```
output/company_contacts_enrichment/
  {company_slug}/
    company_card.json          # Structured CompanyCard
    company_card.md            # Human-readable summary
    raw_research/
      website_crawl.json       # Firecrawl/WebFetch results
      hh_results.json          # HH.ru employer data
      people_search.json       # OSINT results
      rusprofile.json           # Legal entity data
    enrichment_log.json        # Step-by-step log of what was done
```

## Technical Conventions

### Code Style
- Python 3.11+, dataclasses (not Pydantic), type hints everywhere
- `from __future__ import annotations` at top of every file
- Imports: stdlib first, then project imports, alphabetical within groups
- No external dependencies beyond: playwright, PyYAML (check requirements.txt)
- For web fetching: prefer stdlib urllib first, then Firecrawl CLI skill, then Playwright

### File I/O
- All paths via `pathlib.Path`
- JSON with `ensure_ascii=False, indent=2`
- Markdown files with `utf-8-sig` encoding
- State files in `automation/state/`
- Output files in `output/{module_name}/`

### Module Structure (follow existing pattern)
```
automation/modules/company_contacts_enrichment/
  __init__.py
  worker.py          # Main entry point: run_company_enrichment_task()
  web_research.py    # Firecrawl + WebFetch + Playwright fetchers
  models.py          # CompanyCard, PersonContact, EnrichmentTask dataclasses
  state.py           # Track which companies are done
  email_validator.py # SMTP validation + pattern deduction
  sources/
    corporate_site.py   # Step 2: site crawl logic
    hh_search.py        # Step 3: HH.ru employer search
    people_search.py    # Step 4: OSINT for decision-makers
```

### Error Handling
- Each step should be independent -- if step 3 fails, steps 4-6 still run
- Log errors per step in `enrichment_log.json`
- Never crash the whole pipeline for one company

### LLM Usage
- Use `automation/llm/clients.py` for all LLM calls
- brain_model for synthesis/reasoning (Step 5)
- writer_model for pitch generation
- Always provide structured JSON schema for LLM output

### Browser Profiles (AdsPower)
- Profile 345: browser_research (shared lease, for rusprofile/yandex maps)
- Use `automation/adspower.py` + `automation/browser.py` for browser sessions
- Always release lease after use

## Important Rules

1. **Two pipelines are independent** -- company_contacts_enrichment does NOT depend on Instagram discovery pipeline
2. **Never modify Pipeline 1 code** unless explicitly asked
3. **Firecrawl first, fallback to WebFetch, then Playwright** -- this order always
4. **Email pattern deduction** -- always try sibling emails when one departmental email found
5. **Russian language awareness** -- search queries should be in Russian for Russian sources
6. **No spam** -- this tool finds contacts, human decides whether/how to reach out
7. **Data freshness** -- always store `last_updated` timestamp, re-enrich if data > 30 days old

## Commands

```bash
# Pipeline 1 (existing)
python scripts/run_instagram_brand_search.py
python scripts/run_supervisor.py --max-tasks 25

# Pipeline 2 (new, to be created)
python scripts/run_company_enrichment.py                    # Enrich all companies from target list
python scripts/run_company_enrichment.py --company "OZON"   # Enrich single company
python scripts/run_company_enrichment.py --step 2           # Run only step 2 for all
python scripts/run_company_enrichment.py --export xlsx       # Export results to Excel
```

## NSX Production Pitch Context

When generating pitch angles (Step 5), the LLM should know:
- NSX makes premium commercial video content (not UGC, not cheap)
- Strong portfolio: Aeroflot, Dior, Hugo, MTS, Honor, OMODA, Jetour
- Team has cinematic quality (7 years directing, VFX/SFX, music production)
- B2B focus: brand videos, ad campaigns, music videos for corporate events
- Geographic: Moscow-based, work across Russia
- Pitch PDF available: `C:\Users\User\Downloads\Telegram Desktop\NSX.pdf`

## Environment Variables

```env
# AdsPower (required for browser-based research)
ADSPOWER_BASE_URL=http://127.0.0.1:50325
ADSPOWER_API_KEY=...
ADSPOWER_PROFILE_NO=353

# LLM (required for Step 5)
OPENAI_API_KEY=...
# or
KIE_OPENAI_API_KEY=...
KIE_GEMINI_API_KEY=...

# Optional
AUTOSKILL_LLM_MODEL_BRAIN=gpt-5.4
AUTOSKILL_LLM_MODEL_WRITER=gpt-5.4-mini
FIRECRAWL_API_KEY=...  # For Firecrawl, if not using CLI skill
```
