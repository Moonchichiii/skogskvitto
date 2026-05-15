document.addEventListener("click", (event) => {
  const dismissButton = event.target.closest("[data-dismiss-parent]");

  if (dismissButton) {
    dismissButton.closest("[data-dismissible]")?.remove();
    return;
  }

  const applyButton = event.target.closest("[data-apply-correction]");

  if (!applyButton) {
    return;
  }

  const totalAmount = applyButton.dataset.totalAmount;
  const category = applyButton.dataset.category;

  if (totalAmount) {
    const amountInput = document.getElementById("total_amount");
    if (amountInput) {
      amountInput.value = totalAmount;
    }
  }

  if (category) {
    const categoryInput = document.getElementById("category");
    if (categoryInput) {
      categoryInput.value = category;
    }
  }
});
