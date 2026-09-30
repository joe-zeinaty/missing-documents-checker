"use strict";

// Connect each copy button to its own subject and body fields.
document.querySelectorAll(".copy-reminder").forEach((button) => {
  button.addEventListener("click", async () => {
    const subject = document.getElementById(button.dataset.subjectId);
    const body = document.getElementById(button.dataset.bodyId);
    const feedback = button.parentElement.querySelector(".copy-feedback");

    // Copy the full draft together so the advisor can paste it elsewhere.
    const draft = `Subject: ${subject.value}\n\n${body.value}`;

    try {
      // Clipboard access works on HTTPS sites and supported localhost
      // browsers. It may still be denied by browser permissions.
      await navigator.clipboard.writeText(draft);
      feedback.textContent = "Reminder copied.";
    } catch {
      // Keep the existing selectable fields as a manual alternative.
      feedback.textContent =
        "Could not copy automatically. Select and copy the text above.";
    }
  });
});
