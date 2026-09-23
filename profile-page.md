# SVG Profile Page Documentation

This document describes the architecture, visual system, data model, and maintenance workflow for the generated SVG profile page in [`frostyfoxie/frostyfoxie`](https://github.com/frostyfoxie/frostyfoxie).

> The repository's `README.md` is intentionally unchanged. This documentation lives under `docs/` so the profile implementation and its usage notes remain separate from the profile presentation itself.

## Overview

The profile is a self-contained, animated SVG experience generated from a reusable template. It combines personal information, GitHub activity, contribution history, education, skills, technology icons, and contact buttons into a single visual profile card.

The generated assets are:

- [`profile.svg`](../profile.svg) — the primary profile canvas.
- [`btn_github.svg`](../btn_github.svg) — GitHub contact button.
- [`btn_instagram.svg`](../btn_instagram.svg) — Instagram contact button.
- [`btn_email.svg`](../btn_email.svg) — email contact button.

The source assets are:

- [`template.svg`](../template.svg) — SVG layout, styling, animation, and replacement markers.
- [`config.json`](../config.json) — editable profile content.
- [`scripts/update_svg.py`](../scripts/update_svg.py) — data collection and SVG generation logic.
- [`icons/`](../icons/) — local technology and contact icons.
- [`.github/workflows/update-profile.yml`](../.github/workflows/update-profile.yml) — automated regeneration workflow.

## Visual design

The page uses a light, editorial interface with a blue-and-red identity badge and translucent glass-style cards.

### Canvas and layout

- Viewbox: `860 × 948`.
- Background: soft slate (`#f8fafc`).
- Main content is arranged into four areas:
  1. **Behind the Code** introduction and animated identity badge.
  2. **Contribution Graph & Commit Activity** with a GitHub-style activity grid.
  3. **Education** and all-time GitHub statistics.
  4. **Skills** and a keycap-style technology stack.

### Typography

The template defines three font families with system fallbacks:

- `Space Grotesk` for headings and identity labels.
- `Plus Jakarta Sans` for body copy and interface text.
- `JetBrains Mono` for the developer ID label.

Because the SVG may be rendered in environments without web-font loading, each family includes a system fallback.

### Effects and animation

The visual system is built from native SVG and CSS features:

- Gaussian blur creates ambient background orbs.
- Drop shadows provide depth for glass cards and the identity badge.
- Animated gradient stops add subtle motion to the blue lanyard.
- The identity badge gently sways around its lanyard anchor.
- Background glow orbs float and change opacity over time.
- The contribution grid animates an arcade-style purple snake across recent activity.
- Contact buttons include hover styling when the SVG renderer supports interaction.

## Data model

Editable content is kept in [`config.json`](../config.json). The main sections are:

| Section | Purpose |
| --- | --- |
| `contact` | Instagram handle and email label used by the generated contact buttons. |
| `behind_the_code` | Introductory subheading and description paragraphs. |
| `education` | Timeline entries containing `year`, `title`, and `institution`. |
| `skills` | Skill labels rendered as pills. The generator currently renders up to six. |
| `tech_stack` | Icon names resolved from `icons/` or Simple Icons fallback data. The generator currently renders up to fourteen. |

Keep values short enough for the available layout. Long descriptions are wrapped by the generator, while long skill and education labels may require template adjustments for ideal visual results.

## Generation pipeline

Run the generator from the repository root:

```bash
GH_USERNAME=frostyfoxie GITHUB_TOKEN="$GITHUB_TOKEN" python scripts/update_svg.py
```

The script performs the following steps:

1. Loads `config.json` when present.
2. Reads the GitHub username and token from environment variables.
3. Fetches the account profile and avatar from the GitHub REST API.
4. Queries GitHub GraphQL for all-time commit totals and the most recent contribution calendar.
5. Counts owned repositories and their stars through the GitHub REST API.
6. Builds the animated contribution grid and arcade snake.
7. Converts local icons to base64 data URIs; if an icon is unavailable locally, it attempts a Simple Icons CDN lookup.
8. Replaces the markers in `template.svg`.
9. Writes `profile.svg` and the three contact-button SVGs.

### Generated template markers

The primary template receives dynamic values through markers such as:

- `{{NAME}}`, `{{USERNAME}}`, and `{{AVATAR_DATA_URI}}`
- `{{COMMITS}}`, `{{REPOS}}`, `{{ACTIVE_DAYS}}`, and `{{STARS}}`
- `{{BEHIND_THE_CODE_SUBHEADING}}` and `{{BEHIND_THE_CODE_DESCRIPTION}}`
- `{{EDUCATION_ITEMS}}`, `{{SKILLS_ITEMS}}`, and `{{TECH_STACK_ITEMS}}`
- `{{CONTRIBUTION_SNAKE_SECTION}}`
- `{{ICON_GITHUB}}` and `{{ICON_GITHUB_RED}}`

These markers should remain in `template.svg`; they are replaced during generation and are not intended to appear in the final profile.

## Automated updates

The `Update Profile SVG` workflow runs on:

- A scheduled interval configured in [`.github/workflows/update-profile.yml`](../.github/workflows/update-profile.yml).
- Pushes to `main` that change `template.svg`, `config.json`, `icons/**`, or `scripts/**`.
- Manual dispatch from the GitHub Actions tab.

The workflow uses Python 3.11, executes `scripts/update_svg.py`, and commits generated changes to `profile.svg` and the three button assets.

### Required permissions and secrets

The workflow needs permission to write repository contents so it can commit generated files. The generator requires:

- `GH_USERNAME` — supplied by the workflow as the repository owner.
- `GITHUB_TOKEN` — supplied from `PAT_TOKEN` when configured, otherwise the default `GITHUB_TOKEN`.

Use a personal access token only when access to private repositories or additional contribution data is required. Store tokens in GitHub Actions secrets; never place them in `config.json`, SVG files, committed scripts, or documentation.

## Customization guide

### Change profile content

Edit [`config.json`](../config.json), then run the generator locally or trigger the workflow manually. Changes to profile copy, education, skills, or the technology list do not require editing the SVG layout.

### Add or replace icons

Place an icon in [`icons/`](../icons/) using the same lowercase name referenced in `tech_stack`. Supported local formats include SVG, PNG, WebP, JPG, and JPEG. Local icons are preferred over the CDN fallback, which makes committed assets more predictable and keeps generated SVGs self-contained.

### Change the layout or appearance

Edit [`template.svg`](../template.svg) to modify:

- Panel positions and dimensions.
- Colors, gradients, shadows, and typography.
- Animation timing and motion paths.
- The number or arrangement of statistics.
- The visual structure of the profile card.

Preserve the existing replacement markers unless the corresponding logic in `scripts/update_svg.py` is updated at the same time.

### Change the generated buttons

The three contact buttons are created by `generate_button_svg()` in [`scripts/update_svg.py`](../scripts/update_svg.py). Update that function to change their dimensions, typography, hover treatment, or layout.

## Validation checklist

Before committing a design or generator change:

1. Run the generator with a valid GitHub token.
2. Confirm that `profile.svg` and all three button SVGs are regenerated.
3. Open the SVGs in a browser and verify animations, text wrapping, links, and icon rendering.
4. Check that no unresolved `{{...}}` markers remain in generated files.
5. Confirm that secrets, tokens, and private API responses were not written to the repository.
6. Review the generated diff for unintended formatting or large embedded assets.
7. Trigger the workflow manually when validating GitHub Actions behavior.

## Troubleshooting

### `Missing GH_USERNAME or GITHUB_TOKEN environment variables.`

Export both variables before running the script. In Actions, verify that the workflow passes `GH_USERNAME` and that the selected token secret is available to the workflow.

### A technology icon is blank

Check that the name in `config.json` matches a file in `icons/`. If no local file exists, confirm that the corresponding Simple Icons name can be resolved and that outbound network access is available.

### GitHub statistics are incomplete

Contribution and repository data depend on GitHub API responses and token permissions. Check the workflow logs, token scopes, rate limits, and whether the account or repositories are private.

### Text overlaps or is clipped

Shorten the affected value in `config.json` first. If the content must remain long, adjust the relevant coordinates, widths, font sizes, or wrapping behavior in `template.svg` and `scripts/update_svg.py`.

## Maintenance notes

- `profile.svg` and the button SVGs are generated artifacts; make source changes in `config.json`, `template.svg`, `icons/`, or `scripts/update_svg.py`.
- Keep the generated output committed so profile consumers can load the SVGs without running Python.
- Treat embedded avatar and icon data as build output and regenerate it when source assets or account data change.
- Keep this documentation in `docs/`; do not move it into `README.md` unless the repository’s documentation strategy changes.
