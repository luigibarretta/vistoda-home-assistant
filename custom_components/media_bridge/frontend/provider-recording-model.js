export function recordingCommand(config, action) {
  const namespace = config.provider === "blink" ? "blink_live_bridge" : "media_bridge/ezviz";
  const message = { type: `${namespace}/recordings/${action}` };
  if (config.provider === "blink" && action === "create") message.alias = config.alias;
  if (config.provider !== "blink") message.entry_id = config.entryId;
  return message;
}

export function recordingMediaPath(config, recordingId) {
  return config.provider === "blink"
    ? `/api/blink_live_bridge/v1/recordings/${recordingId}/media`
    : `/api/media_bridge/ezviz/recordings/${config.entryId}/${recordingId}`;
}

export function cameraRecordings(items, alias) {
  return items
    .filter((item) => !alias || item.camera === alias)
    .sort((left, right) => right.requested_at.localeCompare(left.requested_at));
}
