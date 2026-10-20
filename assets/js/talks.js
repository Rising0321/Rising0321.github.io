(function () {
  function element(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
  }

  function formatCount(value) {
    if (!Number.isFinite(value) || value < 0) return '暂不可用 / Unavailable';
    return value.toLocaleString('en-US');
  }

  fetch('data/talks.json')
    .then(function (response) {
      if (!response.ok) throw new Error('Cannot load talks');
      return response.json();
    })
    .then(function (talks) {
      var list = document.getElementById('talk-list');
      if (!list || !Array.isArray(talks)) return;
      talks.forEach(function (talk, i) {
        var card = element('article', 'talk-card');
        var thumbnail = element('div', 'talk-thumb');
        var zoom = element('a');
        zoom.href = '#lb-talk-' + i;
        var image = element('img');
        image.src = talk.thumb;
        image.alt = talk.title;
        image.loading = 'lazy';
        zoom.appendChild(image);
        thumbnail.appendChild(zoom);
        card.appendChild(thumbnail);
        var body = element('div', 'talk-body');
        var heading = element('h3');
        var link = element('a', '', talk.title);
        link.href = talk.url;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        heading.appendChild(link);
        body.appendChild(heading);
        if (talk.title_en) {
          var translation = element('p', 'talk-title-en', talk.title_en);
          translation.lang = 'en';
          body.appendChild(translation);
        }
        var meta = element('div', 'talk-meta');
        [['views', '播放 / Views'], ['likes', '点赞 / Likes'], ['favorites', '收藏 / Favorites']].forEach(function (metric) {
          var stat = element('span', 'talk-views', metric[1] + ' ' + formatCount(talk[metric[0]]));
          var timestamp = metric[0] === 'views' ? talk.views_updated_at : talk.engagement_updated_at;
          if (timestamp) stat.title = '更新于 / Updated: ' + new Date(timestamp).toLocaleString();
          meta.appendChild(stat);
        });
        body.appendChild(meta);
        if (talk.stats_status === 'stale' || talk.stats_status === 'partial') {
          body.appendChild(element('p', 'talk-note',
            talk.stats_status === 'stale' ? '统计暂未同步 / Statistics unavailable; showing previously saved counts.' :
              '点赞和收藏暂未同步 / Views updated; likes and favorites show previously saved counts.'));
        }
        card.appendChild(body);
        list.appendChild(card);
        var lightbox = element('div', 'lightbox-target');
        lightbox.id = 'lb-talk-' + i;
        var close = element('a', 'lightbox-close', 'close');
        close.href = '#';
        lightbox.appendChild(close);
        var fullImage = element('img');
        fullImage.src = talk.thumb;
        fullImage.alt = talk.title;
        lightbox.appendChild(fullImage);
        document.body.appendChild(lightbox);
      });
    })
    .catch(function () {
      document.getElementById('talk-list').textContent = '暂时无法加载视频列表，请稍后刷新。 / Unable to load talks. Please try refreshing.';
    });
})();
