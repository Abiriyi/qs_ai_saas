document.addEventListener('DOMContentLoaded', () => {
  const yearTarget = document.getElementById('year');
  if (yearTarget) {
    yearTarget.textContent = new Date().getFullYear();
  }
});
