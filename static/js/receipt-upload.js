document.addEventListener("click", (event) => {
  const trigger = event.target.closest("[data-upload-trigger]");

  if (!trigger) {
    return;
  }

  const wrapper = trigger.closest("[data-receipt-upload]");
  const input = wrapper?.querySelector("[data-receipt-file]");

  if (input) {
    input.click();
  }
});

document.addEventListener("change", (event) => {
  const input = event.target;

  if (!input.matches("[data-receipt-file]")) {
    return;
  }

  const file = input.files?.[0];
  const wrapper = input.closest("[data-receipt-upload]");
  const emptyState = wrapper?.querySelector("[data-upload-empty]");
  const previewWrap = wrapper?.querySelector("[data-upload-preview-wrap]");
  const preview = wrapper?.querySelector("[data-receipt-preview]");
  const fileName = wrapper?.querySelector("[data-file-name]");

  if (!file || !preview || !previewWrap) {
    return;
  }

  if (preview.dataset.objectUrl) {
    URL.revokeObjectURL(preview.dataset.objectUrl);
  }

  const objectUrl = URL.createObjectURL(file);
  preview.src = objectUrl;
  preview.dataset.objectUrl = objectUrl;

  if (fileName) {
    fileName.textContent = file.name;
  }

  if (emptyState) {
    emptyState.classList.add("hidden");
  }

  previewWrap.classList.remove("hidden");
});
