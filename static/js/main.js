// Small helpers for the AUSM Lab site: phone menu, filters, alumni tabs, hero dots.
(function () {
  // Phone menu
  var btn = document.querySelector('.menu-btn');
  var nav = document.getElementById('mainnav');
  if (btn && nav) {
    btn.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
      btn.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    });
  }

  // Filter chips (publications by type, gallery by category)
  document.querySelectorAll('[data-filter-scope]').forEach(function (scope) {
    var chips = scope.querySelectorAll('[data-filter]');
    chips.forEach(function (chip) {
      chip.addEventListener('click', function () {
        var value = chip.getAttribute('data-filter');
        chips.forEach(function (c) { c.setAttribute('aria-pressed', c === chip ? 'true' : 'false'); });
        scope.querySelectorAll('[data-type]').forEach(function (item) {
          item.hidden = !(value === 'all' || item.getAttribute('data-type') === value);
        });
        scope.querySelectorAll('[data-year-block]').forEach(function (block) {
          var visible = block.querySelectorAll('[data-type]:not([hidden])').length;
          var note = block.querySelector('.empty-note');
          if (note) note.hidden = visible > 0;
        });
      });
    });
  });

  // Alumni tabs
  document.querySelectorAll('[data-tabs]').forEach(function (box) {
    var tabs = Array.prototype.slice.call(box.querySelectorAll('[role="tab"]'));
    function select(tab) {
      tabs.forEach(function (t) {
        var on = t === tab;
        t.setAttribute('aria-selected', on ? 'true' : 'false');
        t.tabIndex = on ? 0 : -1;
        document.getElementById(t.getAttribute('aria-controls')).hidden = !on;
      });
    }
    tabs.forEach(function (t, i) {
      t.tabIndex = t.getAttribute('aria-selected') === 'true' ? 0 : -1;
      t.addEventListener('click', function () { select(t); });
      t.addEventListener('keydown', function (e) {
        var j = e.key === 'ArrowRight' ? i + 1 : e.key === 'ArrowLeft' ? i - 1 : null;
        if (j === null) return;
        var next = tabs[(j + tabs.length) % tabs.length];
        select(next); next.focus(); e.preventDefault();
      });
    });
  });

  // Point-cloud dots behind the home hero (skipped when a hero photo is set)
  var canvas = document.querySelector('.hero-dots');
  if (canvas && !canvas.parentElement.style.backgroundImage) {
    var draw = function () {
      var r = canvas.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
      canvas.width = r.width * dpr; canvas.height = r.height * dpr;
      var ctx = canvas.getContext('2d');
      ctx.scale(dpr, dpr); ctx.fillStyle = '#7c8ba8';
      var s = 11, rnd = function () { s = (s * 9301 + 49297) % 233280; return s / 233280; };
      var n = Math.round(r.width * 0.65);
      for (var i = 0; i < n; i++) {
        var x = rnd() * r.width, y = r.height / 2 + (rnd() - 0.5) * r.height * rnd();
        ctx.beginPath(); ctx.arc(x, y, 0.6 + rnd() * 1.6, 0, Math.PI * 2); ctx.fill();
      }
    };
    draw();
    var t; window.addEventListener('resize', function () { clearTimeout(t); t = setTimeout(draw, 150); });
  }

  // Home hero: rotate photos every 6 seconds (stops if the visitor prefers less motion)
  document.querySelectorAll('[data-slides]').forEach(function (hero) {
    var slides = hero.querySelectorAll('.hero-slide');
    var dots = hero.querySelectorAll('.hero-slide-dots button');
    if (slides.length < 2) return;
    var i = 0, timer = null;
    function show(n) {
      i = (n + slides.length) % slides.length;
      slides.forEach(function (s, k) { s.classList.toggle('is-on', k === i); });
      dots.forEach(function (d, k) { d.setAttribute('aria-pressed', k === i ? 'true' : 'false'); });
    }
    function start() {
      if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
      timer = setInterval(function () { show(i + 1); }, 6000);
    }
    dots.forEach(function (d, k) { d.addEventListener('click', function () { clearInterval(timer); show(k); start(); }); });
    start();
  });
})();

// Home "Research in Motion": swap the thumbnail for the YouTube player on click
document.querySelectorAll('.hv-play').forEach(function (b) {
  b.addEventListener('click', function () {
    if (b.dataset.src) {
      var v = document.createElement('video');
      v.src = b.dataset.src; v.controls = true; v.autoplay = true; v.muted = true; v.loop = true; v.playsInline = true;
      v.className = 'hv-frame';
      b.replaceWith(v); v.play && v.play();
      return;
    }
    var f = document.createElement('iframe');
    f.src = 'https://www.youtube-nocookie.com/embed/' + b.dataset.yt + '?autoplay=1&rel=0';
    f.title = b.getAttribute('aria-label');
    f.allow = 'autoplay; encrypted-media; picture-in-picture; fullscreen';
    f.allowFullscreen = true;
    f.className = 'hv-frame';
    b.replaceWith(f);
  });
});

// Visitor map (Contact page): colours each country by its number of visits.
(function () {
  var box = document.querySelector('[data-visitor-map]');
  if (!box) return;
  Promise.all([fetch(box.dataset.map).then(function (r) { return r.json(); }),
               fetch(box.dataset.stats).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; })])
    .then(function (res) {
      var map = res[0], st = res[1] || { countries: [], total: 0 };
      var counts = {}, max = 1;
      (st.countries || []).forEach(function (c) { counts[c.id] = c.count; if (c.count > max) max = c.count; });
      var svg = box.querySelector('.vm-svg'), tip = box.querySelector('.vm-tip'), ns = 'http://www.w3.org/2000/svg';
      svg.setAttribute('viewBox', map.viewBox);
      map.countries.forEach(function (c) {
        var p = document.createElementNS(ns, 'path'), n = counts[c.id] || 0;
        p.setAttribute('d', c.d);
        if (n) { p.setAttribute('class', 'vm-on'); p.style.fillOpacity = (0.25 + 0.75 * Math.log(1 + n) / Math.log(1 + max)).toFixed(2); }
        p.addEventListener('mousemove', function (e) {
          var r = box.querySelector('.vm-wrap').getBoundingClientRect();
          tip.hidden = false; tip.textContent = c.name + (n ? ' · ' + n.toLocaleString() + (n === 1 ? ' visit' : ' visits') : '');
          tip.style.left = (e.clientX - r.left + 12) + 'px'; tip.style.top = (e.clientY - r.top + 12) + 'px';
        });
        p.addEventListener('mouseleave', function () { tip.hidden = true; });
        svg.appendChild(p);
      });
      var nC = (st.countries || []).length;
      box.querySelector('.vm-summary').textContent = nC ? (st.total || 0).toLocaleString() + ' visits from ' + nC + (nC === 1 ? ' country' : ' countries') + ' since ' + (st.since || '') : 'Counting started recently.';
      var top = box.querySelector('.vm-top');
      (st.countries || []).slice().sort(function (a, b) { return b.count - a.count; }).slice(0, 8).forEach(function (c) {
        var li = document.createElement('li'); li.innerHTML = '<span></span><strong></strong>';
        li.firstChild.textContent = c.name; li.lastChild.textContent = c.count.toLocaleString(); top.appendChild(li);
      });
    });
})();
