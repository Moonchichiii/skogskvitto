document.addEventListener("click", (event) => {
  const target = event.target;

  if (!(target instanceof Element)) {
    return;
  }

  const dismissButton = target.closest("[data-dismiss-parent]");

  if (dismissButton instanceof HTMLElement) {
    dismissButton.closest("[data-dismissible]")?.remove();
    return;
  }

  const applyButton = target.closest("[data-apply-correction]");

  if (!(applyButton instanceof HTMLElement)) {
    return;
  }

  const totalAmount = applyButton.dataset.totalAmount;
  const category = applyButton.dataset.category;

  if (totalAmount) {
    const amountInput = document.getElementById("total_amount");
    if (amountInput instanceof HTMLInputElement) {
      amountInput.value = totalAmount;
    }
  }

  if (category) {
    const categoryInput = document.getElementById("category");
    if (categoryInput instanceof HTMLInputElement) {
      categoryInput.value = category;
    }
  }
});