(function () {
  const form = document.getElementById("rental-form");
  const openBtn = document.getElementById("btn-open-save-modal");
  const modal = document.getElementById("save-order-modal");
  const confirmBtn = document.getElementById("btn-confirm-save-order");
  const errEl = document.getElementById("save-order-error");
  if (!form || !openBtn || !modal || !confirmBtn) return;

  const quoteUrl = form.dataset.quoteUrl || "";
  const productName = form.dataset.productName || "";
  const contactFields = form.querySelectorAll(".book-contact input, .book-contact textarea");

  function showError(msg) {
    if (!errEl) return;
    if (msg) {
      errEl.textContent = msg;
      errEl.hidden = false;
    } else {
      errEl.textContent = "";
      errEl.hidden = true;
    }
  }

  function openModal() {
    modal.hidden = false;
    modal.classList.add("is-open");
    document.body.classList.add("save-order-modal-open");
  }

  function closeModal() {
    modal.classList.remove("is-open");
    modal.hidden = true;
    document.body.classList.remove("save-order-modal-open");
    showError("");
  }

  modal.querySelectorAll("[data-save-order-close]").forEach(function (el) {
    el.addEventListener("click", closeModal);
  });

  function readForm() {
    return {
      start: form.querySelector("#start_date")?.value || "",
      end: form.querySelector("#end_date")?.value || "",
      qty: form.querySelector("#quantity")?.value || "1",
      phone: form.querySelector("#phone")?.value.trim() || "",
      address: form.querySelector("#address")?.value.trim() || "",
      note: form.querySelector("#location_note")?.value.trim() || "",
    };
  }

  function validateContact(data) {
    if (!data.phone) return "请填写手机号。";
    if (!data.address) return "请填写收货地址。";
    return null;
  }

  function validateDates(data) {
    if (!data.start || !data.end) return "请选择租借起止日期。";
    if (data.end < data.start) return "结束日期不能早于开始日期。";
    return null;
  }

  async function fetchQuote(data) {
    const params = new URLSearchParams({
      start_date: data.start,
      end_date: data.end,
      quantity: data.qty,
    });
    const res = await fetch(quoteUrl + "?" + params.toString(), { cache: "no-store" });
    const body = await res.json();
    if (!res.ok || !body.ok) {
      throw new Error(body.error || "无法计算费用，请检查日期与数量。");
    }
    return body;
  }

  function fillModal(data, quote) {
    document.getElementById("confirm-product-name").textContent = productName;
    document.getElementById("confirm-dates").textContent =
      data.start + " ～ " + data.end + "（" + quote.days + " 天）";
    document.getElementById("confirm-qty").textContent = data.qty + " 顶";
    document.getElementById("confirm-price").innerHTML =
      "租金 ¥" +
      quote.rent_yuan +
      " · 押金 ¥" +
      quote.deposit_yuan +
      '<br><strong class="pay-sum-inline">合计 ¥' +
      quote.total_yuan +
      "</strong>";
    document.getElementById("confirm-phone").textContent = data.phone;
    document.getElementById("confirm-address").textContent = data.address;
    const noteRow = document.getElementById("confirm-note-row");
    const noteDd = document.getElementById("confirm-note");
    if (data.note && noteRow && noteDd) {
      noteDd.textContent = data.note;
      noteRow.hidden = false;
    } else if (noteRow) {
      noteRow.hidden = true;
    }
  }

  openBtn.addEventListener("click", async function () {
    showError("");
    const data = readForm();
    const dateErr = validateDates(data);
    if (dateErr) {
      alert(dateErr);
      return;
    }
    const contactErr = validateContact(data);
    if (contactErr) {
      contactFields.forEach(function (el) {
        el.required = true;
      });
      alert(contactErr);
      return;
    }
    openBtn.disabled = true;
    try {
      const quote = await fetchQuote(data);
      fillModal(data, quote);
      openModal();
    } catch (e) {
      alert(e.message || "请稍后重试。");
    } finally {
      openBtn.disabled = false;
    }
  });

  form.querySelector('button[value="cart"]')?.addEventListener("click", function () {
    contactFields.forEach(function (el) {
      el.required = false;
    });
  });

  confirmBtn.addEventListener("click", function () {
    showError("");
    confirmBtn.disabled = true;
    const existing = form.querySelector('input[name="action"][data-save-submit]');
    if (existing) existing.remove();
    const action = document.createElement("input");
    action.type = "hidden";
    action.name = "action";
    action.value = "save_order";
    action.setAttribute("data-save-submit", "1");
    form.appendChild(action);
    form.submit();
  });
})();
