# Visual Content Direction

## Scope

Create content-matched Xiaohongshu covers and carousel plans. Do not turn every copy request into a visual production project, and do not generate or publish image files unless the user explicitly requests them.

## Adaptive Brief

Use information already present in the conversation. Check these decisions before committing to a visual direction:

- communication objective and desired reader action;
- target reader and their current problem;
- single strongest claim or takeaway;
- available original or licensed assets;
- desired and prohibited visual qualities;
- requested deliverable: cover, page plan, prompts, review, or image files.

If missing information would produce materially different results, ask one grouped clarification. Otherwise state assumptions and continue. Do not force a fixed ten-question interview.

For full carousel or rendered-image requests, behave like a visual director:

- First produce or preserve a brief analysis: objective, audience, core claim, reader emotion, content density, style report, unsuitable style, and the few clarifying questions that materially affect the result.
- Ask a compact grouped clarification only when the missing answers would produce a different visual system. Do not mechanically ask ten questions when the user has already provided enough context.
- If the user explicitly says to proceed directly, state assumptions and continue.

## Style Selection

Choose style after classifying the content and information density. Useful starting families include:

- editorial clarity for opinions and explainers;
- documentary or lifestyle for personal, travel, food, and experience-led topics;
- structured cards for tutorials, checklists, and tool collections;
- product-first composition for product or software demonstrations;
- data and diagram language for research, comparisons, and systems;
- expressive illustration for stories and emotional concepts.

Explain why the chosen style supports the content and identify at least one unsuitable direction. Avoid vague labels such as “高级” without concrete layout, color, type, and material choices. Do not default to dark backgrounds, neon green, glass effects, or technology imagery.

## Visual Master

For a multi-page series, define one reusable master before page details:

- canvas: `1080x1440px`, strict 3:4 portrait;
- safe margins and mobile text-safe area;
- grid, spacing, corner radius, line, icon, and page-number rules;
- background, text, secondary, and accent colors;
- Chinese title, body, and annotation type hierarchy;
- repeated components and asset treatment;
- what may change per page and what must stay fixed.

Repeat the canvas and master constraints in every image prompt. Keep every page readable on a phone and assign it one primary communication task.

The persistent draft should include a `visual_master` object with canvas, safe margins, grid, palette, typography, components, consistent rules, and variable rules. Every page prompt should repeat the 3:4 canvas, safe margins, unified style, Chinese text-safe area, and mobile readability requirement.

## Page Rhythm

Build only the number of pages the content can support. A typical series may move through cover, problem, context, key idea, method, example, summary, and interaction, but do not mechanically fill eight pages. Use contrast between pages while preserving the visual master.

Each page plan must include role, title, concise copy, layout, visual focus, image prompt, and negative prompt. Never fabricate statistics, screenshots, quotes, product results, or first-hand scenes to fill a page.

## Image Delivery

When the user explicitly requests rendered images:

1. Finish the visual master and page plan.
2. Generate one representative cover or key page.
3. Verify that a real asset exists and check its dimensions and 3:4 ratio.
4. Ask for confirmation of style, composition, palette, and information density.
5. After confirmation, generate the remaining series with the locked master.

If the image model cannot render reliable Chinese, generate an appropriate text-safe visual base and add real Chinese with a deterministic layout tool. Do not deliver gibberish, black placeholder bars, or unreadable generated text as a finished image.

Track image-production status explicitly. A planning draft may contain `production_tasks` such as:

- `plan`: completed after the draft, visual direction, master, and page plan exist.
- `confirm-image`: awaiting_confirmation before generating the first cover or key-page image.
- `batch-images`: ready_for_image_generation only after the representative image is approved.

These task records are planning state only. They must not trigger login, upload, publish, or platform automation.

## Review

Check mobile readability, one-task-per-page focus, hierarchy, contrast, consistent margins, consistent type and color tokens, asset rights, factual claims, 3:4 dimensions, and whether the series feels like social content rather than slide screenshots. Keep image prompts as reproducibility records, not as substitutes for requested image files.
