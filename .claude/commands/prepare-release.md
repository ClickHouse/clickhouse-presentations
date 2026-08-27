Prepare the ClickHouse release presentation for the upcoming version.

This is the counterpart of `/publish-release`: it creates and iterates on the deck before the
release call. Do not do the publish steps (preview.jpg, video embed, root index card) — those
happen at publish time.

## 1. Determine the version and set up

- Previous deck: `ls -d *-release-*/ | sort -t- -k3 -V | tail -1`. The new version is the next
  minor (e.g. 26.8 after 26.7); the directory is `{year}-release-{version}/`.
- Create the directory, copy `pictures/back*.jpg`, `wing.jpg`, `openhouse_tour.jpg`, and
  `LICENSE` from the previous deck as placeholders. They are personal photos, unique per
  release — flag them for replacement; the author swaps them in later.
- Copy the previous `index.html` as the structural template: same `<head>`, styles
  (`.hilite`, `.zoomable`), shower scripts, footer. Keep the YouTube iframe at the end
  **commented out** with a `VIDEO_ID` placeholder.
- Header date and the agenda slide date = the release call date (a Thursday, usually the
  4th-ish of the month). Mark the cover "LTS" when the version is x.8.
- Work on a branch `add-release-{version}`, push early and often. The author edits the same
  branch concurrently: **git pull before every editing session**, rebase on conflicts, and when
  a conflict touches the author's wording, keep his side and re-apply only your mechanical
  change. If he says a slide is final, never touch its markup again (supplying image files it
  references is fine).

## 2. The changelog is the source of facts

- The draft lives on branch `auto/changelog-{version}` of ClickHouse/ClickHouse; close to the
  release day the branch is deleted and the section is merged into master's `CHANGELOG.md`,
  still titled "FIXME (in progress)" with TODO entries — take it from master then, and expect
  it to keep changing until the call.
- Stats slide counts: "new features" = New Feature + Experimental Feature entries + Backward
  Incompatible entries that are actually new capabilities; "performance optimizations" =
  Performance Improvement count; "bug fixes" = Bug Fix count. Record the counting in a hidden
  comment after the stats slide and **recount from the final changelog near the call**.
  Month-themed emojis on the stats slide — never reuse the previous release's.
- Sweep featured PRs for continuation markers (supersedes / based on / continues / revives /
  "Author: [") and credit the original engineer first, regardless of the fate of their
  implementation. Verify the earlier PR implements the *same* change, not a similar-sounding one.

## 3. The hidden table-of-contents comment is the plan

Draft a TOC comment (after the stats slide) grouping the highlights into sections. **The author
will rewrite this list** — after he does, restructure the deck to match it exactly: his item
names, his order, his cuts. Keep his TOC text verbatim. Anything he removed stays removed;
anything he added gets a slide, researched and tested like the rest.

## 4. Test every feature; demo comments are mandatory

- Binaries: master build `curl -L https://builds.clickhouse.com/master/{arch}/clickhouse`
  (contains everything in the upcoming release), plus the previous stable from GitHub release
  assets (`clickhouse-common-static-{ver}-{arch}.tgz`) for A/B comparisons.
- Run a real server from a minimal `config.xml` (query_log section, a local two-shard cluster,
  extra ports, feature gates like `http_allow_path_requests`) — CLI `--` overrides cannot
  create config *sections*. `clickhouse-local` silently loads `config.xml` from the current
  directory — never run it from the server's config directory.
- Every feature slide carries a hidden `<!-- Demo: ... -->` comment with the exact tested
  commands and observed outputs. If something could not be run live (no cloud account, no
  cluster), the slide shows plausible syntax and the comment says so honestly.
- Verify slide claims against the binary, not the changelog prose: check setting names,
  defaults, semantics (`system.settings`, `system.merge_tree_settings`, `system.functions`
  descriptions, `system.statements`). Changelog wording can be subtly wrong — e.g. thresholds
  that are per-block rather than per-table, or argument orders that differ from the docstring.

## 5. Benchmarks

- The machine is shared: interleave old/new runs pinned with `taskset`, repeat 3-5x, take the
  minimum; single-threaded micro-benchmarks are the most stable. If local numbers stay noisy
  or the environment can't show the effect (page cache, slow route to S3), take numbers from
  the PR / CI perf tests and mark clearly, or present the queries with your numbers and tell
  the author they need re-testing — he will substitute proper ones.
- Match the benchmark shape to the optimization (e.g. an optimization for runs of equal values
  needs sorted input; per-partition parallelism needs more partitions than threads) — a null
  result usually means the wrong shape, not a broken feature.
- Numbers formatting on slides: `Example: <description>:` in plain text (never a green bold
  "Measured"), then `26.7: <red>X</red> sec.` / `26.8: <green>Y</green> sec.` lines. Keep
  numbers only when dramatic; a marginal 1.15x is better dropped or replaced with one plain
  sentence about when the feature helps.

## 6. Slide style (learned from the author's edits)

- Titles say what the thing **is** in plain words: "An aggregate function to merge JSONs",
  "Array as an array subscript", "Column statistics, enabled on INSERT" — not codenames.
- Short slides win. When in doubt, cut: fewer bullets, one strong number, one idea per slide.
- Historical and architectural context is welcome: where the technique came from, when
  ClickHouse first had it, which other systems adopted it since.
- Prefer a live "Demo." marker (sometimes `<p style="float: right;">Demo.</p>`) over baked
  screenshots for things the author can show interactively — put the demo query on the real
  `hits` table in the hidden comment.
- Config examples in **YAML**, never XML: a gray `$ cat config.d/name.yaml` line, blank line,
  then the keys with the new setting names in green bold.
- Parquet/object-storage examples use ClickBench: `s3('s3://clickhouse-public-datasets/
  hits_compatible/hits.parquet')` (the s3:// bucket URL, not the datasets.clickhouse.com CDN —
  only the bucket takes the ranged-read path). Web-visible demos use real datasets on
  play.clickhouse.com (hackernews, github_events, hits).
- Credits: gray footer `Developer: Name.` / `Developers: A, B.`, from the changelog names, with
  scopes when contributions differ — e.g. "Auxten Wang (chDB), Alexey Milovidov (parser)".
- Emojis: 🧪 after titles of experimental features.

## 7. Screenshots and animations

- Playwright + chromium. Always `http://127.0.0.1:...`, never `localhost` (chromium resolves
  to ::1 where another server may listen). Dark theme for UI screenshots. In the Play UI, type
  queries with `page.keyboard.type()` so the WASM highlighter runs.
- Screenshot slides are full-bleed `<section>` backgrounds (`center / contain no-repeat`,
  letterbox color matching the site) with a full-slide `<a target="_blank">` pointing at the
  **exact URL state** (Play encodes the query in the base64 hash and sort/filter/color state in
  URL params — drive the UI, then copy `page.url`; verify a fresh open restores it).
  Compose collages (main view + pager/detail strip) with PIL when one screenshot can't show it.
- Inline images use `class="zoomable"` with the standard onclick toggle (click = full-slide,
  second click = collapse).
- Animated PNG is a house specialty: FORMAT PNG with a `t` column (Julia set; a year of ADS-B
  traffic per week over an airport at 10 fps via `output_format_image_time_divisor_seconds`).
  Screenshot-size guidance: 1280x960 usually reads best — 1px traces dim when downscaled from
  higher resolutions. An HTML overlay can sync to the APNG by restarting it (re-set img.src)
  and running a wall-clock timer; re-arm on slide activation and visibilitychange.

## 8. Closing slides

- Meetups: scrape https://clickhouse.com/company/events; list ~12 events *after* the call
  date with country flag emojis, on the wing.jpg (placeholder) background.
- Open House / roadshow slide when a tour is running: openhouse_tour.jpg + dates line.
- Reading Corner: recent posts from https://clickhouse.com/blog (the author names the must-have
  posts in the TOC comment); one QR code to the flagship post (python qrcode, box_size=8,
  border=2, rendered with `image-rendering: pixelated; width: 20%`).

## 9. Verification

- Overflow check with Playwright in list mode: every slide child's bounding box must fit the
  slide box (a few px of tolerance). Fix by tightening `margin-top`s, shrinking code font one
  step, or cutting a line — then re-check. Screenshot dense slides at `?full#N` and *look* at
  them; the checker misses clipped footers under floated images.
- The search index (search-index.js) is rebuilt by CI — never edit it.
- Do not create preview.jpg, do not uncomment the video, do not touch the root index.html —
  that is `/publish-release`, run after the call.
