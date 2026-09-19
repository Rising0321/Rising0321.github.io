(function () {
  var opener = null;

  function closeLightbox() {
    var target = document.querySelector('.lightbox-target.is-open, .lightbox-target:target:not(.is-closed)');
    if (!target) return;
    target.classList.remove('is-open');
    target.classList.add('is-closed');
    if (location.hash === '#' + target.id) {
      history.replaceState(history.state, '', location.pathname + location.search);
    }
    if (opener) opener.focus({ preventScroll: true });
    opener = null;
  }

  // Delegation also covers talk thumbnails added after the data fetch.
  document.addEventListener('click', function (event) {
    var link = event.target.closest('a');
    if (!link || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    if (link.classList.contains('lightbox-close')) {
      event.preventDefault();
      closeLightbox();
      return;
    }
    var href = link.getAttribute('href');
    if (!href || href.indexOf('#lb-') !== 0) return;
    var target = document.getElementById(href.slice(1));
    if (!target || !target.classList.contains('lightbox-target')) return;
    event.preventDefault();
    opener = link;
    target.classList.remove('is-closed');
    target.classList.add('is-open');
    target.querySelector('.lightbox-close').focus({ preventScroll: true });
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') {
      event.preventDefault();
      closeLightbox();
    }
  });
})();
