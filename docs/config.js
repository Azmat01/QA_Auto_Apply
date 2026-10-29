/**
 * Optional local override. The live GitHub Pages site inlines config in index.html
 * so a stale cached config.js cannot blank the dashboard again.
 *
 * URL must be https://PROJECT_REF.supabase.co (correct :// order).
 */
window.SUPABASE_CONFIG = window.SUPABASE_CONFIG || {
  url: "https://gstjnmduuevtwlybaldm.supabase.co",
  anonKey: "sb_publishable_zxQP2aJ4Z79OuDo-0YvWPA_MwDBWBu_",
  table: "job_postings",
};
