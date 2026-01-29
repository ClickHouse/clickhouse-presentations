Publish the latest ClickHouse release presentation.

Follow these steps:

## 1. Find the latest release presentation directory

List all directories matching the pattern `*-release-*/` and find the one with the highest version number:

```bash
ls -d *-release-*/ | sort -t- -k3 -V | tail -1
```

The directory name format is `{year}-release-{version}/` (e.g., `2026-release-26.1/`).

Extract the version number from the directory name (e.g., "26.1" from "2026-release-26.1").

## 2. Generate preview.jpg

Use Playwright to screenshot the first slide of the presentation at exactly 1200x630 pixels:

```bash
npx playwright screenshot --viewport-size="1200,630" "file://$(pwd)/{presentation_dir}/index.html?full#cover" {presentation_dir}/pictures/preview.jpg
```

Read the generated preview.jpg to verify it shows the correct release version text.

## 3. Find the YouTube video

Search the web for "ClickHouse Release {version} site:youtube.com" to find the release call video.

Extract the video ID from the YouTube URL (the part after `v=`).

## 4. Update the presentation's index.html with YouTube embed

In the presentation's `index.html`, find the YouTube iframe section near the end of the file. It may be commented out with `<!-- -->`.

- If commented, uncomment it
- Update the video ID in the embed URL to: `https://www.youtube.com/embed/{video_id}`

The section should look like:
```html
<section class="slide" style="background: black; padding: 0;">
<iframe style="width: 100%; height: 100%; position: absolute; top: 0; left: 0;" src="https://www.youtube.com/embed/{video_id}" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
</section>
```

## 5. Update root index.html

Check if the presentation is already in the root `index.html`. If not, add the new presentation entry at the TOP of the grid, right after `<div class="grid" id="grid">`:

```html
<a href="{presentation_dir}/" class="card" data-title="clickhouse: release {version} call">
    <img src="{presentation_dir}/pictures/preview.jpg" alt="ClickHouse: Release {version} Call" loading="lazy">
    <div class="card-title">ClickHouse: Release {version} Call</div>
</a>
```

## 6. Ask about committing

Ask the user if they want to commit and push the changes.
