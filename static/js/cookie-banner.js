document.addEventListener("DOMContentLoaded", () => {
  const banner = document.querySelector("[data-cookie-banner]");
  const button = document.querySelector("[data-cookie-accept]");

  if (!(banner instanceof HTMLElement) || !(button instanceof HTMLButtonElement)) {
    return;
  }

  let consent = null;

  try {
    consent = window.localStorage.getItem("cookie_consent");
  } catch {
    consent = null;
  }

  if (consent !== "necessary") {
    banner.hidden = false;
  }

  button.addEventListener("click", () => {
    try {
      window.localStorage.setItem("cookie_consent", "necessary");
    } catch {
      // localStorage may be unavailable in private mode.
    }

    banner.hidden = true;
  });
});