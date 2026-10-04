import assert from "node:assert/strict";
import test from "node:test";
import { connectionCopyKey, ezvizConnectivity } from "../custom_components/media_bridge/frontend/ezviz-connectivity.js";

const device = {
  entities: {
    binary_sensor: [
      { entity_id: "binary_sensor.bridge", device_class: "connectivity" },
      { entity_id: "binary_sensor.camera", device_class: "connectivity" },
      { entity_id: "binary_sensor.motion", device_class: "motion" },
    ],
  },
};

function hass(camera, bridge, scoped = true) {
  return {
    states: {
      "binary_sensor.bridge": { state: bridge, attributes: scoped ? { connectivity_scope: "bridge" } : {} },
      "binary_sensor.camera": { state: camera, attributes: { connectivity_scope: "camera" } },
      "binary_sensor.motion": { state: "on", attributes: {} },
    },
  };
}

test("camera reachability is separate from the Vistoda bridge", () => {
  assert.deepEqual(ezvizConnectivity(hass("off", "on"), device), { camera: "off", bridge: "on" });
  assert.deepEqual(ezvizConnectivity(hass("on", "off"), device), { camera: "on", bridge: "off" });
});

test("unknown or unavailable states never claim a connection", () => {
  assert.deepEqual(ezvizConnectivity(hass("unavailable", "unknown"), device), {
    camera: "unknown", bridge: "unknown",
  });
  assert.deepEqual(ezvizConnectivity({ states: {} }, null), { camera: "unknown", bridge: "unknown" });
});

test("an unscoped legacy bridge sensor is never mistaken for the camera", () => {
  const legacy = { entities: { binary_sensor: [device.entities.binary_sensor[0]] } };
  assert.deepEqual(ezvizConnectivity(hass("on", "on", false), legacy), { camera: "unknown", bridge: "on" });
  assert.deepEqual(ezvizConnectivity(hass("off", "on", false), device), { camera: "off", bridge: "on" });
});

test("connection copy keys map to the authored catalog", () => {
  assert.equal(connectionCopyKey("on"), "Connesso");
  assert.equal(connectionCopyKey("off"), "Disconnesso");
  assert.equal(connectionCopyKey("unknown"), "Non rilevata");
});
