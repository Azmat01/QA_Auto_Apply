/**
 * Local / GitHub Pages config for the Supabase-backed dashboard.
 *
 * 1. Create a Supabase project and run supabase/schema.sql
 * 2. Copy your Project URL and anon public key below
 * 3. Enable Row Level Security policies from the schema file
 *
 * The anon key is safe to expose in a static site when RLS is enabled.
 */
window.SUPABASE_CONFIG = {
  // Must be https://PROJECT_REF.supabase.co (note the :// order)
  url: "https://gstjnmduuevtwlybaldm.supabase.co",
  anonKey: "sb_publishable_zxQP2aJ4Z79OuDo-0YvWPA_MwDBWBu_",
  table: "job_postings",
};
