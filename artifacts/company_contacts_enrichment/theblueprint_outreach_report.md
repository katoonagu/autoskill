# The Blueprint Outreach Report

Source shortlist: `inputs/theblueprint_career_hiring.yaml`
Snapshot date: `2026-04-15`

## Snapshot

- Archive scanned: `1999` companies
- Shortlist kept: `81`
- Segment split: `B=45`, `C=24`, `D=3`, `E=9`
- Best immediate lane for NSX: `C + D`
- Best second lane: `B` with strong brand/content signal
- Slower lane: `E`, only when there is a named marketing/PR owner or an unusually strong content signal

## Who To Write First

This is not a list of the biggest brands. It is the list with the best combination of:

- clear "why now"
- identifiable person or route
- fit with NSX offer
- short path to a founder / marketer / PR lead

### Wave 1: Personal Warm-Cold Targets

1. **Befree**
Reason: new `Marketing Manager` (`Евгений Лагутин`) is the strongest current personnel signal in the file.
Who to find: `Евгений Лагутин`
Why now: a new marketing lead often re-tests suppliers and formats in the first 30-60 days.
Route now: search articles/interviews first, then personal socials, then direct pitch.

2. **Emka**
Reason: newly appointed PR lead.
Who to find: `Прохор Шаляпин`
Why now: a new PR owner needs visible wins quickly and is more open to external production.
Route now: personal Instagram / Telegram path first, then brand email fallback.

3. **Ushatava**
Reason: explicit expansion into shoes/accessories.
Who to find: founders first, then product/category owner.
Why now: new category launch means campaign, product and vertical content demand.
Route now: founders' public socials -> Telegram -> direct route to launch contact.

4. **Lamoda**
Reason: strong private-label and digital marketing signal.
Who to find: brand/marketing owner for STM/private label.
Why now: STM needs distinct visual system and recurring content.
Route now: HR/contact bridge plus `pr@` / `marketing@` fallback.

5. **Don't Touch My Skin**
Reason: new head-of-marketing level signal.
Who to find: current or incoming marketing head, founder, brand-side operator.
Why now: when the top marketer changes, content strategy is often reassembled.
Route now: first identify the person; do not cold the generic brand account first.

6. **Finn Flare**
Reason: in-house SMM buildout is a strong proxy for external content need.
Who to find: SMM manager plus brand/marketing lead.
Why now: they are building distribution, not necessarily production capability.
Route now: named email already exists in notes; expand to pattern-deduced brand mailboxes.

7. **Бар «Ровесник»**
Reason: `Content&Sales Lead` signal is unusually close to the actual buyer need.
Who to find: content/sales lead plus founder/owner.
Why now: HoReCa buys faster, and NSX can pitch a concrete vertical-content package.
Route now: Instagram -> Telegram -> owner/contact page.

8. **Bork**
Reason: premium brand, multiple relevant marketing roles, strong fit with high-end visual cases.
Who to find: CRM marketing, brand manager, PR/press owner.
Why now: enough active signals to justify direct brand approach.
Route now: role mailbox + pattern deduction + named HR-based email pattern.

### Wave 2: Good Targets, But Slightly Less Direct

- `YuliaWave`
- `2Mood`
- `Poison Drop`
- `Sela`
- `ADDA gems`
- `ARLIGENT`
- `Studio 29`
- `Belle YOU`
- `Sportmaster`
- `Simple Group`

### Wave 3: Approach Indirectly Or Only With Better Signal

- `Ozon`
- `Сбер`
- `VK`
- `Яндекс`
- `Т-Банк`
- `T2`
- `2ГИС`
- `KION`

These are not bad targets. They are just worse *first* targets because the buying path is longer and the internal structure is heavier.

## Practical Rule: Brand First vs Person First

- If segment is `C` or `D`, default to `person-first`.
- If segment is `B`, default to `person-first` when there is a named marketer/PR lead; otherwise use `brand + named role` in parallel.
- If segment is `E`, default to `role-first`, not founder-first.
- For `A`-like companies hiding inside `B/E`, never start with a generic DM.

## Second-Level Research Logic

Goal of stage 2:

For each top target, do not stop at the company card. Build a `PersonCard`.

Minimum output per person:

- `brand`
- `person_name`
- `role`
- `why_now`
- `instagram_url`
- `telegram_handle_or_url`
- `email`
- `proof_url`
- `preferred_entry_route`
- `confidence`

## Heuristic Search Ladder

Use this order. Do not jump around.

### 1. Lock the reason to contact

Before searching people, answer:

- what exactly changed?
- who is likely to own that budget?
- what kind of content problem does that change imply?

Examples:

- `new PR head` -> owner is PR/brand -> pitch launch/seasonal visual package
- `new marketing manager` -> owner is growth/brand/content -> pitch recurring vertical production
- `new category launch` -> owner is founder/product/brand -> pitch launch campaign + product reels

### 2. Find the likely buyer by role, not by platform

For `C/D`:

- founder
- co-founder
- owner
- CEO if founder-led
- PR head
- brand head

For `B/E`:

- marketing manager
- brand manager
- PR lead
- head of content
- communications lead
- CRM/content/growth lead

### 3. Open-web person search

Use search queries like:

```text
"Имя Фамилия" "Бренд"
"Имя Фамилия" Instagram
"Имя Фамилия" Telegram
site:vc.ru "Имя Фамилия" "Бренд"
site:cossa.ru "Имя Фамилия" "Бренд"
site:sostav.ru "Имя Фамилия" "Бренд"
site:adindex.ru "Имя Фамилия" "Бренд"
site:theblueprint.ru/career "Бренд"
site:brand.ru ("team" OR "команда" OR "press" OR "пресс")
```

Success criterion:

- one named person
- one proof URL tying them to the brand

If you cannot get a named person in `C/D`, the search is not done yet.

### 4. Instagram search only after identity is narrowed

Do not search Instagram by brand first if the brand is founder-led.
Search by person name + brand context.

Patterns:

```text
site:instagram.com "Имя Фамилия" "Бренд"
site:instagram.com "Имя Фамилия"
site:instagram.com "Бренд" founder
```

Validation rules:

- bio mentions brand or role
- avatar/style matches public identity
- linked city / visual context matches
- posts or tagged content show the same brand

What to extract from Instagram:

- direct email in bio
- Telegram handle
- Taplink / Linktree / website
- manager / assistant contact
- public WhatsApp or booking link

### 5. Telegram expansion from Instagram or search

If Instagram bio contains Telegram:

- search the exact handle
- inspect channel/profile bio
- inspect linked websites
- inspect pinned posts for contact info

If no handle exists, search:

```text
"Имя Фамилия" Telegram
"@handle"
"Имя Фамилия" "Бренд" Telegram
```

What to extract from Telegram:

- direct handle
- email in bio
- manager/admin contact
- website or Notion/Taplink
- "for partnerships / cooperation" line

### 6. Brand site last-mile check

Always check:

- `/contacts`
- `/contact`
- `/team`
- `/about`
- `/press`
- `/pr`
- `/media`
- `/partners`
- `/collab`
- `/career`
- footer

Look for:

- founder names
- PR/marketing mailboxes
- press contact
- wholesale / partnerships contact
- hidden staff emails in page source or PDFs

### 7. Email pattern deduction only after one verified mailbox

If you have one verified mailbox like:

- `name@brand.ru`
- `firstname.lastname@brand.ru`

Then derive:

- `pr@brand.ru`
- `marketing@brand.ru`
- `press@brand.ru`
- likely named variations for the identified person

But do this only after the person identity is reasonably locked.

## Scoring Heuristic For Stage 2

Each target gets a simple score out of `10`.

- `+3` named person exists
- `+2` direct why-now signal exists
- `+2` Instagram or Telegram path exists
- `+1` verified brand mailbox exists
- `+1` founder-led brand
- `+1` NSX offer clearly maps to current need

Interpretation:

- `8-10`: write now
- `6-7`: enrich for 10 more minutes, then write
- `4-5`: keep in queue
- `0-3`: stop and move on

## What Not To Do

- Do not start from anonymous brand Instagram if a named person is findable.
- Do not waste time on designers unless they are also a founder or category owner.
- Do not treat generic editorial roles as buying roles.
- Do not spend 30 minutes on one target without finding either a person or a proof URL.
- Do not cold big corps from generic DMs when the only signal is a vacancy.

## Immediate Next Pass

Best next batch for stage 2 enrichment:

1. `Befree`
2. `Emka`
3. `Ushatava`
4. `Lamoda`
5. `Don't Touch My Skin`
6. `Finn Flare`
7. `Бар «Ровесник»`
8. `Bork`
9. `YuliaWave`
10. `2Mood`

For this batch, the success criterion is simple:

- at least `1` named person per brand
- at least `1` verified social/contact route per brand
- a recommended first message path per brand

