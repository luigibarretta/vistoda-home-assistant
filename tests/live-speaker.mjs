import assert from "node:assert/strict";
import test from "node:test";
import { setPlayerMuted } from "../custom_components/media_bridge/frontend/live-speaker.js";
import { findLiveVideo } from "../custom_components/media_bridge/frontend/live-fullscreen.js";

test("listening updates HA transport selection and all nested players", () => {
  const video = { localName:"video", muted:true, volume:0 };
  const player = { localName:"ha-hls-player", muted:true, shadowRoot:{ children:[video] } };
  const stream = { localName:"ha-camera-stream", muted:true, shadowRoot:{ children:[player] } };
  setPlayerMuted(stream, false);
  assert.equal(stream.muted, false); assert.equal(player.muted, false);
  assert.equal(video.muted, false); assert.equal(video.volume, 1);
  setPlayerMuted(stream, true);
  assert.equal(stream.muted, true); assert.equal(video.muted, true);
});

test("a hidden HA fallback player cannot become the microphone/listening target", () => {
  const hiddenVideo = { localName:"video" }; const visibleVideo = { localName:"video" };
  const root = { children:[{ classList:{ contains: name => name === "hidden" },
    shadowRoot:{ children:[hiddenVideo] } }, { shadowRoot:{ children:[visibleVideo] } }] };
  assert.equal(findLiveVideo(root), visibleVideo);
});

test("unmute restores only the current peer's omitted receiving audio track", () => {
  const audio = { kind:"audio", readyState:"live" };
  const ended = { kind:"audio", readyState:"ended" };
  const tracks = [];
  const video = { localName:"video", srcObject:{ getAudioTracks:() => tracks, addTrack:t => tracks.push(t) } };
  const root = { localName:"ha-web-rtc-player", shadowRoot:{ querySelector:() => video, children:[video] },
    _peerConnection:{ getReceivers:() => [{ track:audio }, { track:ended }, { track:{ kind:"video", readyState:"live" } }] } };
  setPlayerMuted(root, true); assert.equal(tracks.length, 0);
  setPlayerMuted(root, false); setPlayerMuted(root, false);
  assert.deepEqual(tracks, [audio]);
});
