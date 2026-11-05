// PostgreSQL in WASM; auth schema/roles below emulate Supabase, not its Auth API.
import { readFile } from 'node:fs/promises';
import assert from 'node:assert/strict';
const { PGlite } = await import(process.argv[2] || '@electric-sql/pglite');
const db = new PGlite();
let checks = 0;
const a = '00000000-0000-0000-0000-000000000001';
const b = '00000000-0000-0000-0000-000000000002';
await db.exec(`
  create role anon; create role authenticated; create role service_role bypassrls;
  create schema auth;
  create table auth.users(id uuid primary key, raw_user_meta_data jsonb);
  create function auth.uid() returns uuid language sql stable as
    $$ select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$;
  grant usage on schema auth, public to anon, authenticated, service_role;
  grant execute on function auth.uid() to anon, authenticated, service_role;
`);
const migration = await readFile(new URL('../supabase/migrations/202611050001_membership.sql', import.meta.url), 'utf8');
await db.exec(migration);
await db.exec(`insert into auth.users values ('${a}', '{"full_name":"Member A"}'), ('${b}', '{"full_name":"Member B", "role":"admin"}');`);
const asRole = async (role, uid, sql) => {
  try {
    await db.exec('begin');
    await db.exec(`set local role ${role}; set local "request.jwt.claim.sub" = '${uid}';`);
    return await db.query(sql);
  } finally { await db.exec('rollback'); }
};
const denied = async (role, uid, sql) => {
  await assert.rejects(asRole(role, uid, sql)); checks++;
};
assert.equal((await db.query('select count(*)::int n from public.member_profiles')).rows[0].n, 2); checks++;
assert.equal((await asRole('authenticated', a, 'select * from public.member_profiles')).rows.length, 1); checks++;
assert.equal((await asRole('authenticated', a, `update public.member_profiles set full_name='Hacked' where user_id='${b}' returning *`)).rows.length, 0); checks++;
assert.equal((await asRole('authenticated', a, `update public.member_profiles set full_name='Updated' where user_id='${a}' returning *`)).rows[0].full_name, 'Updated'); checks++;
await denied('authenticated', a, `update public.member_profiles set user_id='${b}' where user_id='${a}'`);
await denied('authenticated', a, `insert into public.member_profiles values ('${a}', 'Fake', now())`);
for (const table of ['member_profiles','member_articles','member_favorites','member_reading','member_awards','member_newsletter','member_admins']) {
  await denied('anon', '', `select * from public.${table}`);
}
for (const table of ['member_favorites', 'member_reading']) {
  const fields = table === 'member_reading' ? ',progress' : '';
  const values = table === 'member_reading' ? ',40' : '';
  await denied('authenticated', a, `insert into public.${table}(user_id,article_slug${fields}) values ('${b}','apollo-11'${values})`);
  await denied('authenticated', a, `insert into public.${table}(user_id,article_slug${fields}) values ('${a}','unknown-article'${values})`);
  await db.exec(`insert into public.${table}(user_id,article_slug${fields}) values ('${b}','apollo-11'${values})`);
  assert.equal((await asRole('authenticated', a, `select * from public.${table}`)).rows.length, 0); checks++;
  assert.equal((await asRole('authenticated', a, `delete from public.${table} where user_id='${b}' returning *`)).rows.length, 0); checks++;
  assert.equal((await asRole('authenticated', a, `insert into public.${table}(user_id,article_slug${fields}) values ('${a}','apollo-11'${values}) returning *`)).rows.length, 1); checks++;
}
await denied('authenticated', a, `insert into public.member_reading(user_id,article_slug,progress) values ('${a}','apollo-8',101)`);
await denied('authenticated', a, `insert into public.member_awards(user_id,award_key,points) values ('${a}','fake',1000)`);
await denied('authenticated', a, `insert into public.member_newsletter(user_id,status,consent_version,confirmed_at) values ('${a}','subscribed','v1',now())`);
await denied('authenticated', b, `insert into public.member_admins values ('${b}')`);
await denied('authenticated', b, 'select * from public.member_admin_summary()');
await denied('anon', '', 'select * from public.member_admin_summary()');
await db.exec(`insert into public.member_admins values ('${a}'); insert into public.member_awards(user_id,award_key,points,badge) values ('${b}','trusted',10,'Explorer');`);
assert.equal((await asRole('authenticated', a, 'select * from public.member_admin_summary()')).rows[0].members, 2); checks++;
assert.equal((await asRole('authenticated', a, 'select * from public.member_awards')).rows.length, 0); checks++;
await db.exec(`delete from auth.users where id='${b}'`);
assert.equal((await db.query(`select * from public.member_reading where user_id='${b}'`)).rows.length, 0); checks++;
console.log(`${checks} membership database security checks passed.`);
await db.close();
