(function () {
  const gallery = document.getElementById("detail-gallery");
  const dotsWrap = document.getElementById("gallery-dots");
  const lightbox = document.getElementById("lightbox");
  const lightboxImg = document.getElementById("lightbox-img");
  if (!gallery) return;

  const slides = Array.from(gallery.querySelectorAll(".detail-slide"));
  const dots = dotsWrap ? Array.from(dotsWrap.querySelectorAll(".gallery-dot")) : [];

  function activeIndex() {
    const w = gallery.clientWidth;
    if (!w) return 0;
    return Math.round(gallery.scrollLeft / w);
  }

  function syncDots() {
    const i = activeIndex();
    dots.forEach(function (dot, idx) {
      dot.classList.toggle("active", idx === i);
    });
  }

  gallery.addEventListener("scroll", function () {
    window.requestAnimationFrame(syncDots);
  }, { passive: true });

  gallery.querySelectorAll(".detail-zoom-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const src = btn.getAttribute("data-src");
      if (!src || !lightbox || !lightboxImg) return;
      lightboxImg.src = src;
      lightboxImg.alt = btn.querySelector("img")?.alt || "";
      lightbox.hidden = false;
      document.body.classList.add("lightbox-open");
    });
  });

  function closeLightbox() {
    if (!lightbox) return;
    lightbox.hidden = true;
    lightboxImg.src = "";
    document.body.classList.remove("lightbox-open");
  }

  lightbox?.querySelectorAll("[data-lightbox-close]").forEach(function (el) {
    el.addEventListener("click", closeLightbox);
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeLightbox();
  });

  syncDots();
})();
