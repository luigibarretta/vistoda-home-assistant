import assert from "node:assert/strict";
import { mkdir } from "node:fs/promises";

// Real nested components and CSS; only provider data and HA icons are fixtures.
export async function checkArchiveLayout(page, engine) {
  const original = page.viewportSize();
  await page.evaluate(() => {
    document.body.style.cssText = `margin:0;padding:12px;background:#111;color:#eee;
      font:14px Arial;--primary-color:#00aa80;--primary-text-color:#eee;
      --secondary-text-color:#aaa;--divider-color:#383838;--card-background-color:#1c1c1c;
      --secondary-background-color:#282828;`;
    if (!customElements.get("ha-icon")) customElements.define("ha-icon", class extends HTMLElement {
      connectedCallback() { this.style.cssText = "display:inline-block;width:20px;height:20px;flex-shrink:0";
        this.textContent = ({ "mdi:play":"▶", "mdi:download":"↓", "mdi:refresh":"↻",
          "mdi:chevron-left":"‹", "mdi:chevron-right":"›" })[this.getAttribute("icon")] || "◈"; }
    });
    const storage = view.$("storage");
    storage._storages = [{ network_id:"1", sync_module_id:"2", network_name:"Home Security Camera System",
      sync_module_status:"online", sync_module_firmware:"4.5.40",
      status:{usb_storage_used:1}, clips:[{id:"3", device_name:"Corridoio", media_available:true,
        created_at:"2026-09-14T12:00:00Z"}],
      pagination:{page:1,total_pages:1,total_items:76,has_next:true} }];
    storage._render();
    view._archives.configure({entry_id:"test"}, view._devices || []);
    view.$("pager").hidden = false;
    const recordings = view.$("recordings").shadowRoot;
    recordings.getElementById("archive-path").hidden = false;
    recordings.getElementById("archive-directory").textContent = "/data/recordings";
  });
  const directory = process.env.ARCHIVE_SCREENSHOTS;
  if (directory) await mkdir(directory, {recursive:true});
  for (const width of original.width === 390 ? [320,390,600] : [1280]) {
    await page.setViewportSize({width,height:844});
    for (const key of ["usb","local","network"]) {
      await page.locator(`#archive-tabs #tab-${key}`).click();
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      const card = await page.locator("#archives").boundingBox();
      const pager = await page.locator("#pager").boundingBox();
      assert.ok(card.y - pager.y - pager.height >= 23, `${engine}/${width}: pager gap`);
      const filter = page.locator(key === "usb" ? "#module-filter" : key === "local"
        ? "#local-camera-filter" : "vistoda-network-archive #camera");
      const bounds = await filter.boundingBox();
      assert.ok(bounds.x - card.x >= 16 && card.x + card.width - bounds.x - bounds.width >= 16,
        `${engine}/${width}/${key}: horizontal padding`);
      await page.locator("#archives").screenshot(directory ? {path:`${directory}/${engine}-${width}-${key}.png`} : {});
      const style = await filter.evaluate(node => ({radius:getComputedStyle(node).borderRadius,
        background:getComputedStyle(node).backgroundColor,height:node.getBoundingClientRect().height,
        theme:getComputedStyle(node).getPropertyValue('--secondary-background-color'),
        appearance:getComputedStyle(node).appearance}));
      assert.equal(style.radius,"13px"); assert.equal(style.background,"rgb(40, 40, 40)", `${engine}/${width}/${key}: filter background ${JSON.stringify(style)}`);
      assert.ok(style.height >= 44);
      const overflowing = await page.locator("#archives").evaluate(root => {
        const bad=[];
        function inspect(node) {
          for (const element of node.children || []) {
            const r=element.getBoundingClientRect();
            if (r.width && (r.left < -1 || r.right > innerWidth + 1)) bad.push(element.id || element.tagName);
            inspect(element); if(element.shadowRoot) inspect(element.shadowRoot);
          }
        }
        inspect(root); return bad;
      });
      assert.deepEqual(overflowing,[], `${engine}/${width}/${key}: overflow`);
      if(key === "network") {
        for(const selector of [".row button", ".archive-pagination button", "#add-selected-to-lists"]) {
          for(const button of await page.locator(`vistoda-network-archive ${selector}`).all()) {
            const box=await button.boundingBox(); assert.equal(box.width,44); assert.equal(box.height,44);
          }
        }
        const previous=await page.locator("vistoda-network-archive #previous").boundingBox();
        const next=await page.locator("vistoda-network-archive #next").boundingBox();
        assert.equal(previous.y,next.y,"NFS pager stays on one row");
      }
    }
  }
  await page.setViewportSize(original);
  await page.locator("#archive-tabs #tab-usb").click();
  await page.evaluate(() => { document.body.style.cssText = "margin:0"; });
}
