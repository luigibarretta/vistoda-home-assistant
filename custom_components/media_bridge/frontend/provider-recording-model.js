export function recordingCommand(config, action) {
  const namespace = config.provider === "blink" ? "blink_live_bridge" : "media_bridge/ezviz";
  const message = { type: `${namespace}/recordings/${action}` };
  if (config.provider === "blink" && ["create", "list"].includes(action)) {
    message.alias = config.alias;
  }
  if (config.provider !== "blink") message.entry_id = config.entryId;
  return message;
}

export function recordingMediaPath(config, recordingId, playback = false) {
  if (config.provider === "blink") {
    return `/api/blink_live_bridge/v1/recordings/${recordingId}/media`;
  }
  const base = `/api/media_bridge/ezviz/recordings/${config.entryId}/${recordingId}`;
  return playback ? `${base}/playback.mp4` : base;
}

export function cameraRecordings(items, alias) {
  return items
    .filter((item) => !alias || item.camera === alias)
    .sort((left, right) => right.requested_at.localeCompare(left.requested_at));
}
