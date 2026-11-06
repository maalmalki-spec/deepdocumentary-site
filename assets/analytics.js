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
