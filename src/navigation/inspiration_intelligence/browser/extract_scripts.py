"""Provider-specific perception browser extraction scripts — scroll, cookies, smart selectors."""
from __future__ import annotations

import json

# Run before extraction: dismiss cookies + scroll to hydrate lazy grids
PREPARE_PAGE_SCRIPT = """
(async () => {
  const click = (sel) => {
    const el = document.querySelector(sel);
    if (el) { el.click(); return true; }
    return false;
  };
  const labels = ['accept', 'agree', 'got it', 'allow all', 'i agree'];
  for (const btn of document.querySelectorAll('button, a[role="button"], [class*="accept"]')) {
    const t = (btn.textContent || '').trim().toLowerCase();
    if (labels.some((l) => t.includes(l))) { btn.click(); break; }
  }
  click('#onetrust-accept-btn-handler');
  click('[data-testid="cookie-accept"]');
  click('#cookiescript_accept');
  for (let y = 0; y <= 2400; y += 600) {
    window.scrollTo(0, y);
    await new Promise((r) => setTimeout(r, 350));
  }
  window.scrollTo(0, 0);
  return { scrolled: true, links: document.querySelectorAll('a[href]').length };
})()
"""

AWWWARDS_EXTRACT = """
(() => {
  const hits = [];
  const seen = new Set();
  const skip = new Set(['websites', 'login', 'signup', 'pricing', 'jobs']);
  for (const a of document.querySelectorAll('a[href*="/sites/"]')) {
    const href = (a.href || '').split('?')[0];
    const m = href.match(/\\/sites\\/([^/?#]+)/);
    if (!m) continue;
    const id = m[1];
    if (seen.has(id) || skip.has(id)) continue;
    seen.add(id);
    const title = a.querySelector('h3,h2,.title')?.textContent?.trim()
      || a.getAttribute('aria-label')?.trim()
      || a.querySelector('img')?.alt
      || id.replace(/-/g, ' ');
    const img = a.querySelector('img');
    hits.push({
      external_id: id,
      title: title.slice(0, 140),
      url: href,
      preview_url: img?.currentSrc || img?.src || img?.getAttribute('data-src') || '',
    });
    if (hits.length >= 40) break;
  }
  return { hits, url: location.href, count: hits.length };
})()
"""

GODLY_EXTRACT = """
(() => {
  const hits = [];
  const seen = new Set();
  for (const a of document.querySelectorAll('a[href*="/i/"]')) {
    const href = (a.href || '').split('?')[0];
    const m = href.match(/\\/i\\/([^/?#]+)/);
    if (!m) continue;
    const id = m[1];
    if (seen.has(id)) continue;
    seen.add(id);
    const slug = id.replace(/^[a-z0-9]+-/, '').replace(/-/g, ' ');
    const title = a.querySelector('h2,h3,img')?.alt?.trim()
      || a.getAttribute('aria-label')?.trim()
      || slug
      || id;
    const img = a.querySelector('img');
    hits.push({
      external_id: id,
      title: title.slice(0, 140),
      url: href,
      preview_url: img?.currentSrc || img?.src || img?.getAttribute('data-src') || '',
    });
    if (hits.length >= 40) break;
  }
  return { hits, url: location.href, count: hits.length };
})()
"""

_LANDBOOK_SKIP = [
	'template', 'website', 'portfolio', 'blog', 'ecommerce', 'other', 'about-us-page',
	'career-page', 'sign-up-page', 'pricing-page', 'case-study', 'blog-post',
	'product-listing-page', 'product-page', 'landing-page', 'design', 'designs',
]

LANDBOOK_EXTRACT = f"""
(async () => {{
  const skipSet = new Set({json.dumps(_LANDBOOK_SKIP)});
  for (let i = 0; i < 4; i++) {{
    const btn = [...document.querySelectorAll('button,a')].find((el) => /load more|show more/i.test(el.textContent || ''));
    if (btn) {{ btn.click(); await new Promise((r) => setTimeout(r, 1800)); }}
    window.scrollTo(0, document.body.scrollHeight);
    await new Promise((r) => setTimeout(r, 800));
  }}
  const hits = [];
  const seen = new Set();
  for (const a of document.querySelectorAll('a[href*="/design/"]')) {{
    const href = (a.href || '').split('?')[0].split('#')[0];
    const m = href.match(/\\/design\\/([^/?#]+)/);
    if (!m) continue;
    const id = m[1];
    if (seen.has(id) || skipSet.has(id)) continue;
    seen.add(id);
    const title = a.querySelector('h3,h2,img')?.alt?.trim()
      || a.getAttribute('aria-label')?.trim()
      || id.replace(/-/g, ' ');
    const img = a.querySelector('img');
    hits.push({{
      external_id: id,
      title: title.slice(0, 140),
      url: href,
      preview_url: img?.currentSrc || img?.src || img?.getAttribute('data-src') || '',
    }});
    if (hits.length >= 40) break;
  }}
  return {{ hits, url: location.href, count: hits.length }};
}})()
"""

SITEINSPIRE_EXTRACT = """
(() => {
  const hits = [];
  const seen = new Set();
  for (const a of document.querySelectorAll('a[href*="/website/"]')) {
    const href = (a.href || '').split('?')[0];
    const m = href.match(/\\/website\\/(\\d+)/);
    if (!m) continue;
    const id = m[1];
    if (seen.has(id)) continue;
    seen.add(id);
    const title = a.querySelector('h2,.website-title')?.textContent?.trim()
      || a.getAttribute('aria-label')?.replace(/^View details for\\s+/i, '').trim()
      || id;
    const img = a.querySelector('img');
    hits.push({
      external_id: id,
      title: title.slice(0, 140),
      url: href,
      preview_url: img?.currentSrc || img?.src || img?.getAttribute('data-src') || '',
    });
    if (hits.length >= 40) break;
  }
  return { hits, url: location.href, count: hits.length };
})()
"""

PROVIDER_EXTRACT_SCRIPTS: dict[str, str] = {
	'awwwards': AWWWARDS_EXTRACT,
	'godly': GODLY_EXTRACT,
	'land-book': LANDBOOK_EXTRACT,
	'siteinspire': SITEINSPIRE_EXTRACT,
}
