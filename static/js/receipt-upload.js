document.addEventListener("click", (event) => {
  const target = event.target;

  if (!(target instanceof Element)) {
    return;
  }

  const trigger = target.closest("[data-upload-trigger]");

  if (!(trigger instanceof HTMLElement)) {
    return;
  }

  const wrapper = trigger.closest("[data-receipt-upload]");
  const input = wrapper?.querySelector("[data-receipt-file]");

  if (input instanceof HTMLInputElement) {
    input.click();
  }
});

document.addEventListener("change", (event) => {
  const target = event.target;

  if (!(target instanceof HTMLInputElement) || !target.matches("[data-receipt-file]")) {
    return;
  }

  const file = target.files?.[0];
  const wrapper = target.closest("[data-receipt-upload]");
  const emptyState = wrapper?.querySelector("[data-upload-empty]");
  const previewWrap = wrapper?.querySelector("[data-upload-preview-wrap]");
  const preview = wrapper?.querySelector("[data-receipt-preview]");
  const fileName = wrapper?.querySelector("[data-file-name]");

  if (
    !file ||
    !(emptyState instanceof HTMLElement) ||
    !(previewWrap instanceof HTMLElement) ||
    !(preview instanceof HTMLImageElement)
  ) {
    return;
  }

  if (preview.dataset.objectUrl) {
    URL.revokeObjectURL(preview.dataset.objectUrl);
  }

  const objectUrl = URL.createObjectURL(file);
  preview.src = objectUrl;
  preview.dataset.objectUrl = objectUrl;

  if (fileName instanceof HTMLElement) {
    fileName.textContent = file.name;
  }

  emptyState.classList.add("hidden");
  previewWrap.classList.remove("hidden");
});