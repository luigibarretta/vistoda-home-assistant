import { copy } from "./panel-copy.js";
import { ptzRequest } from "./ezviz-ptz-model.js";

const KEYS = { ArrowUp: "up", ArrowDown: "down", ArrowLeft: "left", ArrowRight: "right" };
const STYLE = `.ptz{position:absolute;z-index:3;left:50%;bottom:calc(56px + env(safe-area-inset-bottom));
  transform:translateX(-50%);display:grid;gap:6px;grid-template-columns:repeat(3,48px);grid-template-rows:repeat(3,48px);
  grid-template-areas:". up ." "left . right" ". down ."}
  .ptz button{width:48px;height:48px;border:1px solid #888;border-radius:50%;background:#181818cc;color:#fff;cursor:pointer}
  .ptz button:focus-visible{outline:3px solid #00bcd4;outline-offset:2px}.ptz[aria-busy="true"] button{opacity:.6}
  .ptz [data-direction="up"]{grid-area:up}.ptz [data-direction="down"]{grid-area:down}
  .ptz [data-direction="left"]{grid-area:left}.ptz [data-direction="right"]{grid-area:right}`;

// Accessible D-pad over the live video. Each press is one PTZ step, through the
// Vistoda EZVIZ app or a native button (HA core presses START then STOP);
// presses never queue while one is pending.
export function mountPtz(stage, hass, targets, status) {
  if (!stage || !targets?.length) return;
  const doc = stage.ownerDocument;
  const style = doc.createElement("style"); style.textContent = STYLE;
  const pad = doc.createElement("div"); pad.className = "ptz"; pad.setAttribute("role", "group");
  pad.setAttribute("aria-label", copy({ hass }, "Controllo PTZ"));
  let pending = false;
  const press = async (target) => {
    if (pending) return;
    pending = true; pad.setAttribute("aria-busy", "true");
    try {
      const [kind, payload] = ptzRequest(target);
      if (kind === "ws") await hass.callWS(payload); else await hass.callService(...payload);
      if (status) status.textContent = "";
    } catch {
      if (status) status.textContent = copy({ hass }, "Comando PTZ non riuscito");
    } finally { pending = false; pad.removeAttribute("aria-busy"); }
  };
  for (const target of targets) {
    const button = doc.createElement("button"); button.type = "button";
    button.dataset.direction = target.direction;
    const label = copy({ hass }, target.label);
    button.title = label; button.setAttribute("aria-label", label);
    const icon = doc.createElement("ha-icon"); icon.setAttribute("icon", target.icon);
    button.append(icon); button.addEventListener("click", () => press(target));
    pad.append(button);
  }
  pad.addEventListener("keydown", (event) => {
    const target = targets.find((item) => item.direction === KEYS[event.key]);
    if (!target) return;
    event.preventDefault(); press(target);
  });
  stage.append(style, pad);
}
