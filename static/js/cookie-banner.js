document.addEventListener("DOMContentLoaded", () => {
  const banner = document.querySelector("[data-cookie-banner]");
  const button = document.querySelector("[data-cookie-accept]");

  if (!banner || !button) {
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
      // Ignore private browsing/localStorage failures.
    }

    banner.hidden = true;
  });
});
