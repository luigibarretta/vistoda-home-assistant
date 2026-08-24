export const RECORDINGS_PER_PAGE = 8;

export function recordingPage(recordings, requestedPage, pageSize = RECORDINGS_PER_PAGE) {
  const pages = Math.max(1, Math.ceil(recordings.length / pageSize));
  const page = Math.min(pages, Math.max(1, requestedPage));
  const start = (page - 1) * pageSize;
  return { items: recordings.slice(start, start + pageSize), page, pages };
}

export function recordingDate(recording, locale = "it-IT", timeZone = undefined) {
  const options = { dateStyle: "medium", timeStyle: "short" };
  if (timeZone) options.timeZone = timeZone;
  return new Intl.DateTimeFormat(locale || "it-IT", options)
    .format(new Date(recording.started_at * 1000));
}

export function recordingDuration(recording) {
  const seconds = Math.max(0, recording.ended_at - recording.started_at);
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return minutes ? `${minutes} min ${String(remainder).padStart(2, "0")} s` : `${remainder} s`;
}

export function recordingSize(bytes) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KiB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MiB`;
}
