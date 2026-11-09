---
name: site-analytics
description: Ship every site or web app with launch basics from the first deploy (Umami analytics, a real favicon set, and a designed share image with title, description and Twitter card tags) and read how it performs. Use whenever an agent builds, launches, deploys or promotes a site, page, demo or experiment, when a launch brief is written, or when the owner asks how a site is doing, how many people visited, or which pages or links did well.
---

# Site analytics and launch basics

A site without analytics is not done: you shipped it to learn whether anyone cares. Add analytics, the favicon set and the share image in the same PR that ships the site, not later.

This skill uses [Umami](https://umami.is) (open source, cookie-free, self-hosted or Umami Cloud). The pattern works with any privacy-friendly analytics tool that has a script tag and an API.

## Set up once

- Choose an instance: self-hosted Umami or Umami Cloud. On a self-hosted instance, expose only the tracker (`/script.js`) and the collector (`POST /api/send`) publicly; keep the admin UI private.
- Put the credentials in your secret manager, not in a repository: `UMAMI_API_URL`, and either `UMAMI_API_KEY` (Cloud) or `UMAMI_USERNAME` and `UMAMI_PASSWORD` (self-hosted). Optional: `UMAMI_TEAM`, `UMAMI_SCRIPT_URL`. See the docstring of [scripts/umami-site.py](scripts/umami-site.py).
- One Umami website per site domain.

## Add a site

1. `python3 <skill-dir>/scripts/umami-site.py add <name> <live-domain>` (idempotent). It prints the website id and the tag, for example:
   `<script defer src="https://<your-umami>/script.js" data-website-id="<id>" data-domains="<live-domain>"></script>`
2. Put the tag in the page `<head>`. Static or Vite: `index.html`. Next.js: `next/script` with `strategy="afterInteractive"` in the root layout. Keep `data-domains` set to the live domain so local dev, preview deployments and headless renders are not counted.
3. Track the one or two actions that matter with attributes, no code: `data-umami-event="cta-click"` on the main button, `data-umami-event="outbound" data-umami-event-url="..."` on key outbound links, a small `umami.track('video-play')` on a video's first `play`. Name events in kebab-case. If the repository already has a typed analytics helper, use it.
4. Before merging, check how production was deployed. If the live deployment came from a manual CLI deploy at a commit that is not on the default branch, merging redeploys older code over it. Stop and ask instead. (One merge of a small analytics PR rolled a site back to month-old code for four minutes this way.)

## Launch basics: favicon and share image

A live site also needs these, in the same PR:

- **Favicon set:** `favicon.ico` (32 px), `icon.svg` or a 512 px PNG, `apple-touch-icon.png` (180 px), all drawn from the project's own mark, never a framework default. Check it at 16 px on a dark and a light tab.
- **Share image:** a 1200x630 PNG designed for the project (its own type, colors and one real visual: a chart, a frame, a screenshot), with the title readable at phone size. No generic gradients or stock art.
- **Meta:** `<title>`, `meta description`, `og:title`, `og:description`, `og:image` (absolute URL), `og:url`, `twitter:card=summary_large_image`, `twitter:image`.
- **Prove it:** `curl -s <url> | grep -E 'og:image|twitter:card|rel="(icon|apple-touch-icon)'`, fetch the og:image URL (200, 1200x630) and render the share card once in a card previewer and look at it.

## Prove analytics before calling it done

- The built output contains the tag, and after deploy the live HTML does too (`curl -s <url> | grep -c '<your-umami-host>'`).
- A real browser visit is counted: load the live URL in a headless browser, see `window.umami` defined and a 2xx from `/api/send`, then `umami-site.py stats <domain> 1` shows the pageview. Say the test visit is yours.
- Umami drops bot traffic but still answers 200, so a default headless visit (`HeadlessChrome` user agent) reads as a false zero. Set a normal user agent first, for example in Puppeteer: `page.setUserAgent((await browser.userAgent()).replace('HeadlessChrome', 'Chrome'))`.
- Pages that never go network-idle (other analytics, WebGL) need `waitUntil: 'domcontentloaded'` and a 10 to 15 second wait: the tracker sends its first pageview only after the document is complete.

## Read performance

- `umami-site.py stats <domain> [days]`: pageviews, visitors, visits, bounces, time on site, top pages.
- Tag promotional links with UTM parameters (`utm_source=x&utm_medium=social&utm_campaign=<slug>&utm_content=<post id>`) so the dashboard shows which post sent readers. Check 24 and 72 hours after a launch.
- Never print the admin password, API keys or tokens.
