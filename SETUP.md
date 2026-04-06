# Setup

## What You Need

Required:

- Python `3.11+`
- `pip`
- AdsPower desktop app installed and running
- one AdsPower browser profile that is already logged in to the target website
- local AdsPower API enabled
- project `.env` or `.env.local`

Optional:

- Playwright browser binaries
- MCP only if you want to expose this runtime to another agent or tool
- `OPENAI_API_KEY` only for future research or LLM-driven steps

## Minimal Init

From the project root:

```powershell
cd C:\Users\occult\Desktop\auto\autoskill
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
```

Then create `.env` from `.env.example` and fill:

- `ADSPOWER_BASE_URL`
- `ADSPOWER_API_KEY`
- `ADSPOWER_PROFILE_NO`

## Do You Need MCP

No, not for the current runtime.

This repo already talks to AdsPower through its local HTTP API and attaches Playwright over CDP. That is enough for:

- starting a saved profile
- reusing cookies and login state
- opening pages
- uploading files
- clicking, typing, downloading

Use MCP only if you want one of these:

- control this automation from another agent host
- expose higher-level actions as tools
- combine browser actions with other external MCP services in one workflow

If your goal is just `AdsPower + Playwright`, MCP is optional and can be skipped for now.

## Quick Validation

Run:

```powershell
python scripts/check_setup.py
```

It will verify:

- Python version
- installed packages
- `.env` values
- AdsPower API availability

## First Run

Example:

```powershell
python scripts/run_higgsfield_login_fill.py
```

## Notes

- Put secrets in `.env.local` if you do not want them in `.env`.
- `.env.local` overrides `.env`.
- The Genaipro job config currently contains machine-specific absolute paths and should be adapted before production use.

