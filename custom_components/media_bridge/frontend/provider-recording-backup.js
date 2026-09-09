import { cameraRecordings } from "./provider-recording-model.js";

export async function readyRecordings(fetchPage, alias) {
  const first = await fetchPage(1, 50);
  const items = [...(first.recordings || [])];
  for (let page = 2; page <= (first.pagination?.total_pages || 1); page += 1) {
    const result = await fetchPage(page, 50); items.push(...(result.recordings || []));
  }
  return cameraRecordings(items, alias).filter((item) => item.status === "ready");
}

export async function backupRecording(hass, config, item) {
  return hass.callWS({
    type: "media_bridge/provider/recordings/backup",
    provider: config.provider,
    entry_id: config.entryId || "",
    recording_id: item.recording_id,
  });
}
