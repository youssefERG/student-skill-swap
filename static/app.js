"use strict";

document.addEventListener("submit", (event) => {
  const button = event.submitter;
  const confirmation = button?.dataset.confirm;

  if (confirmation && !window.confirm(confirmation)) {
    event.preventDefault();
  }
});