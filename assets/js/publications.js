(function () {
  var section = document.getElementById('two');
  var filters = section.querySelector('.publication-filters');
  var papers = Array.from(section.querySelectorAll('.paper-card'));
  var status = section.querySelector('.publication-count');
  var buttons = Array.from(filters.querySelectorAll('button'));

  function matches(paper, category) {
    return category === 'all' || paper.dataset.categories.split(' ').includes(category);
  }

  buttons.forEach(function (button) {
    var count = papers.filter(function (paper) {
      return matches(paper, button.dataset.filter);
    }).length;
    button.querySelector('.filter-count').textContent = count;
  });

  filters.addEventListener('click', function (event) {
    var button = event.target.closest('button');
    if (!button || !filters.contains(button)) return;
    var count = 0;
    papers.forEach(function (paper) {
      paper.hidden = !matches(paper, button.dataset.filter);
      if (!paper.hidden) count++;
    });
    buttons.forEach(function (item) {
      item.setAttribute('aria-pressed', String(item === button));
    });
    status.textContent = count + ' of ' + papers.length + ' publications';
    window.dispatchEvent(new Event('scroll'));
  });

  status.textContent = papers.length + ' publications';
  filters.hidden = false;
})();
