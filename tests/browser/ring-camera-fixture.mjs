import assert from "node:assert/strict";

export async function checkRingCameras(page) {
  const result = await page.evaluate(async () => {
    await import("/ring-camera-gallery.js");
    const { RingAudioSession } = await import("/ring-audio-session.js");
    const starts = [], stops = [];
    RingAudioSession.prototype.start = async function(mode) { starts.push({ ...this.entry, mode }); this.mode = mode; this.onState({ phase:"active", mode }); };
    RingAudioSession.prototype.destroy = async function() { stops.push(this.entry.camera_id); };
    const host = document.createElement("vistoda-ring-camera-gallery"); document.body.append(host);
    const hass = { user:{ is_admin:true }, locale:{ language:"en" }, callWS:async () => ({ cameras:[] }) };
    host.configure(hass, { providers:{ ring:{ entries:[{ entry_id:"account" }] } } });
    await new Promise(r => setTimeout(r, 0));
    const emptyHidden = host.hidden;
    const cameras = ["18446744073709551615", "2"].map(device_id => ({ device_id, name:"Camera " + device_id, location_name:"Home" }));
    hass.callWS = async () => ({ cameras });
    await host.load([{ entry_id:"account" }]);
    const selector = host.shadowRoot.querySelector("select");
    const count = selector.options.length;
    selector.value = "1"; selector.dispatchEvent(new Event("change"));
    host.shadowRoot.getElementById("live").click();
    const root = host.live.dialog.firstElementChild.shadowRoot;
    root.getElementById("rotate").click();
    await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
    const stage = root.getElementById("stage").getBoundingClientRect();
    const box = root.querySelector("video").getBoundingClientRect();
    const centered = Math.abs(box.x + box.width / 2 - stage.width / 2) < 2 && Math.abs(box.y + box.height / 2 - stage.height / 2) < 2;
    const rotated = root.getElementById("rotate").getAttribute("aria-pressed");
    const dialog = host.live.dialog;
    root.getElementById("close").click();
    const closed = !dialog.isConnected;
    host.remove();
    return { emptyHidden, count, starts, stops, centered, rotated, closed };
  });
  assert.equal(result.emptyHidden, true);
  assert.equal(result.count, 2);
  assert.deepEqual(result.starts, [{ entry_id:"account", camera_id:"2", mode:"listen" }]);
  assert.deepEqual(result.stops, ["2"]);
  assert.equal(result.rotated, "true"); assert.equal(result.centered, true);
  assert.equal(result.closed, true);
}
