-- Run once in the Supabase SQL editor if you already created job_postings
-- without a unique URL index (needed for optional upserts).

create unique index if not exists job_postings_url_key on public.job_postings (url);
