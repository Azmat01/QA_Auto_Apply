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

-- Public read + update for the static dashboard (anon key).
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

-- Optional sample rows so the UI is not empty on first load
insert into public.job_postings (title, url, description, date, is_applied)
values
  (
    'Junior QA Engineer',
    'https://example.com/jobs/junior-qa',
    'Entry-level QA role. 0-1 years. Manual + light automation. India / Remote.',
    (timezone('utc', now()))::date,
    false
  ),
  (
    'Manual Tester - Fresher',
    'https://example.com/jobs/manual-tester',
    'Campus hire. Manual testing for web apps. Bengaluru.',
    (timezone('utc', now()) - interval '1 day')::date,
    false
  )
on conflict do nothing;
