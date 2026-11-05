const $ = id => document.getElementById(id);
const config = window.DD_MEMBER_CONFIG;
const message = text => { $('status').textContent = text; };
let client;
let currentUser;
let renderVersion = 0;
const callback = new URL('account.html', location.href).href;
function configured(c) {
  if (!c?.enabled || !/^sb_publishable_[A-Za-z0-9_-]+$/.test(c.publishableKey || '')) return false;
  try { const u = new URL(c.supabaseUrl); return u.protocol === 'https:' && /^[a-z0-9-]+\.supabase\.co$/.test(u.hostname) && u.pathname === '/'; }
  catch { return false; }
}
async function action(button, work) {
  button.disabled = true;
  try { await work(); }
  catch { message('تعذر إتمام الطلب. تحقق من البيانات والاتصال وحاول مجددًا.'); }
  finally { button.disabled = false; }
}
function checked(result) { if (result.error) throw result.error; return result.data; }
function bindForm(id, work) {
  $(id).addEventListener('submit', event => {
    event.preventDefault();
    const form = event.currentTarget;
    void action(form.querySelector('button'), async () => {
      await work(Object.fromEntries(new FormData(form)));
      form.querySelectorAll('input[type=password]').forEach(input => { input.value = ''; });
    });
  });
}
function clearPrivate() {
  currentUser = null;
  $('profile').hidden = true;
  $('recovery').hidden = true;
  $('admin').disabled = true;
  $('admin-result').textContent = '';
  for (const id of ['favorites', 'reading', 'badges', 'email', 'points']) $(id).replaceChildren();
  $('name').elements.full_name.value = '';
}
async function render() {
  const version = ++renderVersion;
  clearPrivate();
  $('auth').hidden = true;
  const { data, error } = await client.auth.getUser();
  if (version !== renderVersion) return;
  if (error || !data.user) { $('auth').hidden = false; return; }
  const user = data.user;
  const results = await Promise.all([
    client.from('member_profiles').select('full_name').eq('user_id', user.id).single(),
    client.from('member_favorites').select('article_slug').eq('user_id', user.id).order('created_at', {ascending:false}).limit(100),
    client.from('member_reading').select('article_slug,progress').eq('user_id', user.id).order('updated_at', {ascending:false}).limit(100),
    client.from('member_awards').select('points,badge').eq('user_id', user.id).limit(1000)
  ]);
  if (version !== renderVersion) return;
  const [profile, favorites, reading, awards] = results.map(checked);
  currentUser = user;
  $('email').textContent = user.email || '';
  $('name').elements.full_name.value = profile.full_name;
  $('profile').hidden = false;
  $('admin').disabled = false;
  for (const [id, rows] of [['favorites', favorites], ['reading', reading]]) {
    if (!rows.length) { const li = document.createElement('li'); li.textContent = 'لا توجد عناصر بعد.'; $(id).append(li); }
    for (const row of rows) {
      if (!/^[a-z0-9]+(-[a-z0-9]+)*$/.test(row.article_slug)) continue;
      const li = document.createElement('li');
      const link = document.createElement('a');
      link.href = `articles/${row.article_slug}.html`;
      link.textContent = row.article_slug + (id === 'reading' ? ` · ${row.progress}%` : '');
      li.append(link);
      const remove = document.createElement('button'); remove.type = 'button'; remove.textContent = 'حذف';
      remove.setAttribute('aria-label', `حذف ${row.article_slug}`);
      remove.onclick = () => void action(remove, async () => {
        checked(await client.from(id === 'favorites' ? 'member_favorites' : 'member_reading').delete().eq('user_id', user.id).eq('article_slug', row.article_slug));
        await render();
      });
      li.append(remove); $(id).append(li);
    }
  }
  $('points').textContent = `${awards.reduce((sum, row) => sum + row.points, 0)} نقطة`;
  for (const row of awards.filter(row => row.badge)) { const li = document.createElement('li'); li.textContent = row.badge; $('badges').append(li); }
  if (!awards.some(row => row.badge)) $('badges').textContent = 'لا توجد شارات بعد.';
}
async function start() {
  // No SDK download, auth request or session processing before explicit activation.
  if (!configured(config)) return;
  try {
    const { createClient } = await import('https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.49.8/+esm');
    client = createClient(config.supabaseUrl, config.publishableKey, {auth:{flowType:'pkce', detectSessionInUrl:true}});
    let recovering = new URLSearchParams(location.search).get('mode') === 'recovery';
    client.auth.onAuthStateChange((event) => {
      if (event === 'PASSWORD_RECOVERY') recovering = true;
      // Never await SDK queries inside the auth callback's lock.
      setTimeout(() => {
        if (event === 'SIGNED_OUT') recovering = false;
        void render().then(() => {
          $('recovery').hidden = !recovering || !currentUser;
          if (recovering) $('profile').hidden = true;
        }).catch(() => message('تعذر تحميل الحساب. حاول تحديث الصفحة.'));
      }, 0);
    });
    bindForm('signup', async values => {
      const name = values.full_name.trim();
      if (!name) { message('أدخل الاسم الكامل.'); return; }
      checked(await client.auth.signUp({email:values.email.trim(), password:values.password, options:{data:{full_name:name}, emailRedirectTo:callback}}));
      message('إذا كانت البيانات مؤهلة للتسجيل، ستصلك رسالة تأكيد. تحقق من بريدك.');
    });
    bindForm('signin', async values => {
      checked(await client.auth.signInWithPassword({email:values.email.trim(), password:values.password}));
      message('تم تسجيل الدخول.');
    });
    bindForm('reset', async values => {
      checked(await client.auth.resetPasswordForEmail(values.email.trim(), {redirectTo:callback + '?mode=recovery'}));
      message('إذا كان البريد مسجلًا، ستصلك رسالة استعادة كلمة المرور.');
    });
    bindForm('password', async values => {
      checked(await client.auth.updateUser({password:values.password}));
      recovering = false; $('recovery').hidden = true;
      history.replaceState(null, '', 'account.html');
      message('حُفظت كلمة المرور.'); await render();
    });
    bindForm('name', async values => {
      if (!currentUser) return;
      const name = values.full_name.trim();
      if (!name) { message('أدخل الاسم الكامل.'); return; }
      checked(await client.from('member_profiles').update({full_name:name}).eq('user_id', currentUser.id));
      message('حُفظ الاسم.');
    });
    $('google').onclick = () => void action($('google'), async () => {
      checked(await client.auth.signInWithOAuth({provider:'google', options:{redirectTo:callback}}));
    });
    $('signout').onclick = () => void action($('signout'), async () => {
      checked(await client.auth.signOut()); ++renderVersion; clearPrivate(); $('auth').hidden = false; message('تم تسجيل الخروج.');
    });
    $('admin').onclick = () => void action($('admin'), async () => {
      const result = await client.rpc('member_admin_summary');
      if (result.error) { $('admin-result').textContent = 'غير مصرح لك، أو تعذر تحميل الإحصاءات.'; return; }
      const row = result.data[0];
      $('admin-result').textContent = `الأعضاء: ${row.members} · بانتظار تأكيد البريد: ${row.newsletter_pending} · مشتركو القائمة: ${row.newsletter_subscribed}`;
    });
    await render();
    message('أهلًا بك في حساب المستكشف. الاشتراك البريدي غير مفعّل حاليًا.');
  } catch { clearPrivate(); $('auth').hidden = true; message('خدمة الحساب غير متاحة الآن. يمكنك متابعة قراءة الموقع.'); }
}
void start();
