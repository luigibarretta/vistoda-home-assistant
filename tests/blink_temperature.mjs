import assert from "node:assert/strict";
import test from "node:test";
import { temperatureInputModel } from "../custom_components/media_bridge/frontend/blink-temperature-control.js";
import { orderedChanges, commitDraft } from "../custom_components/media_bridge/frontend/blink-setting-draft.js";

test("temperature editor uses HA units and rejects invalid/out-of-range values", () => {
  const field = {value:86,min:-4,max:113};
  const c = temperatureInputModel(field, {config:{unit_system:{temperature:"°C"}}});
  assert.equal(c.value,30); assert.equal(c.min,-20); assert.equal(c.max,45);
  assert.equal(c.encode(30),86); assert.equal(c.encode(NaN),null); assert.equal(c.encode(80),null);
  const f = temperatureInputModel(field, {config:{unit_system:{temperature:"°F"}}});
  assert.equal(f.value,86); assert.equal(f.encode(90),90);
  assert.equal(temperatureInputModel({...field,value:null},{}).value, "");
});

test("missing upstream thresholds require explicit paired initialization before enable", async () => {
  const settings = {revision:"before",settings:[{key:"temperature_min",value:null},
    {key:"temperature_max",value:null},{key:"temperature_alerts",value:false}]};
  const calls = [];
  const hass = {callWS: async (request) => { calls.push(request); return {...settings,revision:"after"}; }};
  await assert.rejects(commitDraft(hass,"camera",settings,new Map([["temperature_alerts",true]])),/temperature_missing/);
  assert.equal(calls.length,0);
  await commitDraft(hass,"camera",settings,new Map([["temperature_alerts",true],
    ["temperature_min",32],["temperature_max",95]]));
  assert.deepEqual(calls.map((request)=>request.key),["temperature_thresholds","temperature_alerts"]);
  assert.deepEqual(calls[0].value,{temperature_min:32,temperature_max:95});
  assert.equal(calls[1].revision,"after");
  await assert.rejects(commitDraft({callWS:async()=>{throw new Error("timeout");}},
    "camera",settings,new Map([["temperature_min",32],["temperature_max",95]])),
    (error)=>error.rollbackFailed === true);
});

test("paired thresholds expand before shrinking and enable alerts last", () => {
  const settings = {settings:[{key:"temperature_min",value:32},{key:"temperature_max",value:60}]};
  const draft = new Map([["temperature_alerts",true],["temperature_min",80],["temperature_max",100]]);
  assert.deepEqual(orderedChanges(settings,draft).map(([key])=>key),
    ["temperature_max","temperature_min","temperature_alerts"]);
  assert.deepEqual(Array.from(draft.keys()),["temperature_alerts","temperature_min","temperature_max"]);
  assert.throws(()=>orderedChanges(settings,new Map([["temperature_min",55]])),/temperature_gap/);
});
