import assert from "node:assert/strict";

export async function checkAuthoredCopy(page, language) {
  const failures = await page.evaluate(async (language) => {
    const { copy, ADVANCED_COPY } = await import("/panel-copy.js");
    const failures = [];
    const visit = (root) => {
      for (const element of root.querySelectorAll("*")) {
        if (element.checkVisibility()) {
          if (language === "en" && !element.matches("style, script")) {
            for (const node of element.childNodes) {
              const value = node.nodeType === 3 ? node.textContent.trim() : "";
              if (ADVANCED_COPY[value] && ADVANCED_COPY[value] !== value && !["Elimina", "Salva"].includes(value)) {
                failures.push(`untranslated authored text: ${value}`);
              }
            }
          }
          if (element.hasAttribute("data-copy")) {
            const source = element.getAttribute("data-copy");
            if (element.textContent !== copy(language, source)) failures.push(`${source}: ${element.textContent}`);
          }
          for (const attr of ["aria-label", "title", "placeholder", "data-tooltip", "alt"]) {
            if (element.hasAttribute(`data-copy-${attr}`)) {
              const source = element.getAttribute(`data-copy-${attr}`);
              if (element.getAttribute(attr) !== copy(language, source)) failures.push(`${attr}: ${source}`);
            }
          }
        }
        if (element.shadowRoot) visit(element.shadowRoot);
      }
    }; visit(document); return failures;
  }, language);
  assert.deepEqual(failures, [], `authored copy follows ${language}`);
}

export async function checkAdvancedPanel(page, provider, language, check) {
  const en = language === "en";
  if (provider === "ring") {
    const archive = page.locator("vistoda-ring-recording-archive");
    await archive.locator(".recording-card, tbody tr").first().waitFor();
    await archive.locator("#manage-lists").click();
    assert.match(await archive.locator("#list-manager").textContent(), /Elimina/);
    await archive.getByRole("button", { name: "Info", exact: true }).first().click();
    assert.match(await archive.locator(".recording-info").textContent(), en ? /File path/ : /Percorso file/);
    assert.match(await archive.locator(".recording-info code").textContent(), /\/media\/Elimina/);
    await check(`archive-${language}`);
    await page.locator("vistoda-ring-device-identity #edit").click();
    const dialog = page.locator("vistoda-ring-identity-dialog");
    assert.match(await dialog.locator("h2").textContent(), en ? /Ring identity/ : /Identità Ring/);
    assert.equal(await dialog.locator('input[data-field="city"]').inputValue(), "Elimina");
    await checkAuthoredCopy(page, language); await check(`identity-${language}`);
    await dialog.locator("#cancel").click();
    assert.equal(await page.locator("vistoda-ring-device-identity #edit").evaluate(e => e === e.getRootNode().activeElement), true);
  }
  if (provider === "blink" || provider === "ezviz") {
    const archive = page.locator("vistoda-provider-recordings");
    await archive.locator(".item").first().waitFor();
    assert.match(await archive.locator(".item .meta").textContent(), en ? /Ready/ : /Pronta/);
    await archive.locator(".select-item input").check();
    await archive.locator("#add-selected-to-lists").click();
    assert.match(await archive.locator("#bulk-list-title").textContent(), en ? /Add clips/ : /Aggiungi clip/);
    assert.match(await archive.locator("#bulk-list-options").textContent(), /Elimina/);
    await checkAuthoredCopy(page, language); await check(`bulk-${provider}-${language}`);
    await archive.locator('#bulk-list-dialog button[value="cancel"]').click();
  }
  if (provider === "blink") {
    const usb = page.locator("vistoda-blink-storage");
    await usb.locator(".format-action").click();
    assert.match(await usb.locator("#format-target").textContent(), /Elimina/);
    assert.equal(await usb.locator("#confirm-format").isDisabled(), true);
    await checkAuthoredCopy(page, language); await check(`usb-format-${language}`);
    await page.keyboard.press("Escape");
    await page.locator("vistoda-blink-view #details").click();
    const settings = page.locator("vistoda-blink-settings");
    assert.equal(await settings.locator("#title").textContent(), "Elimina");
    assert.equal(await settings.locator('input[type="text"]').inputValue(), "Elimina");
    await settings.locator('details[data-section="video"] summary').click();
    assert.match(await settings.locator(".quality-options").textContent(), en ? /Best.*recommended/s : /Migliore.*consigliata/s);
    await checkAuthoredCopy(page, language); await check(`settings-${language}`);
    await settings.locator('details[data-section="privacy"] summary').click();
    const zones = page.locator("vistoda-blink-zones");
    assert.match(await zones.locator(".cell").first().getAttribute("aria-label"), en ? /^Row 1, column 1/ : /^Riga 1, colonna 1/);
    await checkAuthoredCopy(page, language); await check(`zones-${language}`);
    assert.equal(await zones.locator("#grid").evaluate(grid => grid.scrollWidth === grid.clientWidth && grid.scrollHeight === grid.clientHeight), true,
      "all zone cells must fit the image coordinate grid, not overflow and get clipped");
    await zones.locator(".cell").first().focus(); await page.keyboard.press("Space");
    assert.equal(await zones.locator(".cell").first().getAttribute("aria-pressed"), "false");
    await page.locator("vistoda-blink-view #details-back").click();
  }
}
