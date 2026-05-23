# getjob4u — SEO & Backlinks Playbook

A live checklist of what's already shipped, and what to do this week / month / quarter to actually move organic traffic.

---

## ✅ Already shipped (technical SEO)

These changes are live in the codebase as of this push:

- **Structured data (JSON-LD) on every page**
  - `Organization`, `WebSite` (with SearchAction), `SiteNavigationElement` on every page (`templates/base.html`)
  - `CollectionPage` + `ItemList` of `SoftwareApplication` items on `/free-ai-tools`
  - `CollectionPage` + `ItemList` of `Course` items on `/free-courses`
  - `CollectionPage` + `ItemList` of `HowTo` per roadmap on `/career-roadmap`
  - `AboutPage` + `Person` schema on `/about` (helps Google Knowledge Graph link the founder)
  - `ContactPage` + `Organization` + `ContactPoint` on `/contact`
  - `FAQPage`, `HowTo`, `SoftwareApplication` (with `aggregateRating`) on `/`
- **Sitemap improvements** (`/sitemap.xml`) — re-prioritized, image entries added, all 14 URLs covered
- **Robots.txt** allows GPTBot, ChatGPT-User, PerplexityBot, ClaudeBot, Google-Extended, Applebot-Extended → answer-engine reach (AEO)
- **Internal cross-linking** — every new page has a "Related resources" block linking 6 sibling pages
- **Breadcrumbs** with `BreadcrumbList` schema on every sub-page
- **Open Graph + Twitter Card** on every page
- **Canonical URLs** set
- **Mobile-first responsive** (a separate fix shipped) — Google uses mobile-first indexing
- **Pre-connect + font-display: swap** for Google Fonts

## ☐ Do today (15 minutes)

1. **Submit sitemap to Google**
   - Go to [Google Search Console](https://search.google.com/search-console)
   - Add `getjob4u.com` as a property (use the DNS-record method for full-domain coverage)
   - Submit `https://getjob4u.com/sitemap.xml` under **Sitemaps**
   - Use **URL Inspection** → **Request indexing** for each of these:
     - `/`, `/free-ai-tools`, `/free-courses`, `/career-roadmap`, `/about`, `/contact`

2. **Submit to Bing Webmaster Tools** ([bing.com/webmasters](https://www.bing.com/webmasters)) — same sitemap. Bing also feeds DuckDuckGo + ChatGPT Browse.

3. **Test your structured data**
   - Run each page through [Google Rich Results Test](https://search.google.com/test/rich-results)
   - Run [Schema.org Validator](https://validator.schema.org/) on at least `/`, `/career-roadmap`, `/free-courses`

4. **Verify Open Graph previews**
   - [LinkedIn Post Inspector](https://www.linkedin.com/post-inspector/)
   - [Twitter/X Card Validator](https://cards-dev.twitter.com/validator)
   - [Facebook Sharing Debugger](https://developers.facebook.com/tools/debug/)

---

## ☐ Do this week — high-quality backlinks (Tier 1)

These platforms have **high domain authority** AND **active job-seeker / dev audiences**. Each one is worth 5–50 random Web 2.0 backlinks.

### Free directory submissions (do all 12 today)
- [ ] [Product Hunt](https://www.producthunt.com/posts/new) — launch as "Free ATS resume scanner + AI/ML career toolkit"
- [ ] [BetaList](https://betalist.com/submit) — startup directory
- [ ] [AlternativeTo](https://alternativeto.net/calls/contribute/) — list as alternative to Resume Worded, Jobscan, Enhancv
- [ ] [SaaSHub](https://www.saashub.com/) — submit getjob4u as a SaaS tool
- [ ] [There's an AI for That](https://theresanaiforthat.com/submit/) — list multiple tools: ATS scanner, cold email gen, AI tools index
- [ ] [Futurepedia](https://www.futurepedia.io/submit-tool) — AI tools directory
- [ ] [AI Tools Directory](https://aitools.directory/submit-tool/)
- [ ] [Toolify.ai](https://www.toolify.ai/submit) — AI tools directory
- [ ] [Insidr.ai Tools](https://www.insidr.ai/submit-ai-tool/)
- [ ] [LaunchingNext](https://www.launchingnext.com/submit/)
- [ ] [BetaPage](https://betapage.co/submit-startup)
- [ ] [Startup Stash](https://startupstash.com/add-listing/)

### Developer / community platforms (your audience IS here)
- [ ] **Hacker News** — Submit `https://getjob4u.com` as a Show HN. Title: "Show HN: Free ATS resume scanner + AI/ML career toolkit (no signup)". Post Tue 7 AM PT for best traction.
- [ ] **Reddit** — post natively to:
  - r/MachineLearning — flair "Project", explain the problem you're solving (resumes for ML roles)
  - r/datascience — share the ATS scanner + roadmap
  - r/learnmachinelearning — share the free courses + roadmap pages
  - r/cscareerquestions — share the ATS scanner
  - r/india + r/developersIndia — your home market
  - r/Btechtards — Indian college students hunting first jobs
  - **Important**: 9 helpful comments before 1 self-promo post in each sub, or you'll be banned.
- [ ] **Dev.to** — write a 1,200-word article: "I built a free ATS scanner for AI/ML resumes — here's what 90% of resumes get wrong"
- [ ] **Hashnode** — same article, repost canonical
- [ ] **Medium / Towards Data Science** — same article (cross-canonical)
- [ ] **LinkedIn article (long-form)** — same article, native post
- [ ] **IndieHackers** — share milestone post: "I built a free toolkit for AI/ML job seekers — here's what I learned"
- [ ] **Lobsters** — submit if you have an invite (high-value backlink)

---

## ☐ Do this month — long-term backlinks (Tier 2)

### Curated free-resource lists (most likely to link back)
- [ ] [Free for Developers](https://github.com/ripienaar/free-for-dev) — open PR adding getjob4u to "Tools for Teams or Collaboration"
- [ ] [Awesome AI Tools](https://github.com/mahseema/awesome-ai-tools) — open PR
- [ ] [Awesome Machine Learning](https://github.com/josephmisiti/awesome-machine-learning) — request inclusion in tools section
- [ ] [Awesome Data Science](https://github.com/academic/awesome-datascience) — same
- [ ] [Awesome Free Software](https://github.com/Phantas0s/awesome-devops) — relevant sections
- [ ] [Awesome AI](https://github.com/owainlewis/awesome-artificial-intelligence)

### Q&A platforms (genuinely helpful answers → consistent backlink trickle)
- [ ] [Quora](https://www.quora.com) — answer 5 questions/week with a helpful answer that mentions getjob4u where appropriate. Search: "how to optimize resume for ATS", "free ATS scanner", "data science roadmap", "free ML courses with certificate"
- [ ] [Reddit comments](https://www.reddit.com) — same approach
- [ ] [Stack Overflow / Cross Validated](https://stats.stackexchange.com) — career-tag answers
- [ ] [Quora Spaces](https://www.quora.com/spaces) — join Data Science / AI Engineering spaces

### Guest posts / interview swaps (1 per month)
- [ ] Email AI/ML newsletter authors offering to write a guest piece on AI resume optimization. Targets: TLDR AI, Ben's Bites, The Batch, Import AI.
- [ ] Pitch yourself to AI/ML YouTube channels (Krish Naik, CodeBasics, Codebagel) for a tool review video.

### Educational / community backlinks
- [ ] Email career services at 10 engineering colleges in India offering free use of getjob4u for placement prep. Many will link from their resources page (`.edu` / `.ac.in` = high-value backlinks).
- [ ] Post in **CSU / IIT / NIT placement Slack/Discord/Telegram groups**.
- [ ] Share in 20+ relevant Discord servers (data science, ML, GenAI, job hunting).
- [ ] Add yourself to [GitHub Student Pack](https://education.github.com/pack) reviewer lists if applicable.

---

## ☐ Content strategy (highest long-term ROI)

Backlinks come naturally to content that genuinely helps. Write **one piece every 2 weeks**, and they will compound.

### Article ideas already half-written (steal these)
1. **"The 50+ Free AI Tools I'd Use to Build My Resume in 2026"** — repurpose `/free-ai-tools` content as an article on Medium/Dev.to/LinkedIn with a backlink to the page.
2. **"AI/ML Career Roadmap — Visual Flowchart for Data Scientists, ML Engineers, Data Analysts, and Gen AI Engineers"** — repurpose `/career-roadmap`.
3. **"Every Free AI/ML Course With a Real Certificate — Tested in 2026"** — repurpose `/free-courses`.
4. **"I Analyzed 1,000 AI/ML Resumes — Here Are the 7 Reasons Most Get Rejected"** — fictional/composite case study driving traffic to `/ats-scanner`.
5. **"100 Python Coding Questions Asked at FAANG (Free, With Solutions)"** — link to `/python-questions`.
6. **"Cold Email Templates That Got Me Three AI/ML Referrals"** — link to `/email-generator`.
7. **"The AI Tools List That Replaces $200/month of Subscriptions"** — viral title, links to `/free-ai-tools`.

### Distribute each article
- LinkedIn (long-form post)
- Dev.to + Hashnode + Medium (canonical = original)
- 2-3 relevant subreddits
- Hacker News (only if exceptional)
- Twitter/X thread (10 tweets)
- Newsletter (start your own free Substack — 10 minutes to set up)

---

## ☐ Track what works

In Google Search Console, monitor:
- **Performance → Search results** — clicks, impressions, average position. Track per page.
- **Coverage** — make sure every page is indexed (not "Discovered – currently not indexed").
- **Enhancements** — verify FAQ, HowTo, Breadcrumb, Logo, Sitelinks are all valid.

In Google Analytics (already installed as `G-EN17K7WRB1`), track:
- **Acquisition → Traffic acquisition → Session source/medium** — see which backlinks send traffic.
- Set up a **Custom event** for outbound clicks on `/free-ai-tools` (already wired via `data-gtag="ai_tool_click"` — you can promote it to a key event in GA4 admin).

---

## Quick wins you can run weekly (the boring ones that compound)

| Cadence | Action |
|---|---|
| **Daily**   | Answer 1 Quora / Reddit question with a helpful answer that links naturally to a getjob4u page. |
| **Weekly**  | Publish 1 long-form article on Dev.to / LinkedIn / Medium with backlink. |
| **Weekly**  | Submit to 2 new directories. |
| **Weekly**  | Reach out to 3 college career-services accounts. |
| **Monthly** | Audit Search Console for broken pages / 404s. |
| **Monthly** | Update `/free-ai-tools` and `/free-courses` JSON with any newly-discovered free tools — Google rewards freshness. |
| **Quarterly** | Re-run Rich Results Test on every page. |

---

**Last updated:** 2026-05-23
