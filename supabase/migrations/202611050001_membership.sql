begin;

create table public.member_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  full_name text not null check (char_length(trim(full_name)) between 1 and 120),
  created_at timestamptz not null default now()
);
create table public.member_articles (
  slug text primary key check (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$')
);
insert into public.member_articles(slug) values
('alula-khaybar-archaeology'), ('apollo-11'), ('apollo-8'), ('black-holes'),
('canva-video-editor-beginners-guide'), ('chernobyl'), ('mary-celeste'),
('passkeys-end-of-passwords-2026');
create table public.member_favorites (
  user_id uuid not null references auth.users(id) on delete cascade,
  article_slug text not null references public.member_articles(slug),
  created_at timestamptz not null default now(),
  primary key(user_id, article_slug)
);
create table public.member_reading (
  user_id uuid not null references auth.users(id) on delete cascade,
  article_slug text not null references public.member_articles(slug),
  progress smallint not null check (progress between 0 and 100),
  updated_at timestamptz not null default now(),
  primary key(user_id, article_slug)
);
-- Award ledger is server-managed. A member cannot grant points or badges.
create table public.member_awards (
  user_id uuid not null references auth.users(id) on delete cascade,
  award_key text not null check (char_length(award_key) between 1 and 120),
  points integer not null check (points between 0 and 1000),
  badge text check (char_length(badge) between 1 and 120),
  created_at timestamptz not null default now(),
  primary key(user_id, award_key)
);
-- Only trusted server processes may change subscription status after Brevo DOI.
create table public.member_newsletter (
  user_id uuid primary key references auth.users(id) on delete cascade,
  status text not null check (status in ('pending', 'subscribed', 'unsubscribed')),
  consent_version text not null,
  requested_at timestamptz not null default now(),
  confirmed_at timestamptz,
  check (status <> 'subscribed' or confirmed_at is not null)
);
create table public.member_admins (
  user_id uuid primary key references auth.users(id) on delete cascade
);

alter table public.member_profiles enable row level security;
alter table public.member_articles enable row level security;
alter table public.member_favorites enable row level security;
alter table public.member_reading enable row level security;
alter table public.member_awards enable row level security;
alter table public.member_newsletter enable row level security;
alter table public.member_admins enable row level security;

revoke all on public.member_profiles, public.member_articles, public.member_favorites,
  public.member_reading, public.member_awards, public.member_newsletter,
  public.member_admins from anon, authenticated;
grant select on public.member_profiles, public.member_articles, public.member_favorites,
  public.member_reading, public.member_awards, public.member_newsletter to authenticated;
grant update(full_name) on public.member_profiles to authenticated;
grant insert(user_id, article_slug), delete on public.member_favorites to authenticated;
grant insert(user_id, article_slug, progress), update(progress), delete on public.member_reading to authenticated;
grant all on public.member_profiles, public.member_articles, public.member_favorites,
  public.member_reading, public.member_awards, public.member_newsletter,
  public.member_admins to service_role;

create policy profile_read on public.member_profiles for select to authenticated using (user_id = (select auth.uid()));
create policy profile_update on public.member_profiles for update to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy articles_read on public.member_articles for select to authenticated using (true);
create policy favorites_owner on public.member_favorites for all to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy reading_owner on public.member_reading for all to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy awards_read on public.member_awards for select to authenticated using (user_id = (select auth.uid()));
create policy newsletter_read on public.member_newsletter for select to authenticated using (user_id = (select auth.uid()));

create function public.initialize_member() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  insert into public.member_profiles(user_id, full_name)
  values (new.id, left(coalesce(nullif(trim(new.raw_user_meta_data->>'full_name'), ''), 'مستكشف'), 120));
  return new;
end;
$$;
revoke all on function public.initialize_member() from public, anon, authenticated;
create trigger initialize_member after insert on auth.users
  for each row execute function public.initialize_member();
-- Backfill accounts created before this migration, without overwriting profiles.
insert into public.member_profiles(user_id, full_name)
select id, left(coalesce(nullif(trim(raw_user_meta_data->>'full_name'), ''), 'مستكشف'), 120)
from auth.users on conflict (user_id) do nothing;

create function public.stamp_member_reading() returns trigger
language plpgsql set search_path = '' as $$
begin new.updated_at = now(); return new; end;
$$;
revoke all on function public.stamp_member_reading() from public, anon, authenticated;
create trigger stamp_member_reading before update on public.member_reading
  for each row execute function public.stamp_member_reading();

-- Bounded admin report; role is never taken from editable user metadata.
create function public.member_admin_summary()
returns table(members bigint, newsletter_pending bigint, newsletter_subscribed bigint)
language plpgsql stable security definer set search_path = '' as $$
begin
  if not exists(select 1 from public.member_admins where user_id = (select auth.uid())) then
    raise exception 'Forbidden' using errcode = '42501';
  end if;
  return query select (select count(*) from public.member_profiles),
    (select count(*) from public.member_newsletter where status = 'pending'),
    (select count(*) from public.member_newsletter where status = 'subscribed');
end;
$$;
revoke all on function public.member_admin_summary() from public, anon, authenticated;
grant execute on function public.member_admin_summary() to authenticated;
commit;
