# Issue #68 investigation: Today gutter still offset after PR #67

Dated 2026-10-12. Investigation only; no application code changes were required.

## Summary

The code on `main` (commit `adc415d`, which includes PR #67's fix) is correct.
The production asset bundle actually being served by `https://d.edgelog.trade/`
at the time of this investigation is **byte-for-byte identical** to a fresh
local build of that exact commit. The gutter-alignment bug does not exist in
the deployed artifact. The most likely explanation for what the owner saw is
a **CDN edge cache (Cloudflare) serving a stale `index.html`** from before the
PR #67 deploy to some client requests, which a client-side hard refresh cannot
bypass. See "Recommended verification" below for how to confirm/rule this out
in minutes rather than waiting on cache TTL.

## What was checked

### 1. Source code on `main`

```
$ grep -n "journal-day\|max-width" frontend/src/views/JournalDay.vue
220:  <div v-if="loading" class="journal-day el-page el-empty-state" ...
221:  <div v-else-if="loadError" class="journal-day el-page">...
222:  <div v-else-if="day" class="journal-day el-page">
831:  max-width: 100%;   (.scale-buttons -- unrelated internal widget)
863:  max-width: 100%;   (.bias-chart-preview -- unrelated internal widget)
```

No `.journal-day { ... }` rule exists anywhere in the file. PR #67's removal
is intact on `main`.

### 2. Compiled production CSS (`npm run build`, this commit)

```
$ grep -o '\.journal-day[^{]*{[^}]*}' dist/assets/index-*.css
(no output -- rule does not exist in the compiled bundle)

$ grep -o '\.el-page{[^}]*}' dist/assets/index-*.css
.el-page{width:100%;max-width:var(--el-content-max);margin-inline:auto;padding:36px var(--el-page-padding) 48px}
.el-page{padding:20px 16px}   /* @media (max-width:640px) */
```

`.el-page` is global/unscoped (no `[data-v-xxxx]` attribute), so it applies
identically to every page that carries the class.

### 3. Rendered output of that exact build (Playwright + `vite preview`, desktop 1440px)

| Page | left edge | max-width | margin-left | padding-left |
|---|---|---|---|---|
| Dashboard | 230px | 1200px | 10px | 48px |
| Calendar | 230px | 1200px | 10px | 48px |
| **Today** | **230px** | **1200px** | **10px** | **48px** |

All three identical. Full ancestor chain for `.journal-day` on the Today page
(root to `<body>`) shows no competing wrapper, no inline style, no stray
margin anywhere between it and `.app-main`:

```json
[
  { "tag": "DIV", "class": "journal-day el-page", "maxWidth": "1200px", "left": 230 },
  { "tag": "MAIN", "class": "app-main", "maxWidth": "none", "left": 220 },
  { "tag": "DIV", "class": "app-shell", "maxWidth": "none", "left": 0 }
]
```

Screenshots of this exact build: `screenshots/issue68/01-calendar-prod-build.png`,
`screenshots/issue68/02-today-prod-build.png` -- Today's "DAILY JOURNAL" aligns
with Calendar's "JOURNAL CALENDAR" exactly as expected.

### 4. The actual live response from `https://d.edgelog.trade/`

```
$ curl -s -D - https://d.edgelog.trade/
HTTP/2 200
cache-control: public,max-age=10,s-maxage=86400
age: 900
server: cloudflare
cf-cache-status: HIT
x-do-app-origin: 39a14937-f57a-44ee-a590-f770dea98325
...
<script type="module" crossorigin src="/assets/index-1fF9PKdv.js"></script>
<link rel="stylesheet" crossorigin href="/assets/index-5bxZZKy-.css">
```

The referenced asset filenames (`index-1fF9PKdv.js`, `index-5bxZZKy-.css`) are
**exactly** the hashes produced by this investigation's local build of current
`main`. Fetching both files directly from `d.edgelog.trade` and comparing MD5
against the local `dist/` output:

```
8cedb8e0af448d39b4c4a429798afc68  live index-5bxZZKy-.css
8cedb8e0af448d39b4c4a429798afc68  local dist/assets/index-5bxZZKy-.css
0d6a1a31bbb204371e3facdaf91c9ff5  live index-1fF9PKdv.js
0d6a1a31bbb204371e3facdaf91c9ff5  local dist/assets/index-1fF9PKdv.js
```

Identical. **At the moment of this check, the live site is serving the
corrected build.** No service worker is registered anywhere in the app
(checked `src/`, `index.html`, `public/`), so a client-side SW cache is ruled
out as the cause of anything a user might still be seeing.

## Why the owner may still have seen the old layout

The response headers above are the key clue:

```
cache-control: public,max-age=10,s-maxage=86400
cf-cache-status: HIT
age: 900
```

`max-age=10` governs the *browser's* cache (effectively nothing -- a normal
reload always revalidates). `s-maxage=86400` governs *shared/CDN* caches --
Cloudflare, sitting in front of the DO App Platform origin, is allowed to
hold its own cached copy of `index.html` for up to 24 hours. Cloudflare has
many independent edge locations (PoPs); a purge or natural expiry on one PoP
does not affect another. **A client-side hard refresh forces the browser to
skip its own cache, but the request still terminates at whichever Cloudflare
edge node serves that user -- it cannot reach past a stale edge cache to the
origin.** That reproduces exactly what was reported: "hard refresh did not
help."

Given the DNS cutover to the App Platform CNAME happened very recently (same
day, per the issue), it's likely some edge PoPs cached `index.html` from
*before* PR #67 was deployed and haven't yet revalidated against
`s-maxage`'s 24-hour ceiling. The fetch performed for this investigation
happened to land on a PoP whose cache had already refreshed.

This is an infrastructure/CDN-cache condition, not an application bug, and is
outside this investigation's access (no Cloudflare/DO App Platform dashboard
credentials in this environment) and outside issue #68's explicit scope (no
production changes).

## Recommended verification (owner-side, no deploy needed)

1. Open `https://d.edgelog.trade/` in an incognito/private window (bypasses
   browser cache entirely, still subject to CDN edge cache) or from a
   different network/device, and compare.
2. In DevTools Network tab, reload and check the `<script src>`/`<link href>`
   hashes referenced by `index.html` against `index-1fF9PKdv.js` /
   `index-5bxZZKy-.css` (the known-correct hashes for this commit). A
   different hash means a stale cached `index.html`.
3. Check the `cf-cache-status` response header for `index.html` -- `HIT`
   means it came from Cloudflare's edge cache, not freshly from origin.
4. If stale, purge the Cloudflare cache for `d.edgelog.trade` (or at minimum
   purge `/index.html`) via the Cloudflare dashboard -- this resolves it
   immediately rather than waiting out the 24-hour `s-maxage`.
5. Longer-term fix (not made here, since it's an infrastructure/cache-header
   change, not application code, and out of this issue's explicit scope):
   `index.html` should be served with a much shorter/no shared cache
   (e.g. `cache-control: no-cache` or `max-age=0, s-maxage=0`), since it's the
   entry point that references content-hashed assets -- those hashed asset
   files (`/assets/*.js`, `/assets/*.css`) are exactly what's safe to cache
   aggressively/immutably, since their filename itself changes on every
   content change.

## Regression coverage added

`frontend/src/views/JournalDay.spec.js` gained one test asserting the page's
root element carries only `journal-day`/`el-page` (plus the existing
empty/error-state classes) and no inline `style` attribute -- guarding
against a new class or inline style silently reintroducing a competing
width/margin override. jsdom can't run a real CSS cascade, so it can't catch
*this specific* scoped-vs-global specificity bug directly (that was only
catchable by measuring the live rendered page, as this investigation and
PR #67 both did) -- this test guards the easiest way to reintroduce it.
