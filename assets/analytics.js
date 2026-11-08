(() => {
  const measurementId = 'G-CBDETZZYPG';
  if (!['deepdocumentary.com', 'www.deepdocumentary.com'].includes(location.hostname)
      || document.getElementById('dd-google-tag')) return;

  // Preserve the choices of visitors who previously disabled analytics.
  let optedOut = navigator.globalPrivacyControl === true;
  try {
    optedOut ||= localStorage.getItem('dd-analytics-consent') === 'no';
  } catch {
    // The browser may block access to local storage.
  }

  window['ga-disable-' + measurementId] = optedOut;
  if (optedOut) return;

  window.dataLayer = window.dataLayer || [];
  function gtag() { window.dataLayer.push(arguments); }
  window.gtag = gtag;
  gtag('consent', 'default', {
    ad_storage: 'denied',
    ad_user_data: 'denied',
    ad_personalization: 'denied'
  });
  gtag('js', new Date());
  gtag('config', measurementId, {
    allow_google_signals: false,
    allow_ad_personalization_signals: false,
    page_location: location.origin + location.pathname,
    page_referrer: ''
  });

  const tag = document.createElement('script');
  tag.id = 'dd-google-tag';
  tag.async = true;
  tag.src = 'https://www.googletagmanager.com/gtag/js?id=' + measurementId;
  document.head.append(tag);
})();

/* Universal navigation is independent of analytics and privacy opt-out. */
(() => {
  if (document.getElementById('dd-shared-header-loader')) return;
  const css = document.createElement('link');
  css.id = 'dd-shared-header-styles';
  css.rel = 'stylesheet';
  css.href = '/assets/shared-header.css?v=1';
  document.head.append(css);
  const script = document.createElement('script');
  script.id = 'dd-shared-header-loader';
  script.src = '/assets/shared-header.js?v=1';
  script.defer = true;
  document.head.append(script);
})();

/* Privacy-aware behavioral events. GA4 only; no personal text or identifiers. */
(() => {
  if (!['deepdocumentary.com', 'www.deepdocumentary.com'].includes(location.hostname)) return;
  if (navigator.globalPrivacyControl === true) return;
  try { if (localStorage.getItem('dd-analytics-consent') === 'no') return; } catch {}
  if (location.pathname === '/dashboard.html') return;
  const send = (name, params = {}) => {
    if (typeof window.gtag === 'function') window.gtag('event', name, params);
  };
  const path = location.pathname;
  const isArticle = /^\/articles\//.test(path) || /historical-event/.test(path);
  const lang = document.documentElement.lang?.toLowerCase().startsWith('en') ? 'en' : 'ar';
  const base = { content_path: path.slice(0, 100), content_language: lang };
  if (isArticle) {
    const reached = new Set();
    let lastScroll = 0;
    const measure = () => {
      const root = document.documentElement;
      const max = Math.max(0, root.scrollHeight - innerHeight);
      const percent = max ? Math.min(100, Math.round(scrollY / max * 100)) : 100;
      for (const threshold of [25, 50, 75, 90]) {
        if (percent >= threshold && !reached.has(threshold)) {
          reached.add(threshold);
          send('article_scroll', { ...base, scroll_percent: threshold });
        }
      }
    };
    let scheduled = false;
    addEventListener('scroll', () => {
      if (scheduled) return;
      scheduled = true;
      setTimeout(() => { scheduled = false; measure(); }, 250);
    }, { passive: true });
    addEventListener('load', measure, { once: true });
    // Active reading time, excluding hidden/background tabs and inactivity.
    let activeSeconds = 0;
    let lastActivity = Date.now();
    for (const event of ['pointerdown', 'keydown', 'scroll']) {
      addEventListener(event, () => { lastActivity = Date.now(); }, { passive: true });
    }
    const timer = setInterval(() => {
      if (document.visibilityState !== 'visible' || Date.now() - lastActivity > 60000) return;
      activeSeconds += 5;
      if ([30, 60, 120, 300].includes(activeSeconds)) {
        send('article_read_time', { ...base, read_seconds: activeSeconds });
      }
      if (activeSeconds >= 300) clearInterval(timer);
    }, 5000);
  }
  document.addEventListener('click', (event) => {
    const target = event.target instanceof Element ? event.target.closest('a,button') : null;
    if (!target) return;
    const href = target.tagName === 'A' ? target.getAttribute('href') || '' : '';
    const category = target.tagName === 'BUTTON' ? 'button'
      : /^https?:\/\//i.test(href) && !href.startsWith(location.origin) ? 'external_link'
      : 'internal_link';
    send('site_click', { ...base, click_category: category });
  }, { passive: true });
  // Track submitted search terms by length only, never the actual query.
  document.addEventListener('submit', (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    const field = form.querySelector('input[type="search"],input[name="q"],input[name="query"]');
    if (!(field instanceof HTMLInputElement)) return;
    const length = field.value.trim().length;
    if (length) send('site_search', { ...base, query_length: Math.min(length, 100) });
  });
})();
