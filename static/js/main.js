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
