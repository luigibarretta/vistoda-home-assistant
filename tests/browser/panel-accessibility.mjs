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
        if (visible && element.matches("select") && element.selectedOptions[0] &&
            element.getAttribute("aria-hidden") !== "true") {
          // The chosen option must fit: a capped width once cut "Vistoda theme".
          const style = getComputedStyle(element);
          const probe = Object.assign(document.createElement("span"), {
            textContent: element.selectedOptions[0].textContent });
          probe.style.cssText = `position:absolute;visibility:hidden;white-space:nowrap;font:${style.font}`;
          document.body.append(probe);
          const needed = probe.offsetWidth + parseFloat(style.paddingLeft) + parseFloat(style.paddingRight) + 12;
          probe.remove();
          if (element.clientWidth < needed) failures.push(`${path}: truncated select#${element.id}`);
        }
        if (element.shadowRoot) visit(element.shadowRoot, `${path}/${element.localName}`);
      }
    };
    visit(document, "document"); return failures;
  });
  assert.deepEqual(failures, [], `${label}: semantic accessibility`);
}

