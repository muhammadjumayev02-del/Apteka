"use strict";
const searchForm = document.querySelector("#search-form");
if (searchForm) {
  const input = document.querySelector("#query");
  const results = document.querySelector("#results");
  const status = document.querySelector("#search-status");
  let timer, controller, revision = 0;
  async function search(version) {
    controller = new AbortController();
    const url = new URL(searchForm.action);
    url.searchParams.set("q", input.value.trim());
    url.searchParams.set("partial", "1");
    status.textContent = status.dataset.loading;
    results.setAttribute("aria-busy", "true");
    try {
      const response = await fetch(url, {signal: controller.signal});
      if (version !== revision) return;
      if (response.redirected) { window.location.assign(response.url); return; }
      if (!response.ok) throw new Error("Qidiruv xatosi");
      const html = await response.text();
      if (version !== revision) return;
      results.innerHTML = html;
      url.searchParams.delete("partial");
      history.replaceState(null, "", url);
      status.textContent = status.dataset.updated;
    } catch (error) {
      if (error.name !== "AbortError" && version === revision)
        status.textContent = status.dataset.error;
    } finally {
      if (version === revision) results.removeAttribute("aria-busy");
    }
  }
  input.addEventListener("input", () => {
    clearTimeout(timer);
    controller?.abort();
    const version = ++revision;
    timer = setTimeout(() => search(version), 220);
  });
}
const addPlacement = document.querySelector("#add-placement");
if (addPlacement) {
  addPlacement.addEventListener("click", () => {
    const total = document.querySelector("#id_places-TOTAL_FORMS");
    const index = Number(total.value);
    if (index >= 100) return;
    const html = document.querySelector("#empty-placement").innerHTML.replaceAll("__prefix__", index);
    document.querySelector("#placements").insertAdjacentHTML("beforeend", html);
    total.value = index + 1;
    if (index + 1 >= 100) addPlacement.disabled = true;
  });
}

const saleTotal = document.querySelector("#sale-total");
if (saleTotal) {
  const quantity = document.querySelector("#id_quantity");
  const cents = BigInt(saleTotal.dataset.price.replace(".", ""));
  function updateTotal() {
    const value = quantity.value;
    if (!/^\d{1,7}$/.test(value) || Number(value) > 1000000) {
      saleTotal.textContent = "—";
      return;
    }
    const total = cents * BigInt(value);
    saleTotal.textContent = `${total / 100n},${String(total % 100n).padStart(2, "0")}`;
  }
  quantity.addEventListener("input", updateTotal);
  updateTotal();
}
