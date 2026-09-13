import assert from "node:assert/strict";
import test from "node:test";
import { configureRingMedia, ringSessionRequest } from "../custom_components/media_bridge/frontend/ring-session-protocol.js";
import { RingAudioSession } from "../custom_components/media_bridge/frontend/ring-audio-session.js";

test("native cameras use H264 receiving video while Intercom remains audio-only", () => {
  globalThis.RTCRtpSender = { getCapabilities: () => ({ codecs:[{ mimeType:"audio/PCMU" }] }) };
  globalThis.RTCRtpReceiver = { getCapabilities: () => ({ codecs:[{ mimeType:"video/H264" }] }) };
  for (const camera of [false, true]) {
    const calls = [], track = {}, sender = {};
    const session = { entry:camera ? { camera_id:"18446744073709551615" } : {}, localMedia:{ stream:{ getAudioTracks:() => [track] } } };
    const pc = { addTransceiver: (kind, options) => { calls.push({ kind, options }); return { sender, setCodecPreferences: codecs => assert.equal(codecs.length, 1) }; } };
    assert.equal(configureRingMedia(session, pc), sender);
    assert.equal(calls.length, camera ? 2 : 1);
    assert.equal(calls[0].options.direction, "sendrecv");
    if (camera) assert.deepEqual(calls[1], { kind:"video", options:{ direction:"recvonly" } });
  }
});

test("camera routes preserve IDs without inheriting an Intercom control route", () => {
  assert.deepEqual(ringSessionRequest({ entry_id:"entry", camera_id:"18446744073709551615" }, "delete"), {
    type:"media_bridge/ring/camera/session/delete", entry_id:"entry", camera_id:"18446744073709551615",
  });
  assert.deepEqual(ringSessionRequest({ entry_id:"entry" }, "delete"), { type:"media_bridge/ring/session/delete", entry_id:"entry" });
});

test("streamless camera tracks retain both receiving audio and video without duplication", async () => {
  globalThis.MediaStream = class { constructor() { this.tracks = []; } getTracks() { return this.tracks; } addTrack(track) { this.tracks.push(track); } };
  const video = { srcObject:null, play:async () => {} };
  const session = new RingAudioSession({}, { camera_id:"123" }, video, () => {});
  const audioTrack = { kind:"audio" }, videoTrack = { kind:"video" };
  for (const track of [audioTrack, videoTrack, audioTrack]) await session.play({ streams:[], track }, 0);
  assert.deepEqual(video.srcObject.getTracks(), [audioTrack, videoTrack]);
});
