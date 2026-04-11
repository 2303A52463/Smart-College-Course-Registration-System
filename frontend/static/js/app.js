const flashes = document.querySelectorAll('.flash');

flashes.forEach((flash, index) => {
  setTimeout(() => {
    flash.style.transition = 'opacity 0.35s ease';
    flash.style.opacity = '0.96';
  }, 80 * index);

  setTimeout(() => {
    flash.style.opacity = '0';
    setTimeout(() => flash.remove(), 350);
  }, 5200 + index * 300);
});
