/* Shared site header for every existing and future public subpage.
   Loaded independently of analytics consent; never changes the homepage. */
(() => {
  if (document.documentElement.dataset.ddHeaderInstalled) return;
  document.documentElement.dataset.ddHeaderInstalled = '1';
  const init = () => {
    if (location.pathname === '/' || location.pathname === '/index.html') return;
    const old = document.querySelector('body > header, body > .dd-unified-header, header.dd-unified-header');
    if (!old) return;
    if (old.dataset.ddSharedHeader === '1') return;
    const isArticle = location.pathname.includes('/articles/');
    const home = isArticle ? '../index.html' : 'index.html';
    const logo = isArticle ? '../assets/logo.svg' : 'assets/logo.svg';
    const priorToggle = old.querySelector('#toggle');
    const lang = (() => { try { return localStorage.getItem('dd-language') === 'en' ? 'en' : 'ar'; } catch { return document.documentElement.lang === 'en' ? 'en' : 'ar'; } })();
    const header = document.createElement('header');
    header.className = 'dd-global-header';
    header.dataset.ddSharedHeader = '1';
    header.innerHTML = '<a class="dd-global-brand" href="'+home+'" aria-label="Deep Documentary home"><img src="'+logo+'" alt="" width="54" height="54"><span class="dd-global-wordmark"><strong>DEEP DOCUMENTARY</strong><small data-dd-global-tag></small></span></a><nav class="dd-global-controls" aria-label="Site navigation"><a href="'+home+'" data-dd-global-home></a><span data-dd-global-toggle></span></nav>';
    if (priorToggle) {
      // Move the original toggle to preserve existing click listeners and IDs.
      header.querySelector('[data-dd-global-toggle]').replaceWith(priorToggle);
    } else {
      const btn = document.createElement('button');
      btn.id = 'dd-global-language-toggle';
      btn.type = 'button';
      btn.addEventListener('click', () => {
        const next = document.documentElement.lang === 'en' ? 'ar' : 'en';
        try { localStorage.setItem('dd-language', next); } catch {}
        document.documentElement.lang = next;
        document.documentElement.dir = next === 'ar' ? 'rtl' : 'ltr';
        document.querySelectorAll('[data-ar][data-en]').forEach(el => { el.textContent = el.dataset[next]; });
        update();
      });
      header.querySelector('[data-dd-global-toggle]').replaceWith(btn);
    }
    old.replaceWith(header);
    function update() {
      const english = document.documentElement.lang === 'en';
      header.querySelector('[data-dd-global-home]').textContent = english ? 'Home' : 'الرئيسية';
      header.querySelector('[data-dd-global-tag]').textContent = english ? 'In-depth stories worth discovering' : 'الوثائقي العميق · قصص تستحق الاكتشاف';
      const btn = header.querySelector('#dd-global-language-toggle');
      if (btn) btn.textContent = english ? 'العربية 🌐' : '🌐 English';
    }
    update();
    new MutationObserver(update).observe(document.documentElement, {attributes:true,attributeFilter:['lang']});
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, {once:true});
  else init();
})();
