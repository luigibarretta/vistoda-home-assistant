export function recordingCommand(config, action) {
  const namespace = config.provider === "blink" ? "blink_live_bridge" : "media_bridge/ezviz";
  const message = { type: `${namespace}/recordings/${action}` };
  if (config.provider === "blink" && ["create", "list"].includes(action)) {
    if (config.alias) message.alias = config.alias;
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

/** Recording origin from the optional manifest `trigger`; absent means manual. */
export function recordingTrigger(item) { return item?.trigger === "motion" ? "motion" : "manual"; }

/** When the media was recorded: the card interval for microSD, else capture start. */
export function recordedAt(item) {
  return item?.source === "sd" && Number.isInteger(item.sd_start)
    ? item.sd_start * 1000 : item?.started_at || item?.requested_at;
}
