-- QA Auto Apply · job_postings table for the GitHub Pages dashboard
-- Run this in the Supabase SQL editor for your project.

create extension if not exists "pgcrypto";

create table if not exists public.job_postings (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  url text not null,
  description text default '',
  date date not null default (timezone('utc', now()))::date,
  is_applied boolean not null default false,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

-- Required so the daily script can upsert by application URL without wiping is_applied
create unique index if not exists job_postings_url_key on public.job_postings (url);
create index if not exists job_postings_date_idx on public.job_postings (date desc);
create index if not exists job_postings_is_applied_idx on public.job_postings (is_applied);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

drop trigger if exists job_postings_set_updated_at on public.job_postings;
create trigger job_postings_set_updated_at
before update on public.job_postings
for each row
execute function public.set_updated_at();

alter table public.job_postings enable row level security;

-- Public read + write for the static dashboard + GitHub Action sync (anon / publishable key).
-- Tighten these policies if you later add auth.
drop policy if exists "Allow public read job_postings" on public.job_postings;
create policy "Allow public read job_postings"
on public.job_postings
for select
to anon, authenticated
using (true);

drop policy if exists "Allow public update is_applied" on public.job_postings;
create policy "Allow public update is_applied"
on public.job_postings
for update
to anon, authenticated
using (true)
with check (true);

drop policy if exists "Allow public insert job_postings" on public.job_postings;
create policy "Allow public insert job_postings"
on public.job_postings
for insert
to anon, authenticated
with check (true);

-- Do not seed example.com rows. Real openings are inserted by job_finder.py
-- when SUPABASE_URL and SUPABASE_ANON_KEY are set.
