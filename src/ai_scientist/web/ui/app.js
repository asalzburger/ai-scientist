"use strict";
// Keep the access token in page memory, not persistent browser storage or request URLs.
const token = location.hash.slice(1);
history.replaceState(null, "", "/");
const items = document.getElementById("items");
const status = document.getElementById("status");
let currentRequest = 0;
async function load(view, label) {
  const request = ++currentRequest;
  document.getElementById("heading").textContent = label;
  items.replaceChildren();
  status.textContent = "Loading…";
  try {
    const response = await fetch(`/api/${view}`, {headers: {Authorization: `Bearer ${token}`}});
    if (!response.ok) throw new Error("Reopen the full workspace link printed in the terminal.");
    const records = await response.json();
    if (request !== currentRequest) return;
    status.textContent = records.length ? `${records.length} records` : "Nothing here yet.";
    for (const record of records) {
      const article = document.createElement("article");
      const title = document.createElement("h3");
      title.textContent = record.subject || record.title || record.name || record.action || record.id;
      const content = document.createElement("pre");
      // Untrusted email/calendar data is always text, never HTML.
      content.textContent = JSON.stringify(record, null, 2);
      article.append(title, content);
      items.append(article);
    }
  } catch (error) {
    if (request === currentRequest) status.textContent = error.message;
  }
}
document.querySelectorAll("button[data-view]").forEach(button => {
  button.addEventListener("click", () => load(button.dataset.view, button.textContent));
});
load("drafts", "Email drafts");
