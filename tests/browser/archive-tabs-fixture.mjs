import assert from "node:assert/strict";

export async function checkArchives(page) {
  await page.evaluate(async () => {
    const archive = view.$("network-archive");
    const realCall = view._hass.callWS;
    view._hass.callWS = async (request) => {
      if (request.type !== "media_bridge/network_archive/list") return realCall(request);
      return { cameras: ["Kitchen"], directory: "/media/fixture", automatic: { enabled: false },
        items: [{ id: "blink-usb/Kitchen/1-2.mp4", media_id: "usb:1:2:1:2", camera: "Kitchen",
          created_at: "2026-09-14T12:00:00Z", media_type: "video/mp4", media_path: "/fixture.mp4" }],
        pagination: { page: request.page, page_size: request.page_size, total_items: 1,
          total_pages: 1, has_previous: false, has_next: false } };
    };
    await archive.reload();
  });
  const tabs = page.locator("#archive-tabs");
  await tabs.locator("#tab-network").click();
  const archive = page.locator("vistoda-network-archive");
  assert.equal(await archive.locator(".row").count(), 1);
  assert.equal(await archive.locator("#path").textContent(), "/media/fixture");
  await archive.locator('.row input[type="checkbox"]').check();
  assert.equal(await archive.locator("#add-selected-to-lists").isEnabled(), true);
  await tabs.locator("#tab-local").click();
  assert.equal(await archive.isVisible(), false);
  assert.equal(await page.locator("#recordings").isVisible(), true);
  await tabs.locator("#tab-local").focus(); await page.keyboard.press("ArrowRight");
  assert.equal(await archive.isVisible(), true);
  assert.equal(await archive.locator('.row input[type="checkbox"]').isChecked(), true);
  await tabs.locator("#tab-usb").click();
}
