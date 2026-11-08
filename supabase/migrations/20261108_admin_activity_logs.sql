-- Deep Documentary: private administrator activity log
-- Run once in Supabase SQL Editor. No public write access.
create table if not exists public.admin_activity_logs (
  id bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  actor_user_id uuid references auth.users(id) on delete set null,
  event_type text not null check (char_length(event_type) between 3 and 80),
  description text not null check (char_length(description) between 1 and 500),
  metadata jsonb not null default '{}'::jsonb,
  constraint admin_activity_metadata_object check (jsonb_typeof(metadata) = 'object')
);
create index if not exists admin_activity_logs_created_at_idx
  on public.admin_activity_logs (created_at desc);
create index if not exists admin_activity_logs_actor_idx
  on public.admin_activity_logs (actor_user_id, created_at desc);
alter table public.admin_activity_logs enable row level security;
-- Revoke all direct access from web-facing roles. Future trusted Edge Functions
-- must verify admin privileges and use the service-role key server-side.
revoke all on table public.admin_activity_logs from anon, authenticated;
revoke all on sequence public.admin_activity_logs_id_seq from anon, authenticated;
-- RLS intentionally has no anon/authenticated policies.
comment on table public.admin_activity_logs is
  'Private audit trail. Write and read only through admin-verified server-side functions.';
