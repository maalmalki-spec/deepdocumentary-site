(() => {
  const measurementId = 'G-CBDETZYPG';
  const preferenceKey = 'dd-analytics-consent';

  if (['deepdocumentary.com', 'www.deepdocumentary.com'].includes(location.hostname)
      && !document.getElementById('dd-analytics-preferences')) {
    const panel = document.createElement('aside');
    panel.id = 'dd-analytics-preferences';
    panel.style.cssText = 'padding:1rem;text-align:center;background:#151515;color:#fff';
    panel.innerHTML = '<p></p><button type="button"></button> <button type="button"></button>';
    document.body.append(panel);

    const [accept, decline] = panel.querySelectorAll('button');
    for (const button of [accept, decline]) {
      button.style.cssText = 'font:inherit;padding:.4rem .8rem;margin:.2rem;cursor:pointer';
    }
    const message = panel.querySelector('p');
    let choice;
    try {
      choice = localStorage.getItem(preferenceKey);
    } catch {
      // A blocked storage API leaves analytics off until an explicit choice.
    }

    function render() {
      const english = document.documentElement.lang === 'en';
      message.textContent = english
        ? 'Optional Google Analytics helps us understand which pages people read.'
        : 'يساعدنا Google Analytics الاختياري على معرفة الصفحات التي يقرؤها الزوار.';
      accept.textContent = english ? 'Allow analytics' : 'السماح بالإحصاءات';
      decline.textContent = english ? 'Disable analytics' : 'إيقاف الإحصاءات';
      accept.disabled = choice === 'yes';
      decline.disabled = choice === 'no';
    }

    function enableAnalytics() {
      if (document.getElementById('dd-google-tag')) return;

      window['ga-disable-' + measurementId] = false;
      window.dataLayer = window.dataLayer || [];
      function gtag() { window.dataLayer.push(arguments); }
      const consent = {
        ad_storage: 'denied',
        ad_user_data: 'denied',
        ad_personalization: 'denied',
        analytics_storage: 'denied'
      };
      gtag('consent', 'default', consent);
      gtag('consent', 'update', { ...consent, analytics_storage: 'granted' });
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
    }

    function setChoice(value) {
      const wasEnabled = choice === 'yes';
      choice = value;
      let saved = false;
      try {
        localStorage.setItem(preferenceKey, value);
        saved = true;
      } catch {
        // Apply the choice for the current page even if storage is blocked.
      }
      if (value === 'yes') {
        enableAnalytics();
      } else if (wasEnabled) {
        window['ga-disable-' + measurementId] = true;
        for (const name of ['_ga', '_ga_' + measurementId.slice(2)]) {
          document.cookie = name + '=; Max-Age=0; Path=/';
          document.cookie = name + '=; Max-Age=0; Path=/; Domain=deepdocumentary.com';
        }
        if (saved) location.reload();
      }
      render();
    }

    accept.addEventListener('click', () => setChoice('yes'));
    decline.addEventListener('click', () => setChoice('no'));
    new MutationObserver(render).observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['lang']
    });
    render();
    if (choice === 'yes') enableAnalytics();
  }

})();
