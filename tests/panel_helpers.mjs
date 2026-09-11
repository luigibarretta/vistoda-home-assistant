import assert from "node:assert/strict";
import test from "node:test";

import {
  HOME_ASSISTANT_PATH,
  homeAssistantPath,
  canonicalVistodaPath,
  devicesWithDomain,
  firstEntity,
  isVistodaPath,
  pictureUrl,
  providerFromPanel,
  providerPath,
  snapshotTimeText,
  snapshotTimestamp,
  stateText,
  swipeStep,
  wrappedIndex,
} from "../custom_components/media_bridge/frontend/panel-helpers.js";

const info = {
  providers: {
    blink: {
      devices: [
        {
          name: "Kitchen",
          entities: {
            camera: [{ entity_id: "camera.kitchen", name: "Kitchen" }],
            sensor: [
              { entity_id: "sensor.kitchen_temperature", device_class: "temperature" },
            ],
          },
        },
        { name: "Sync", entities: { alarm_control_panel: [{ entity_id: "alarm.blink" }] } },
      ],
    },
  },
};

test("provider route resolution keeps hub and compatibility aliases stable", () => {
  assert.equal(providerFromPanel({ config: { provider: "overview" } }, "/vistoda-ring"), "ring");
  assert.equal(providerFromPanel({ config: { provider: "overview" } }, "/vistoda/blink"), "blink");
  assert.equal(providerFromPanel({ config: { provider: "blink" } }, "/vistoda"), "overview");
  assert.equal(providerFromPanel({}, "/vistoda-ezviz"), "ezviz");
  assert.equal(providerFromPanel({}, "/unknown"), "overview");
  assert.equal(providerPath("ring"), "/vistoda/ring");
  assert.equal(canonicalVistodaPath("/vistoda-ring"), "/vistoda/ring");
  assert.equal(canonicalVistodaPath("/vistoda/ring"), "/vistoda/ring");
});

test("inventory helpers select provider devices and entity domains", () => {
  const cameras = devicesWithDomain(info, "blink", "camera");
  assert.equal(cameras.length, 1);
  assert.equal(firstEntity(cameras[0], "camera").entity_id, "camera.kitchen");
  assert.equal(firstEntity(cameras[0], "sensor", (item) => item.device_class === "battery"), null);
});

test("picture URLs remain HA-local and receive a refresh nonce", () => {
  const hass = {
    hassUrl: (path) => `https://ha.example${path}`,
    states: {
      "camera.kitchen": { attributes: { entity_picture: "/api/camera_proxy/camera.kitchen?token=x" } },
    },
  };
  assert.equal(
    pictureUrl(hass, { entity_id: "camera.kitchen" }, 42),
    "https://ha.example/api/camera_proxy/camera.kitchen?token=x&vistoda=42",
  );
  assert.equal(pictureUrl(hass, { entity_id: "camera.absent" }), "");
});

test("state labels include units and hide unavailable values", () => {
  const hass = {
    states: {
      "sensor.temperature": { state: "21.4", attributes: { unit_of_measurement: "°C" } },
      "sensor.missing": { state: "unavailable", attributes: {} },
    },
  };
  assert.equal(stateText(hass, { entity_id: "sensor.temperature" }), "21,4 °C");
  assert.equal(stateText(hass, { entity_id: "sensor.missing" }, "Assente"), "Assente");
}
);

test("Blink snapshot timestamps use the provider epoch and an observed refresh fallback", () => {
  const state = { attributes: {
    thumbnail: "/thumbnail.jpg?ts=/nested/thumbnail.jpg?ts=1788935529&ext=&ext=",
  } };
  assert.equal(snapshotTimestamp(state), 1788935529000);
  assert.equal(snapshotTimestamp(state, 1788935530000), 1788935530000);
  assert.match(snapshotTimeText(state, "it-IT"), /^Snapshot del .*2026/);
  assert.equal(snapshotTimeText({ attributes: {} }), "Ora snapshot non disponibile");
});

test("horizontal swipes wrap forever and ignore short or vertical gestures", () => {
  assert.equal(wrappedIndex(4, 1, 5), 0);
  assert.equal(wrappedIndex(0, -1, 5), 4);
  assert.equal(swipeStep({ x: 180, y: 20 }, { x: 80, y: 25 }), 1);
  assert.equal(swipeStep({ x: 80, y: 20 }, { x: 180, y: 25 }), -1);
  assert.equal(swipeStep({ x: 80, y: 20 }, { x: 100, y: 150 }), 0);
});

test("mobile exit fallback uses the user's HA dashboard without private paths", () => {
  assert.equal(HOME_ASSISTANT_PATH, "/lovelace");
  assert.equal(homeAssistantPath({ defaultPanel: "home" }), "/home");
  assert.equal(homeAssistantPath({ defaultPanel: "vistoda" }), "/lovelace");
  assert.equal(homeAssistantPath({ defaultPanel: "//example.com" }), "/lovelace");
  assert.equal(isVistodaPath("/vistoda-blink"), true);
  assert.equal(isVistodaPath("/vistoda/blink"), true);
  assert.equal(isVistodaPath("/casa-famiglia/casa"), false);
});
