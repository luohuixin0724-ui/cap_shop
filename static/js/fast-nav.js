(function () {
  const loading = document.getElementById("nav-loading");
  const prefetched = new Set();

  function prefetchUrl(url) {
    if (!url || prefetched.has(url)) return;
    prefetched.add(url);
    const link = document.createElement("link");
    link.rel = "prefetch";
    link.href = url;
    link.as = url.match(/\.(jpg|jpeg|png|webp)/i) ? "image" : "document";
    document.head.appendChild(link);
  }

  function onIntent(el) {
    const href = el.getAttribute("href");
    const img = el.getAttribute("data-prefetch-img");
    if (href) prefetchUrl(href);
    if (img) prefetchUrl(img);
  }

  document.querySelectorAll(".prefetch-link").forEach(function (el) {
    el.addEventListener("touchstart", function () {
      onIntent(el);
    }, { passive: true });
    el.addEventListener("mouseenter", function () {
      onIntent(el);
    });
  });

  document.addEventListener("click", function (e) {
    const a = e.target.closest("a.prefetch-link, a.sig-card, a.sku-row");
    if (!a || a.target === "_blank") return;
    const href = a.getAttribute("href");
    if (!href || href.startsWith("#") || a.origin !== location.origin) return;
    if (loading) {
      loading.hidden = false;
    }
  });
})();
