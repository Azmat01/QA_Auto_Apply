# QA Auto Apply

Python job finder that queries the **public** Greenhouse Job Board API and Lever Postings API for a configured list of companies, keeps QA / SDET / Test Engineer roles in **India** or **Remote**, and writes Company Name, Role, Location, and Application URL to CSV and JSON.

A GitHub Actions workflow (`.github/workflows/job_monitor.yml`) runs the finder every day, opens an issue labeled `QA-auto-apply`, and can email `azmatsparrow@gmail.com`.

Public ATS APIs expose published listings and apply URLs. Submitting an application through Greenhouse or Lever still requires each employer's own job-board API key, so this project collects apply links instead of posting applications on your behalf.

## Quick start

```bash
python job_finder.py
```

Outputs (created under `output/`):

| File | Contents |
| --- | --- |
| `output/jobs.csv` | Spreadsheet of matches |
| `output/jobs.json` | Same data as JSON |
| `output/digest.md` | Markdown table used in GitHub issues and email |

Structured JSON logs (for CI):

```bash
set LOG_FORMAT=json
python job_finder.py
```

On Linux / macOS: `LOG_FORMAT=json python job_finder.py`

## Configuration

Edit these files — no code changes required:

- `config/companies.json` — Greenhouse `board_token` values (from `boards.greenhouse.io/{token}`) and Lever `site` slugs (from `jobs.lever.co/{site}`)
- `config/settings.json` — keywords, location aliases, timeouts, notify email, and label

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
- Emails **azmatsparrow@gmail.com** when SMTP secrets are present

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

## Project layout

```
job_finder.py
qa_auto_apply/          # fetch, filter, export, notify
config/companies.json
config/settings.json
.github/workflows/job_monitor.yml
tests/
```
