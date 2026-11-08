-- Application-level Supabase Edge Function error monitoring.
-- This table does not automatically ingest Supabase platform logs.
create table if not exists public.edge_function_errors (
  id bigint generated always as identity primary key,
  occurred_at timestamptz not null default now(),
  function_name text not null check (char_length(function_name) between 1 and 100),
  error_code text,
  message text not null check (char_length(message) between 1 and 500),
  request_id text,
  resolved_at timestamptz
);
create index if not exists edge_function_errors_occurred_at_idx on public.edge_function_errors(occurred_at desc);
alter table public.edge_function_errors enable row level security;
revoke all on public.edge_function_errors from anon, authenticated;
revoke all on sequence public.edge_function_errors_id_seq from anon, authenticated;
grant select, insert, update on public.edge_function_errors to service_role;
grant usage, select on sequence public.edge_function_errors_id_seq to service_role;
comment on table public.edge_function_errors is 'Explicitly reported application errors only; not a complete Supabase platform log feed.';
