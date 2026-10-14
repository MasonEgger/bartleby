---
title: "Check Accessibility Before You Publish"
description: "Run bartleby lint, read each accessibility finding, and fix the page until it reports no issues."
date: 2026-10-14
audience: existing-user
tags:
  - accessibility
  - cli
authors:
  - mason
---

The bundled themes and the HTML the Markdown pipeline renders pass an axe-core audit, so what is left to get wrong is in the pages you write: an image with no alt text, a heading that jumps two levels, a link that says "here".
`bartleby lint` checks for those on every published page, prints the source line and a fix for each finding, and exits 1 when a finding is an error.
This guide runs it against a page that trips nine of the rules and fixes them one at a time.

<!-- more -->

## Step 1: Run Lint

Run the command from the directory that holds `bartleby.yml`.
It renders every published page the way `bartleby build` does, without writing `site/`, so a finding points at the HTML a reader would get.

```
bartleby lint
```

A clean site prints one line:

```
lint: no issues
```

The page below, saved as `content/release-notes.md` and listed under `nav`, is not clean.

```markdown
---
title: Release Notes
description: What changed in the 2.0 release.
---

<img src="dashboard.png">

![screenshot](settings.png)

**Highlights**

- Faster builds
- A new theme

#### Upgrading

Read [here](/docs/upgrade/) before you upgrade, or see
<https://example.com/docs/release-notes/2.0/migration-guide/>.

<table>
<tr><td>Python</td><td>3.14</td></tr>
<tr><td>uv</td><td>0.9</td></tr>
</table>

<iframe src="https://www.openstreetmap.org/export/embed.html?bbox=-97.8,30.2,-97.6,30.4"></iframe>

## Thanks

<p id="credits">To every contributor.</p>
<p id="credits">To every reader.</p>
```

Lint reports nine findings on it:

```
error [image-missing-alt] release-notes.md:6: <img src='dashboard.png'> has no alt attribute (fix: write alt text that says what the image shows, or alt="" for a decorative image)
warning [image-alt-is-filename] release-notes.md:8: <img src='settings.png'> has alt text 'screenshot', which does not describe it (fix: describe what the image shows in the alt text, as a reader who cannot see it needs)
warning [emphasis-as-heading] release-notes.md:10: paragraph 'Highlights' is only bold or italic text before a ul (fix: use a heading (## Text) instead of bold text to title a section)
warning [heading-level-skip] release-notes.md:15: <h4> 'Upgrading' follows an h1, skipping h2 (fix: use the next heading level down; a page body starts at ## because the title is the h1)
warning [link-generic-text] release-notes.md:17: <a href='/docs/upgrade/'> reads only 'here' (fix: make the link text name its target, such as [the configuration reference](...))
warning [link-raw-url-text] release-notes.md:18: <a href='https://example.com/docs/release-notes/2.0/migration-guide/'> reads as the URL 'https://example.com/docs/release-notes/2.0/migration-guide/' (fix: give the link a name: [Name](https://...) instead of the bare URL)
warning [table-missing-header] release-notes.md:20: <table> whose first row is 'Python | 3.14' has no header row (fix: give the table a header row; in Markdown, the first row is the header)
error [iframe-missing-title] release-notes.md:25: <iframe src='https://www.openstreetmap.org/export/embed.html?bbox=-97.8,30.2,-97.6,30.4'> has no title (fix: add title="..." saying what the frame shows, such as the video or map name)
error [duplicate-id] release-notes.md:29: id 'credits' is used 2 times (<p>, <p>) (fix: rename one of the ids; for repeated headings, change one heading's text)
3 error(s), 6 warning(s), 0 info
```

## Step 2: Read a Finding

Every line has the same shape:

```
<severity> [<rule>] <file>:<line>: <message> (fix: <hint>)
```

The severity is `error` or `warning`.
An error fails the command; a warning prints and the command still exits 0.
The rule is a stable id you can pass to `--rules` or `--skip`.
The line counts from the top of the Markdown file, front matter included, so `release-notes.md:6` is the `<img>` line.
The message names the element, and the fix says what to change.

With `--output json`, each finding is an object with `severity`, `rule`, `file`, `line`, `message`, and `hint` keys, which is the shape to read from a script or an agent.

## Step 3: Fix Each Finding

Work down the list.
Each heading below is one rule from the output above, with the change that clears it.

### image-missing-alt

A reader who cannot see the image hears its alt text, so write what the image shows.
If the image is decoration (a divider, a flourish), write `alt=""` and lint passes it as decorative.

```html
<img src="dashboard.png" alt="The dashboard after the upgrade, with the build time at the top">
```

### image-alt-is-filename

`screenshot`, `image`, `photo`, `picture`, and a file name are not descriptions.
Say what is in the picture.

```markdown
![The settings page, with the new theme picker open](settings.png)
```

### emphasis-as-heading

A bold line before a list looks like a heading but is a paragraph, so it is missing from the table of contents and from a screen reader's heading list.
Make it one.

```markdown
## Highlights
```

### heading-level-skip

The theme renders the page title as the `h1`, so a body starts at `##`.
`#### Upgrading` after the title skips two levels; `## Upgrading` is the next level down.

### link-generic-text

"Here" says nothing when a screen reader lists the links on a page.
Name the target.

```markdown
Read [the upgrade guide](/docs/upgrade/) before you upgrade
```

### link-raw-url-text

A bare URL longer than 40 characters is read out one character at a time.
Give it a name.

```markdown
[the 2.0 migration guide](https://example.com/docs/release-notes/2.0/migration-guide/)
```

### table-missing-header

A table without a header row gives a screen reader no column names to announce.
In Markdown the first row is the header, so write the table in Markdown.

```markdown
| Tool | Version |
| ---- | ------- |
| Python | 3.14 |
| uv | 0.9 |
```

### iframe-missing-title

The title is the only name a screen reader has for an embedded frame.
The pipeline adds one to markwright's own `[youtube ...]` embed; raw HTML needs it written in.

```html
<iframe title="Map of the Austin office" src="https://www.openstreetmap.org/export/embed.html?bbox=-97.8,30.2,-97.6,30.4"></iframe>
```

### duplicate-id

An anchor reaches only the first element with its id.
Rename one.
When two headings share an anchor, the message names the heading text that repeats; change one heading's wording.

```html
<p id="credits-contributors">To every contributor.</p>
<p id="credits-readers">To every reader.</p>
```

### The Rules This Page Did Not Trip

`heading-empty` reports a heading with no text, and `link-empty` reports a link with no text, no `aria-label`, and no image with alt text inside it; both are errors.
`language-invalid` checks `site.language` in `bartleby.yml` once per run and reports it against the config file; a tag such as `en`, `de-AT`, or `pt-BR` passes.
Run `bartleby lint --list-rules` to print every rule with its severity and fix, or add `--output json` to read the table from a script.

## Step 4: Run Lint Again

With every change above applied, the page is clean:

```
bartleby lint
```

```
lint: no issues
```

To check one rule while you work, or to leave one out, name it:

```
bartleby lint --rules heading-level-skip,emphasis-as-heading
bartleby lint --skip orphaned-page
```

The [CLI reference](../../reference/pages/cli.md#bartleby-lint) lists every flag and the full rule table.
