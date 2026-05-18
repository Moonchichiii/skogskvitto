/**
 * SkogsKvitto — bundled client JS.
 *
 * Strategy:
 *   - Most interactivity lives in Alpine components defined here.
 *   - One global helper (window.applyCorrection) exposed for templates that
 *     need to apply OCR-correction suggestions into the scan-review form.
 *
 * Loaded once via base.html. No per-page scripts.
 */

(function () {
  "use strict";

  // ---------------------------------------------------------------------------
  // Alpine components — registered before Alpine starts
  // ---------------------------------------------------------------------------

  document.addEventListener("alpine:init", () => {
    /**
     * cookieBanner — shows the cookie banner until the user accepts.
     * Persists the choice via localStorage (degrades gracefully).
     */
    Alpine.data("cookieBanner", () => ({
      show: false,

      init() {
        let consent = null;
        try {
          consent = window.localStorage.getItem("cookie_consent");
        } catch (err) {
          consent = null;
        }
        this.show = consent !== "necessary";
      },

      accept() {
        try {
          window.localStorage.setItem("cookie_consent", "necessary");
        } catch (err) {
          // ignore — private mode or storage unavailable
        }
        this.show = false;
      },
    }));

    /**
     * receiptUpload — direct-to-Cloudinary upload flow.
     *
     * 1. User selects file → preview shown
     * 2. User clicks "Starta skanning" → upload() runs:
     *    a. POST to /scanning/sign/ → returns Cloudinary signature
     *    b. POST file to api.cloudinary.com directly with signature
     *    c. POST result back to /scanning/job/<id>/intake/
     *    d. Receive pending HTML → inject into #scan-result → HTMX takes over polling
     */
    Alpine.data("receiptUpload", () => ({
      previewUrl: "",
      fileName: "",
      file: null,
      uploading: false,
      uploadStatusText: "",
      error: "",
      _objectUrl: null,

      onFileChange(event) {
        this.error = "";
        const target = event.target;
        if (!(target instanceof HTMLInputElement)) return;
        const file = target.files && target.files[0];
        if (!file) return;

        if (!file.type.startsWith("image/")) {
          this.error = "Endast bildfiler stöds.";
          return;
        }
        if (file.size > 10 * 1024 * 1024) {
          this.error = "Bilden är för stor (max 10 MB).";
          return;
        }

        this._revokeObjectUrl();
        const url = URL.createObjectURL(file);
        this._objectUrl = url;
        this.previewUrl = url;
        this.fileName = file.name;
        this.file = file;
      },

      async upload() {
        if (!this.file || this.uploading) return;
        this.uploading = true;
        this.error = "";

        const csrfToken = this._csrfToken();
        if (!csrfToken) {
          this.error = "CSRF-token saknas. Ladda om sidan.";
          this.uploading = false;
          return;
        }

        try {
          // 1. Sign
          this.uploadStatusText = "Förbereder uppladdning...";
          const signResponse = await fetch("/scanning/sign/", {
            method: "POST",
            headers: { "X-CSRFToken": csrfToken, Accept: "application/json" },
          });
          if (!signResponse.ok) {
            const err = await signResponse.json().catch(() => ({}));
            throw new Error(
              err.error || `Sign endpoint returned ${signResponse.status}`
            );
          }
          const sig = await signResponse.json();

          // 2. Upload to Cloudinary
          this.uploadStatusText = "Laddar upp bilden...";
          const cloudFormData = new FormData();
          cloudFormData.append("file", this.file);
          cloudFormData.append("api_key", sig.api_key);
          cloudFormData.append("timestamp", String(sig.timestamp));
          cloudFormData.append("signature", sig.signature);
          cloudFormData.append("folder", sig.folder);
          cloudFormData.append("public_id", sig.public_id);

          const cloudResponse = await fetch(
            `https://api.cloudinary.com/v1_1/${sig.cloud_name}/image/upload`,
            { method: "POST", body: cloudFormData }
          );
          if (!cloudResponse.ok) {
            const errText = await cloudResponse.text().catch(() => "");
            console.error(
              "Cloudinary upload failed:",
              cloudResponse.status,
              errText
            );
            throw new Error("Cloudinary avvisade uppladdningen.");
          }
          const cloudResult = await cloudResponse.json();

          // 3. Notify backend
          this.uploadStatusText = "Startar analys...";
          const intakeBody = new FormData();
          intakeBody.append("public_id", cloudResult.public_id);
          intakeBody.append("secure_url", cloudResult.secure_url);
          const intakeResponse = await fetch(
            `/scanning/job/${sig.job_id}/intake/`,
            {
              method: "POST",
              headers: { "X-CSRFToken": csrfToken },
              body: intakeBody,
            }
          );
          if (!intakeResponse.ok) {
            throw new Error(
              `Intake endpoint returned ${intakeResponse.status}`
            );
          }
          const html = await intakeResponse.text();

          // 4. Hand off to HTMX
          const resultSlot = document.getElementById("scan-result");
          if (resultSlot) {
            resultSlot.innerHTML = html;
            if (typeof window.htmx !== "undefined") {
              window.htmx.process(resultSlot);
            }
          }
        } catch (err) {
          this.error =
            err && err.message ? err.message : "Ett okänt fel inträffade.";
          console.error("Upload failed:", err);
        } finally {
          this.uploading = false;
          this.uploadStatusText = "";
        }
      },

      _csrfToken() {
        // First try the form input inside our component (most reliable on page load)
        const input = this.$el.querySelector("[name=csrfmiddlewaretoken]");
        if (input instanceof HTMLInputElement && input.value) {
          return input.value;
        }
        // Fallback: any other csrf input on the page (e.g. logout form in header)
        const anyInput = document.querySelector("[name=csrfmiddlewaretoken]");
        if (anyInput instanceof HTMLInputElement && anyInput.value) {
          return anyInput.value;
        }
        // Last resort: read the csrftoken cookie directly
        const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : "";
      },

      _revokeObjectUrl() {
        if (this._objectUrl) {
          URL.revokeObjectURL(this._objectUrl);
          this._objectUrl = null;
        }
      },

      destroy() {
        this._revokeObjectUrl();
      },
    }));

    /**
     * thumbnailPreload — primes the browser cache with kassabok thumbnails
     * when the user hovers/focuses the Kassabok tile on the overview.
     *
     * Reads URLs from <span data-url="…"> children inside x-ref="preloadData"
     * and injects <link rel="preload" as="image"> into the document head.
     *
     * Runs at most once per page (the .once modifier on @mouseenter / @focus
     * is belt-and-suspenders to the internal `done` flag).
     */
    Alpine.data("thumbnailPreload", () => ({
      done: false,

      preload() {
        if (this.done) return;
        this.done = true;

        const root = this.$refs.preloadData;
        if (!(root instanceof HTMLElement)) return;

        const urls = Array.from(root.querySelectorAll("[data-url]"))
          .map((el) => el.getAttribute("data-url"))
          .filter((url) => typeof url === "string" && url.length > 0);

        if (urls.length === 0) return;

        const frag = document.createDocumentFragment();
        for (const url of urls) {
          const link = document.createElement("link");
          link.rel = "preload";
          link.as = "image";
          link.href = url;
          // Hint to the browser: don't compete with critical resources
          link.setAttribute("fetchpriority", "low");
          frag.appendChild(link);
        }
        document.head.appendChild(frag);
      },
    }));

    /**
     * taxYearHint — derives the inkomstår + declaration year from the date
     * input and updates the pedagogical hint card.
     *
     * Initialised from server-side rendered value (works on page load before
     * user touches the date) and updates live as user edits the date field.
     */
    Alpine.data("taxYearHint", () => ({
      incomeYear: null,
      declarationYear: null,

      updateFromDate(rawDate) {
        if (rawDate === null) return; // event fired from a non-date input

        const match = /^(\d{4})-\d{2}-\d{2}$/.exec(String(rawDate || ""));
        if (!match) {
          this.incomeYear = null;
          this.declarationYear = null;
          return;
        }
        const year = parseInt(match[1], 10);
        if (!Number.isFinite(year) || year < 1900 || year > 2100) {
          this.incomeYear = null;
          this.declarationYear = null;
          return;
        }
        this.incomeYear = year;
        this.declarationYear = year + 1;
      },
    }));

    /**
     * netRecalc — keeps the read-only "Netto" field in sync with total - vat
     * as the user edits the amounts in the review form.
     */
    Alpine.data("netRecalc", (config) => ({
      net: config && config.initial ? config.initial : "",

      init() {
        const root = this.$el;
        const totalInput = root.querySelector("#total_amount");
        const vatInput = root.querySelector("#vat_amount");
        const netDisplay = root.querySelector("#net_amount_preview");

        const recalc = () => {
          if (!netDisplay) return;
          const parse = (el) => {
            if (!(el instanceof HTMLInputElement)) return null;
            const s = el.value.replace(",", ".").trim();
            if (!s) return null;
            const n = Number(s);
            return Number.isFinite(n) ? n : null;
          };
          const total = parse(totalInput);
          if (total === null) {
            netDisplay.value = "";
            return;
          }
          const vat = parse(vatInput) ?? 0;
          netDisplay.value = (total - vat).toFixed(2);
        };

        if (totalInput) totalInput.addEventListener("input", recalc);
        if (vatInput) vatInput.addEventListener("input", recalc);
      },
    }));
  });

  // ---------------------------------------------------------------------------
  // Global helpers (used from inline @click handlers in correction suggestions)
  // ---------------------------------------------------------------------------

  /**
   * Apply an OCR correction suggestion into the scan-review form.
   * Called from correction_suggestion.html via Alpine @click.
   */
  window.applyCorrection = function (suggestion) {
    if (!suggestion || typeof suggestion !== "object") {
      return;
    }

    if (suggestion.totalAmount) {
      const amountInput = document.getElementById("total_amount");
      if (amountInput instanceof HTMLInputElement) {
        amountInput.value = suggestion.totalAmount;
      }
    }

    if (suggestion.category) {
      const categoryInput = document.getElementById("category");
      if (categoryInput instanceof HTMLInputElement) {
        categoryInput.value = suggestion.category;
      }
    }
  };
})();