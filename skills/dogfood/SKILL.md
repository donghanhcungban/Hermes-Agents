---
name: dogfood
description: "Exploratory QA of web apps: find bugs, evidence, reports."
version: 1.1.0
author: Teknium (teknium1), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [qa, testing, browser, web, dogfood]
    related_skills: []
---

# Dogfood: Systematic Web Application QA Testing

## Overview

This skill guides you through systematic exploratory QA testing of web applications using Hermes browser tools. You will navigate the application, interact with elements, capture evidence of issues, and produce a structured bug report.

## Prerequisites

- `mcp__browser_exec` must be available (Hermes browser tool that accepts Python code using pre-imported helpers)
- A target URL and testing scope from the user

## Inputs

The user provides:
1. **Target URL** — the entry point for testing
2. **Scope** — what areas/features to focus on (or "full site" for comprehensive testing)
3. **Output directory** (optional) — where to save screenshots and the report (default: `./dogfood-output`)

## Workflow

Follow this 5-phase systematic workflow:

### Phase 1: Plan

1. Create the output directory structure:
   ```
   {output_dir}/
   ├── screenshots/       # Evidence screenshots
   └── report.md          # Final report (generated in Phase 5)
   ```
2. Identify the testing scope based on user input.
3. Build a rough sitemap by planning which pages and features to test:
   - Landing/home page
   - Navigation links (header, footer, sidebar)
   - Key user flows (sign up, login, search, checkout, etc.)
   - Forms and interactive elements
   - Edge cases (empty states, error pages, 404s)

### Phase 2: Explore

For each page or feature in your plan:

1. **Navigate** to the page:
   ```python
   # Navigate to a page
   new_tab("https://example.com/page")   # first navigation
   # or for subsequent pages:
   goto_url("https://example.com/page")
   wait_for_load()
   ```

2. **Get a DOM/accessibility snapshot** to understand the page structure:
   ```python
   # Get page info (title, URL, basic structure)
   print(page_info())
   # For a full accessibility tree (filter before printing — it can be thousands of nodes):
   nodes = cdp('Accessibility.getFullAXTree')['nodes']
   interactive = [n for n in nodes if n.get('role', {}).get('value') in ('button','link','textbox','combobox','checkbox')]
   print(interactive[:30])
   ```

3. **Check the console** for JavaScript errors:
   ```python
   # Inject error collector and check for errors
   errors = js('window.__hermes_errors || []')
   # Or intercept going forward:
   js('window.__hermes_errors = []; window.addEventListener("error", e => window.__hermes_errors.push(e.message));')
   print(errors)
   ```
   Do this after every navigation and after every significant interaction. Silent JS errors are high-value findings.

4. **Take a screenshot** to visually assess the page:
   ```python
   path = capture_screenshot()
   print(path)
   ```
   Then analyze it with `mcp__vision_analyze(image_url=path, question="Describe the page layout, identify any visual issues, broken elements, or accessibility concerns")`.

5. **Test interactive elements** systematically:
   - Click by coordinates: `click_at_xy(x, y)` (get coords from `cdp('DOM.getBoxModel', backendNodeId=n)`)
   - Fill inputs: `fill_input("css-selector", "test input")`
   - Test keyboard navigation: `js('document.activeElement.dispatchEvent(new KeyboardEvent("keydown",{key:"Tab",bubbles:true}))')`
   - Scroll through content: `js('window.scrollBy(0, 600)')`
   - Test form validation with invalid inputs
   - Test empty submissions

6. **After each interaction**, check for:
   - Console errors: `js('window.__hermes_errors || []')`
   - Visual changes: `capture_screenshot()` then `mcp__vision_analyze(image_url=path, question="What changed after the interaction?")`
   - Expected vs actual behavior

### Phase 3: Collect Evidence

For every issue found:

1. **Take a screenshot** showing the issue:
   ```python
   path = capture_screenshot()
   print(path)  # save this path for the report
   ```
   Then analyze with `mcp__vision_analyze(image_url=path, question="Describe the issue visible on this page")`.

2. **Record the details**:
   - URL where the issue occurs
   - Steps to reproduce
   - Expected behavior
   - Actual behavior
   - Console errors (if any)
   - Screenshot path

3. **Classify the issue** using the issue taxonomy (see `references/issue-taxonomy.md`):
   - Severity: Critical / High / Medium / Low
   - Category: Functional / Visual / Accessibility / Console / UX / Content

### Phase 4: Categorize

1. Review all collected issues.
2. De-duplicate — merge issues that are the same bug manifesting in different places.
3. Assign final severity and category to each issue.
4. Sort by severity (Critical first, then High, Medium, Low).
5. Count issues by severity and category for the executive summary.

### Phase 5: Report

Generate the final report using the template at `templates/dogfood-report-template.md`.

The report must include:
1. **Executive summary** with total issue count, breakdown by severity, and testing scope
2. **Per-issue sections** with:
   - Issue number and title
   - Severity and category badges
   - URL where observed
   - Description of the issue
   - Steps to reproduce
   - Expected vs actual behavior
   - Screenshot references (use `MEDIA:<screenshot_path>` for inline images)
   - Console errors if relevant
3. **Summary table** of all issues
4. **Testing notes** — what was tested, what was not, any blockers

Save the report to `{output_dir}/report.md`.

## Tools Reference

| Tool | Purpose |
|------|---------|
| `new_tab(url)` | Open/navigate to a URL (first navigation in session) |
| `goto_url(url)` + `wait_for_load()` | Navigate to a URL on subsequent pages |
| `page_info()` | Summary of current page state (title, URL, structure) |
| `cdp('Accessibility.getFullAXTree')['nodes']` | Full DOM/accessibility tree for element discovery |
| `cdp('DOM.getBoxModel', backendNodeId=n)` | Get click coordinates for a node by backendNodeId |
| `click_at_xy(x, y)` | Click at viewport coordinates |
| `fill_input(selector, text)` | Type into an input field by CSS selector |
| `js(expr)` | Evaluate JavaScript — navigate, scroll, check errors, fire events |
| `capture_screenshot()` | Take a screenshot; returns a file path |
| `mcp__vision_analyze(image_url=path, question=...)` | Analyze a screenshot for visual issues, layout, bugs |

All helpers except `mcp__vision_analyze` are used **inside a `mcp__browser_exec` call** as pre-imported Python functions.

## Tips

- **Always check for JS errors after navigating and after significant interactions.** Inject `window.__hermes_errors` once, then poll it — silent JS errors are among the most valuable findings.
- **Use `mcp__vision_analyze` with a specific question** about what you're looking for to get targeted analysis rather than generic descriptions.
- **Test with both valid and invalid inputs** — form validation bugs are common.
- **Scroll through long pages** — content below the fold may have rendering issues: `js('window.scrollBy(0, 800)')`.
- **Test navigation flows** — click through multi-step processes end-to-end.
- **Check responsive behavior** by noting any layout issues visible in screenshots.
- **Don't forget edge cases**: empty states, very long text, special characters, rapid clicking.
- When reporting screenshots to the user, include `MEDIA:<screenshot_path>` so they can see the evidence inline.
- Batch independent `mcp__browser_exec` calls when you need to check multiple unrelated things at once.

## Verification

After running a dogfood session, confirm the following before closing:

1. **All phases completed** — Plan → Explore → Evidence → Categorize → Report
2. **Every finding has evidence** — each issue in the report has a real `screenshot_path` captured by `capture_screenshot()`, not a fabricated path
3. **Console errors checked** — JS errors were polled after every navigation and significant interaction
4. **Report saved** — `{output_dir}/report.md` exists and is readable; verify with `read_file`
5. **No invented data** — every severity, URL, and reproduction step in the report corresponds to something actually observed during the session
6. **Screenshots referenced correctly** — `MEDIA:<path>` links in the report point to files that actually exist on disk (verify with `search_files`)
