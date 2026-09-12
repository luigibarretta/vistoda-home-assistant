export const PAGE_SIZES = Object.freeze([10, 25, 50, 100]);
export const PAGE_SIZE_TEMPLATE = `<label for="page-size" data-copy="Clip per pagina">Clip per pagina</label>
  <select id="page-size">${PAGE_SIZES.map((size) => `<option value="${size}">${size}</option>`).join("")}</select>`;

export function bindPageSize(root, changed) {
  root.getElementById("page-size").addEventListener("change", (event) => {
    const size = Number(event.target.value);
    if (!event.target.disabled && PAGE_SIZES.includes(size)) changed(size);
  });
}
export function renderPageSize(root, size, busy) {
  const select = root.getElementById("page-size");
  select.value = String(size); select.disabled = Boolean(busy);
}
