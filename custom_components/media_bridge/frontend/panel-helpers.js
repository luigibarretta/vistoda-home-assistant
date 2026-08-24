export const PROVIDERS = ["ring", "blink", "ezviz"];

export const PROVIDER_META = {
  ring: {
    label: "Ring",
    icon: "mdi:phone-in-talk",
    description: "Citofono, audio full-duplex, portone e archivio chiamate",
  },
  blink: {
    label: "Blink",
    icon: "mdi:cctv",
    description: "Telecamere, live, snapshot, movimento e clip cloud",
  },
  ezviz: {
    label: "EZVIZ",
    icon: "mdi:doorbell-video",
    description: "Spioncino, snapshot aggiornato e live protetto",
  },
};

export function providerFromPanel(panel, pathname = globalThis.location?.pathname || "") {
  const configured = panel?.config?.provider;
  if (["overview", ...PROVIDERS].includes(configured)) return configured;
  const suffix = pathname.split("/").filter(Boolean).at(-1) || "vistoda";
  if (suffix === "vistoda") return "overview";
  return PROVIDERS.find((provider) => suffix === `vistoda-${provider}`) || "overview";
}

export function providerDevices(info, provider) {
  return info?.providers?.[provider]?.devices || [];
}

export function devicesWithDomain(info, provider, domain) {
  return providerDevices(info, provider).filter((device) => device.entities?.[domain]?.length);
}

export function firstEntity(device, domain, predicate = () => true) {
  return (device?.entities?.[domain] || []).find(predicate) || null;
}

export function entityState(hass, entity) {
  return entity?.entity_id ? hass?.states?.[entity.entity_id] : null;
}

export function pictureUrl(hass, entity, nonce = 0) {
  const state = entityState(hass, entity);
  const picture = state?.attributes?.entity_picture;
  if (!picture || !hass?.hassUrl) return "";
  const separator = picture.includes("?") ? "&" : "?";
  return hass.hassUrl(`${picture}${separator}vistoda=${nonce}`);
}

export function openMoreInfo(host, entityId) {
  if (!entityId) return;
  host.dispatchEvent(new CustomEvent("hass-more-info", {
    bubbles: true,
    composed: true,
    detail: { entityId },
  }));
}

export function stateText(hass, entity, fallback = "Non disponibile") {
  const state = entityState(hass, entity);
  if (!state || ["unknown", "unavailable"].includes(state.state)) return fallback;
  const numeric = Number(state.state);
  const value = Number.isFinite(numeric)
    ? numeric.toLocaleString(hass?.locale?.language || "it-IT", { maximumFractionDigits: 1 })
    : state.state;
  const unit = state.attributes?.unit_of_measurement;
  return unit ? `${value} ${unit}` : value;
}

export function setText(root, id, value) {
  const target = root.getElementById(id);
  if (target) target.textContent = value ?? "";
}
