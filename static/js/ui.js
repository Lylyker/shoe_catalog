/* Плотность интерфейса, зум-устойчивость, обёртки таблиц. */
(function () {
  'use strict';
  var KEY = 'shoe.ui.v1';
  var defaults = { density: 'auto', rows: 'normal', sticky: 'on', contrast: 'normal', motion: 'on', sidebar: 'on' };
  var state = Object.assign({}, defaults);
  try { Object.assign(state, JSON.parse(localStorage.getItem(KEY) || '{}')); } catch (e) {}

  function save() { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {} }

  function autoScale() {
    var w = window.innerWidth;
    if (w < 520) return 0.8;
    if (w < 760) return 0.875;
    if (w < 1024) return 0.94;
    return 1;
  }

  function apply() {
    var scale = state.density === 'auto' ? autoScale()
      : state.density === 'compact' ? 0.85
      : state.density === 'large' ? 1.15 : 1;
    document.documentElement.style.setProperty('--ui-scale', String(scale));
    document.body.dataset.rows = state.rows;
    document.body.dataset.sticky = state.sticky;
    document.body.dataset.contrast = state.contrast;
    document.body.dataset.motion = state.motion;
    document.body.dataset.sidebar = state.sidebar;
    document.querySelectorAll('[data-density]').forEach(function (b) {
      b.setAttribute('aria-pressed', String(b.dataset.density === state.density));
    });
    document.querySelectorAll('[data-ui]').forEach(function (el) {
      var k = el.dataset.ui;
      if (el.type === 'checkbox') el.checked = state[k] === 'on';
      else el.value = state[k];
    });
    var out = document.getElementById('scale-value');
    if (out) out.textContent = Math.round(scale * 100) + '%';
  }

  /* Ни один блок с фиксированной шириной не вылезает за контейнер. */
  function guardWidths() {
    document.querySelectorAll('[style]').forEach(function (el) {
      var w = el.style.width;
      if (!w || w.indexOf('px') === -1) return;
      var n = parseFloat(w);
      if (!isFinite(n) || n <= 0) return;
      el.style.width = 'min(' + n + 'px, 100%)';
      el.style.maxWidth = '100%';
      el.style.minWidth = '0';
    });
    document.querySelectorAll('[style*="height"]').forEach(function (el) {
      if (el.tagName === 'IMG' || el.tagName === 'SVG') return;
      var h = parseFloat(el.style.height);
      if (isFinite(h) && h > 200 && el.style.height.indexOf('px') !== -1) {
        el.style.height = 'auto';
        el.style.minHeight = 'min(' + h + 'px, 60vh)';
      }
    });
  }

  /* Каждая таблица получает собственный горизонтальный скролл. */
  function wrapTables() {
    document.querySelectorAll('table').forEach(function (t) {
      var p = t.parentElement;
      if (p && p.classList.contains('table-wrap')) return;
      var box = document.createElement('div');
      box.className = 'table-wrap';
      t.parentNode.insertBefore(box, t);
      box.appendChild(t);
      t.classList.add('tbl');
    });
  }

  function toast(msg) {
    var host = document.querySelector('.toast-host');
    if (!host) { host = document.createElement('div'); host.className = 'toast-host'; document.body.appendChild(host); }
    var el = document.createElement('div');
    el.className = 'toast'; el.textContent = msg;
    host.appendChild(el);
    setTimeout(function () { el.remove(); }, 2400);
  }

  function bind() {
    document.querySelectorAll('[data-density]').forEach(function (b) {
      b.addEventListener('click', function () {
        state.density = b.dataset.density; save(); apply();
        toast('Плотность: ' + b.textContent.trim());
      });
    });
    document.querySelectorAll('[data-ui]').forEach(function (el) {
      var k = el.dataset.ui;
      el.addEventListener('change', function () {
        state[k] = el.type === 'checkbox' ? (el.checked ? 'on' : 'off') : el.value;
        save(); apply();
      });
    });
    var reset = document.getElementById('ui-reset');
    if (reset) reset.addEventListener('click', function () {
      state = Object.assign({}, defaults); save(); apply(); toast('Настройки вида сброшены');
    });
    document.querySelectorAll('form[data-confirm]').forEach(function (f) {
      f.addEventListener('submit', function (e) {
        if (!window.confirm(f.dataset.confirm)) e.preventDefault();
      });
    });
    var all = document.getElementById('check-all');
    if (all) all.addEventListener('change', function () {
      document.querySelectorAll('input[name="ids"]').forEach(function (c) { c.checked = all.checked; });
    });
  }

  function boot() {
    guardWidths(); wrapTables(); apply(); bind();
    var nav = document.getElementById('nav-page-name');
    if (nav && !nav.textContent.trim()) nav.textContent = document.title;
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();

  var t;
  window.addEventListener('resize', function () {
    clearTimeout(t);
    t = setTimeout(function () { if (state.density === 'auto') apply(); }, 140);
  });
})();