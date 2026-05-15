document.addEventListener("DOMContentLoaded", () => {
  const button = document.querySelector("[data-mobile-menu-button]");
  const panel = document.querySelector("[data-mobile-menu-panel]");

  if (!(button instanceof HTMLButtonElement) || !(panel instanceof HTMLElement)) {
    return;
  }

  button.addEventListener("click", () => {
    const isOpen = button.getAttribute("aria-expanded") === "true";
    button.setAttribute("aria-expanded", String(!isOpen));
    panel.hidden = isOpen;
  });
});