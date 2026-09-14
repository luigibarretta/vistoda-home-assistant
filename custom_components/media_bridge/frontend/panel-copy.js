// Scoped catalogs for advanced UI. Only authored copy is eligible for lookup.
import { panelLanguage } from "./panel-localize.js";
import { COMMON_COPY } from "./panel-copy-common.js";
import { RING_COPY } from "./panel-copy-ring.js";
import { BLINK_COPY } from "./panel-copy-blink.js";
import { STORAGE_COPY } from "./panel-copy-storage.js";

export const ADVANCED_COPY = Object.freeze({ ...COMMON_COPY, ...RING_COPY, ...BLINK_COPY, ...STORAGE_COPY });
export function copyLocale(context) {
  return context?._hass || context?.hass || context?.host?._hass || context?.host?.hass || context;
}
export function copy(context, source, values = {}) {
  const key = source.replace(/\s+/g, " ").trim();
  const message = panelLanguage(copyLocale(context)) === "it" ? key : ADVANCED_COPY[key] || key;
  return message.replace(/\{(p\d+)\}/g, (_, name) => String(values[name] ?? `{${name}}`));
}

// Markers are authored in static templates. No matching arbitrary DOM text,
// mutation observers, device names, input values or upstream error rewriting.
const rootLanguages = new WeakMap();
export function localizeCopy(root, context) {
  if (!root?.querySelectorAll) return;
  const language = panelLanguage(copyLocale(context));
  const changed = rootLanguages.get(root) !== language;
  rootLanguages.set(root, language);
  root.querySelectorAll("[data-copy]").forEach((node) => {
    const text = copy(context, node.getAttribute("data-copy"));
    // Replacing unchanged native option text can dismiss a mobile picker
    // during background HA state updates.
    if (node.textContent !== text) node.textContent = text;
  });
  for (const attribute of ["aria-label", "title", "placeholder", "data-tooltip", "alt"]) {
    root.querySelectorAll(`[data-copy-${attribute}]`).forEach((node) => {
      const text = copy(context, node.getAttribute(`data-copy-${attribute}`));
      if (node.getAttribute(attribute) !== text) node.setAttribute(attribute, text);
    });
  }
  return changed;
}

export function copyHtml(context, html) {
  const template = document.createElement("template");
  template.innerHTML = html;
  localizeCopy(template.content, context);
  return template.innerHTML;
}
