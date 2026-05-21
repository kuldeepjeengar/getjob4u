// Site-wide Google Analytics event tracking.
//
// Strategy:
//   1) Delegated listener catches every click on [data-gtag] and fires a
//      gtag('event', ...) with the attribute payload.
//   2) Auto-tracking falls back to .btn / .feature-card / .med-btn / .star
//      / .nav-cta / .tab when no explicit data-gtag is present — so any new
//      CTA is tracked by default with no extra wiring.
//   3) Outbound links (a[href] to a different origin) are tracked as
//      'outbound_click'.
//   4) Form submissions on the ATS, email, and feedback forms emit a
//      'form_submit' event so we can build funnels in GA4.
//
// Exposes window.g4uTrack(event, params) for inline use.
(function () {
  'use strict';

  function send(event, params) {
    try {
      if (typeof window.gtag === 'function') {
        window.gtag('event', event, params || {});
      }
    } catch (e) { /* never break the UI on tracking errors */ }
  }

  // Public helper.
  window.g4uTrack = send;

  // Fire the per-page page_view with the category provided by base.html.
  if (window.__G4U_PAGE__) {
    send('page_view', {
      page_title: document.title,
      page_location: window.location.href,
      page_path: window.location.pathname,
      page_category: window.__G4U_PAGE__.category,
      page_section: window.__G4U_PAGE__.section,
    });
  }

  // ----- click tracking ----------------------------------------------------

  function labelFor(el) {
    return (
      el.getAttribute('data-gtag-label') ||
      (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 80) ||
      el.getAttribute('aria-label') ||
      el.getAttribute('href') ||
      el.id ||
      ''
    );
  }

  function inferCategory(el) {
    if (el.closest('.site-header')) return 'nav_header';
    if (el.closest('.site-footer')) return 'nav_footer';
    if (el.closest('.hero')) return 'hero';
    if (el.closest('.feature-grid')) return 'feature_card';
    if (el.closest('.how-to')) return 'how_to';
    if (el.closest('.faq')) return 'faq';
    if (el.closest('.testimonials')) return 'testimonial';
    if (el.closest('.share-row')) return 'share';
    if (el.closest('form')) return 'form';
    return 'cta';
  }

  function autoEvent(el) {
    if (el.matches('.feature-card')) return 'feature_card_click';
    if (el.matches('.med-btn'))      return 'mode_toggle';
    if (el.matches('.tab'))          return 'tab_switch';
    if (el.matches('.star'))         return 'rating_select';
    if (el.matches('.nav-cta'))      return 'nav_cta_click';
    if (el.matches('.faq-item summary')) return 'faq_open';
    return 'cta_click';
  }

  document.addEventListener('click', function (evt) {
    // Pick up the first useful ancestor: explicit data-gtag wins, else any
    // .btn / link / known interactive class.
    const el =
      evt.target.closest('[data-gtag]') ||
      evt.target.closest('.btn, .feature-card, .med-btn, .tab, .star, .nav-cta, .share-btn, .faq-item summary, a.channel-card, a.course-card, a.blog-card');

    if (!el) return;

    const explicit = el.getAttribute('data-gtag');
    const event = explicit || autoEvent(el);
    const label = labelFor(el);
    const category = el.getAttribute('data-gtag-category') || inferCategory(el);

    const params = {
      event_category: category,
      event_label: label,
      page_path: window.location.pathname,
    };

    // Outbound link?
    const href = el.getAttribute && el.getAttribute('href');
    if (href && /^https?:\/\//i.test(href)) {
      try {
        const url = new URL(href, window.location.href);
        if (url.host && url.host !== window.location.host) {
          send('outbound_click', Object.assign({}, params, { link_url: href, link_domain: url.host }));
          return;
        }
      } catch (e) { /* fall through */ }
    }

    send(event, params);
  }, true);

  // ----- form submissions --------------------------------------------------

  const FORM_EVENTS = {
    atsForm:       { event: 'ats_scan_submit',     category: 'ats_scanner' },
    emailForm:     { event: 'email_generate_submit', category: 'email_generator' },
    feedbackForm:  { event: 'feedback_submit',     category: 'feedback' },
  };

  Object.keys(FORM_EVENTS).forEach(function (id) {
    const f = document.getElementById(id);
    if (!f) return;
    f.addEventListener('submit', function () {
      const cfg = FORM_EVENTS[id];
      send(cfg.event, { event_category: cfg.category, page_path: window.location.pathname });
    });
  });

  // ----- scroll depth (useful reach signal) --------------------------------

  const sentDepths = {};
  function trackScroll() {
    const h = document.documentElement;
    const scrolled = (h.scrollTop + window.innerHeight) / h.scrollHeight;
    [25, 50, 75, 100].forEach(function (pct) {
      if (!sentDepths[pct] && scrolled * 100 >= pct) {
        sentDepths[pct] = true;
        send('scroll_depth', { percent: pct, page_path: window.location.pathname });
      }
    });
  }
  let scrollTimer = null;
  window.addEventListener('scroll', function () {
    if (scrollTimer) return;
    scrollTimer = setTimeout(function () { scrollTimer = null; trackScroll(); }, 250);
  }, { passive: true });
})();
