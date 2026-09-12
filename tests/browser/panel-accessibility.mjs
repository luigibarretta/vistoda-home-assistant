import assert from "node:assert/strict";

export async function checkSemantics(page, label) {
  const failures = await page.evaluate(() => {
    const failures = [];
    const visit = (root, path) => {
      const ids = new Set();
      for (const element of root.querySelectorAll("*")) {
        if (element.id) {
          if (ids.has(element.id)) failures.push(`${path}: duplicate id ${element.id}`);
          ids.add(element.id);
        }
        const visible = element.checkVisibility();
        if (visible && element.matches("button, a, input, select, textarea")) {
          const labelledBy = element.getAttribute("aria-labelledby");
          const referenced = labelledBy?.split(/\s+/)
            .map((id) => root.getElementById?.(id)?.textContent || "").join(" ");
          const labelText = element.closest("label")?.textContent || "";
          const name = element.getAttribute("aria-label") || referenced || labelText ||
            element.textContent || element.title;
          if (!name?.trim()) failures.push(`${path}: unnamed ${element.localName}#${element.id}`);
        }
        if (visible && element.matches("img") && !element.hasAttribute("alt")) {
          failures.push(`${path}: image without alt#${element.id}`);
        }
        if (visible && element.matches("dialog, [role='dialog']") &&
            !element.hasAttribute("aria-label") && !element.hasAttribute("aria-labelledby")) {
          failures.push(`${path}: unnamed dialog#${element.id}`);
        }
        if (element.tabIndex > 0) failures.push(`${path}: positive tabindex#${element.id}`);
        if (element.shadowRoot) visit(element.shadowRoot, `${path}/${element.localName}`);
      }
    };
    visit(document, "document"); return failures;
  });
  assert.deepEqual(failures, [], `${label}: semantic accessibility`);
}

