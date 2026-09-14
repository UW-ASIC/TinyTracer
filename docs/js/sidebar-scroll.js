/* Keep the left navigation column still when moving between pages.
 *
 * The readthedocs theme calls scrollIntoView() on the current page's sidebar
 * entry at every page load, which drags the entry you just clicked to the top
 * of the column. This script instead puts the clicked entry back at the same
 * height it had inside the column before the click. That also absorbs the
 * headings the theme expands under the current page and collapses when you
 * leave it. When a page is reached some other way (a link in the text, the
 * previous/next buttons), the column's scroll offset is restored instead.
 * Clicking a section heading of the current page (hash change) leaves the
 * column alone. If nothing has been remembered yet (first page of a session
 * opened directly), the theme's behaviour is left as is.
 */
(function () {
  var KEY = 'tinytracer-docs-sidebar';
  var pendingLinkY = null;

  function sidebar() { return document.querySelector('.wy-side-scroll'); }
  function load() { try { return JSON.parse(sessionStorage.getItem(KEY)); } catch (e) { return null; } }
  function save(o) { try { sessionStorage.setItem(KEY, JSON.stringify(o)); } catch (e) {} }

  // A plain left click on a sidebar page link: note where that link sits in the column.
  document.addEventListener('click', function (ev) {
    var s = sidebar();
    var a = ev.target && ev.target.closest ? ev.target.closest('.wy-menu-vertical a[href]') : null;
    if (!s || !a || ev.button !== 0 || ev.ctrlKey || ev.metaKey || ev.shiftKey) return;
    if (a.getAttribute('href').charAt(0) === '#') return;   // same-page heading, no reload
    pendingLinkY = a.getBoundingClientRect().top - s.getBoundingClientRect().top;
  }, true);

  window.addEventListener('pagehide', function () {
    var s = sidebar();
    if (!s) return;
    save({ top: s.scrollTop, linkY: pendingLinkY });
    pendingLinkY = null;
  });

  var nav = window.SphinxRtdTheme && window.SphinxRtdTheme.Navigation;
  if (!nav || typeof nav.reset !== 'function') return;

  var themeReset = nav.reset;
  var firstRun = true;

  nav.reset = function () {
    var s = sidebar();
    var before = s ? s.scrollTop : 0;
    themeReset.apply(this, arguments);       // marks the current entry, then scrollIntoView()
    if (!s) return;
    if (!firstRun) { s.scrollTop = before; return; }   // hash change: leave the column alone
    firstRun = false;

    var o = load();
    if (!o) {                                // nothing remembered: keep the theme's behaviour,
      var head = s.querySelector('.wy-side-nav-search');   // but don't hide the entry under the
      if (head && s.scrollTop > 0) {                        // sticky title/search block
        s.scrollTop = Math.max(0, s.scrollTop - head.offsetHeight - parseFloat(getComputedStyle(head).marginBottom));
      }
      return;
    }
    var cur = s.querySelector('.wy-menu-vertical a[href="#"]');
    if (cur && typeof o.linkY === 'number') {
      var posInColumn = cur.getBoundingClientRect().top - s.getBoundingClientRect().top + s.scrollTop;
      s.scrollTop = posInColumn - o.linkY;   // clicked entry back where it was
    } else if (typeof o.top === 'number') {
      s.scrollTop = o.top;                   // reached another way: same offset as before
    }
  };
})();
