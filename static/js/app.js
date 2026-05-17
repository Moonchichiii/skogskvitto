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
     * receiptUpload — handles file selection in the scan upload form.
     * Reveals an image preview and the captured file name.
     */
    Alpine.data("receiptUpload", () => ({
      previewUrl: "",
      fileName: "",
      _objectUrl: null,

      onFileChange(event) {
        const target = event.target;
        if (!(target instanceof HTMLInputElement)) {
          return;
        }
        const file = target.files && target.files[0];
        if (!file) {
          return;
        }
        this._revokeObjectUrl();
        const url = URL.createObjectURL(file);
        this._objectUrl = url;
        this.previewUrl = url;
        this.fileName = file.name;
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