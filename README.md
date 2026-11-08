# QA Auto Apply

Python job finder that queries the **public** Greenhouse Job Board API and Lever Postings API for a **configured company list** (not the whole internet), keeps junior QA / Manual Tester roles, selects a daily mix of **10 jobs** (3 preferred-city office + 2 India WFH + 5 international WFH), writes them to CSV and JSON, and emails the apply URLs to `azmatsparrow@gmail.com`.

A GitHub Actions workflow (`.github/workflows/job_monitor.yml`) runs the finder every day, opens an issue labeled `QA-auto-apply`, and can email the digest.

Public ATS APIs expose published listings and apply URLs. Submitting an application through Greenhouse or Lever still requires each employer's own job-board API key, so this project collects apply links instead of posting applications on your behalf.

## Quick start

```bash
python job_finder.py
```

Outputs (created under `output/`):

| File | Contents |
| --- | --- |
| `output/jobs.csv` | Top 10 matches |
| `output/jobs.json` | Same data as JSON |
| `output/digest.md` | Markdown table and apply links used in GitHub issues and email |

Structured JSON logs (for CI):

```bash
set LOG_FORMAT=json
python job_finder.py
```

On Linux / macOS: `LOG_FORMAT=json python job_finder.py`

## How matching works

- **Role:** QA / Manual Tester / SDET titles, including **QA Intern** and testing internships.
- **Experience:** `junior_only` — fresher, intern, 0–1 years (Senior/Staff/Lead dropped).
- **Daily mix (10):** `daily_quotas` in settings —
  - **3** office jobs in preferred cities (Noida, Gurgaon/Gurugram, Jaipur, Lucknow, Bhopal, Pune, Mumbai, Kochi, Hyderabad, Amritsar, Zirakpur, Varanasi, …)
  - **2** work-from-home jobs in India
  - **5** work-from-home jobs outside India (Europe, Americas, Arabian/Gulf, SE Asia, Australia, …)
- **Blocked countries:** Pakistan, Egypt, Argentina (and major cities there).
- Internships are ranked first within each bucket.

Configured in [`config/settings.json`](config/settings.json). This script cannot search Naukri/LinkedIn/Indeed — only public Greenhouse/Lever boards in `config/companies.json`.

## Configuration

Edit these files — no code changes required:

- `config/companies.json` — Greenhouse `board_token` values (from `boards.greenhouse.io/{token}`) and Lever `site` slugs (from `jobs.lever.co/{site}`)
- `config/settings.json` — keywords, `daily_quotas`, `preferred_office_cities`, timeouts, notify email, and label

The finder skips missing boards (HTTP 404) and retries transient errors (429 / 5xx) with backoff.

## Tests

```bash
python -m unittest discover -s tests -v
```

## GitHub Actions

Workflow file: `.github/workflows/job_monitor.yml`

- Runs daily at **08:00 IST** (`30 2 * * *` UTC) and on manual **Run workflow**
- Uploads CSV / JSON / digest as an artifact
- Creates a GitHub issue labeled **`QA-auto-apply`**, assigned to the repo owner (GitHub emails you if issue notifications are on)
- Emails **azmatsparrow@gmail.com** when SMTP secrets are present (HTML list with clickable apply URLs)

### Email secrets (Gmail)

In the GitHub repo: **Settings → Secrets and variables → Actions**

| Secret | Example |
| --- | --- |
| `SMTP_USERNAME` | `azmatsparrow@gmail.com` |
| `SMTP_PASSWORD` | Gmail [App Password](https://support.google.com/accounts/answer/185833) |
| `SMTP_HOST` | `smtp.gmail.com` (optional) |
| `SMTP_PORT` | `587` (optional) |
| `SMTP_FROM` | `azmatsparrow@gmail.com` (optional) |

Local email send (after a fetch):

```bash
python job_finder.py --send-email
```

## Job dashboard (GitHub Pages + Supabase)

Static SPA in [`docs/`](docs/): HTML, Tailwind (CDN), custom CSS, and vanilla JS.

| File | Role |
| --- | --- |
| `docs/index.html` | Page shell, filter tabs, board |
| `docs/styles.css` | Layout, cards, collapsible date sections |
| `docs/app.js` | Fetch jobs, group by date, toggle `is_applied` |
| `docs/config.js` | Supabase URL + anon key |
| `supabase/schema.sql` | `job_postings` table + RLS policies |

### Columns

`id`, `title`, `url`, `description`, `date`, `is_applied`

### How data flows

```text
job_finder.py
  → email + GitHub issue
  → docs/data/jobs.json  (committed by Actions)  →  GitHub Pages dashboard
  → optional Supabase sync (applied toggles / backup)
```

The website reads **`docs/data/jobs.json` first**. Supabase is optional. If Actions secrets for Supabase are missing, email can still work and the Pages site still updates from the committed JSON feed.

### Setup

1. Create a Supabase project and run [`supabase/schema.sql`](supabase/schema.sql) in the SQL editor (includes a unique index on `url` for upserts).
2. Put **Project URL** and **anon / publishable** key in [`docs/config.js`](docs/config.js). The URL must look like `https://YOUR_PROJECT.supabase.co` (not `https//:`).
3. Add the same values as GitHub Actions secrets so the daily run can fill the table:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY` (or `SUPABASE_SERVICE_ROLE_KEY`)
4. On GitHub: **Settings → Pages → Deploy from a branch → `/docs`** (branch `main`).
5. Re-run **Actions → Daily Job Monitor**, then refresh the Pages URL.

Local preview:

```bash
cd docs
python -m http.server 8080
```

Then visit `http://localhost:8080`.

## Project layout

```
job_finder.py
qa_auto_apply/          # fetch, filter, export, notify
config/companies.json
config/settings.json
docs/                   # GitHub Pages dashboard
supabase/schema.sql
.github/workflows/job_monitor.yml
tests/
```
