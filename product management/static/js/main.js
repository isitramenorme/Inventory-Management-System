/* StockFlow - small progressive enhancements (no dependencies). */

(function () {
  "use strict";

  var body = document.body;
  var toggleButton = document.querySelector("[data-sidebar-toggle]");

  /* -------------------------------------------------- Sidebar (mobile) */
  function openSidebar() {
    body.classList.add("sidebar-open");
    if (toggleButton) toggleButton.setAttribute("aria-expanded", "true");
  }

  function closeSidebar() {
    body.classList.remove("sidebar-open");
    if (toggleButton) toggleButton.setAttribute("aria-expanded", "false");
  }

  if (toggleButton) {
    toggleButton.addEventListener("click", function () {
      if (body.classList.contains("sidebar-open")) {
        closeSidebar();
      } else {
        openSidebar();
      }
    });
  }

  document.querySelectorAll("[data-sidebar-close]").forEach(function (element) {
    element.addEventListener("click", closeSidebar);
  });

  // Close the drawer when a navigation link is used on small screens.
  document.querySelectorAll(".sidebar .nav__link[href]").forEach(function (link) {
    link.addEventListener("click", closeSidebar);
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") closeSidebar();
  });

  // Reset the drawer state when growing back to desktop width.
  window.addEventListener("resize", function () {
    if (window.innerWidth > 980) closeSidebar();
  });

  /* ------------------------------------------------------------- Toast */
  window.showToast = function (message) {
    var stack = document.getElementById("toastStack");
    if (!stack) return;

    var toast = document.createElement("div");
    toast.className = "toast";
    toast.textContent = message;
    stack.appendChild(toast);

    window.setTimeout(function () {
      toast.style.transition = "opacity .2s ease, transform .2s ease";
      toast.style.opacity = "0";
      toast.style.transform = "translateY(6px)";
      window.setTimeout(function () {
        if (toast.parentNode) toast.parentNode.removeChild(toast);
      }, 220);
    }, 3200);
  };
})();
