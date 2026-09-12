import { copy } from "./panel-copy.js";

export function temperatureInputModel(field, hass) {
  const fahrenheit = hass?.config?.unit_system?.temperature === "°F";
  const display = (value) => value === null ? "" : fahrenheit ? value : Math.round((value - 32) * 50 / 9) / 10;
  return { unit: fahrenheit ? "°F" : "°C", value: display(field.value),
    min: display(field.min), max: display(field.max),
    encode(value) {
      if (!Number.isFinite(value)) return null;
      const raw = Math.round(fahrenheit ? value : value * 9 / 5 + 32);
      return raw < field.min || raw > field.max ? null : raw;
    } };
}

export function temperatureControl(view, field, label) {
  const model = temperatureInputModel(field, view._hass);
  const wrapper = document.createElement("div"); wrapper.className = "temperature-control";
  const input = document.createElement("input"); input.type = "number";
  input.inputMode = "decimal"; input.step = "any";
  input.min = model.min; input.max = model.max; input.value = model.value;
  if (field.value === null) input.placeholder = "—";
  input.setAttribute("aria-label", `${label} (${model.unit})`);
  const unit = document.createElement("span"); unit.textContent = model.unit;
  const stage = (value) => {
    const raw = model.encode(value);
    input.setCustomValidity(raw === null ? copy(view, "Temperatura fuori intervallo") : "");
    if (raw === null) { input.reportValidity(); return; }
    view._stage(field.key, raw);
  };
  input.addEventListener("change", () => stage(input.valueAsNumber));
  const buttons = [-1, 1].map((delta) => {
    const button = document.createElement("button"); button.type = "button";
    const description = copy(view, delta < 0 ? "Diminuisci temperatura" : "Aumenta temperatura");
    button.setAttribute("aria-label", `${description}: ${label}`); button.title = description;
    const icon = document.createElement("ha-icon");
    icon.setAttribute("icon", delta < 0 ? "mdi:minus" : "mdi:plus");
    icon.setAttribute("aria-hidden", "true"); button.append(icon);
    const next = model.value === "" ? (delta < 0 ? model.min : model.max) : model.value + delta;
    button.disabled = model.encode(next) === null;
    button.addEventListener("click", () => stage(next));
    return button;
  });
  wrapper.append(buttons[0], input, unit, buttons[1]); return wrapper;
}
