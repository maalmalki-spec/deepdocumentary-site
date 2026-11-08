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
