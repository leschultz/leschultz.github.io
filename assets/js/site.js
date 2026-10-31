"use strict";

// Only collapse navigation after the enhancement is initialized. Without JS,
// every navigation link remains visible and every page is fully readable.
const menuButton = document.querySelector(".menu-toggle");
const navigation = document.querySelector("#site-nav");

if (menuButton && navigation) {
  const mobile = window.matchMedia("(max-width: 720px)");
  let navigationHadFocus = false;
  document.addEventListener("focusin", (event) => {
    // Browsers may blur a hidden link to <body> before dispatching a media-query
    // change. Retain its previous focus location until a real destination wins.
    if (event.target !== document.body) {
      navigationHadFocus = navigation.contains(event.target);
    }
  });
  const setMenu = (open, returnFocus = false) => {
    menuButton.setAttribute("aria-expanded", String(open));
    menuButton.querySelector("span").textContent = open ? "−" : "+";
    navigation.classList.toggle("is-open", open);
    if (returnFocus) menuButton.focus();
  };

  menuButton.hidden = false;
  document.documentElement.classList.add("menu-ready");
  menuButton.addEventListener("click", () => {
    setMenu(menuButton.getAttribute("aria-expanded") !== "true");
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && menuButton.getAttribute("aria-expanded") === "true") {
      setMenu(false, true);
    }
  });
  document.addEventListener("click", (event) => {
    if (!event.target.closest(".site-header")) {
      navigationHadFocus = false;
      setMenu(false);
    }
  });
  navigation.addEventListener("click", (event) => {
    const link = event.target.closest("a");
    if (!link || !mobile.matches) return;
    setMenu(false);
    // Preserve native anchor navigation and history, but move keyboard focus out
    // of the now-hidden menu to the destination section.
    const destination = new URL(link.href);
    if (destination.pathname === window.location.pathname && destination.hash) {
      const target = document.getElementById(destination.hash.slice(1));
      if (target) {
        target.setAttribute("tabindex", "-1");
        target.focus({ preventScroll: true });
      }
    }
  });
  mobile.addEventListener("change", () => {
    const wasInMenu = navigation.contains(document.activeElement) || navigationHadFocus;
    setMenu(false, mobile.matches && wasInMenu);
  });
}

document.querySelectorAll("[data-year]").forEach((element) => {
  element.textContent = String(new Date().getFullYear());
});
