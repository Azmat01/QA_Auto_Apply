-- Allow the dashboard / scripts to remove placeholder rows.
-- Paste into the Supabase SQL editor once.

drop policy if exists "Allow public delete job_postings" on public.job_postings;
create policy "Allow public delete job_postings"
on public.job_postings
for delete
to anon, authenticated
using (true);

-- Remove documentation placeholders (example.com is not a real job board)
delete from public.job_postings
where url ilike '%example.com%';
