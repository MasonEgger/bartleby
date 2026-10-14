// ABOUTME: Host script for markwright's click-to-load embeds: swaps a preview for its live markup on click.
// ABOUTME: Vanilla JS with one document listener (no Alpine), so it works before and without any component init.
//
// Contract: markwright preview markup, version 1 (docs/click-to-load.md in the markwright repo).
// A .mw-embed wrapper holds a template.mw-embed-content with the live markup and a
// button.mw-embed-load. On click the wrapper is replaced by a .mw-embed-live element
// holding a clone of the template, then the provider named by data-mw-embed renders it:
//   twitter    window.twttr.widgets.load(element)
//   instagram  window.instgrm.Embeds.process()
//   codepen    window.__CPEmbed()
//   youtube    nothing; the iframe loads itself
// data-mw-script names the provider script. Each script is injected once per page.
// An unknown data-mw-version is left alone, so a future markup change cannot half-work.
(function () {
  "use strict";

  var SUPPORTED_VERSION = "1";
  var scriptLoads = new Map();

  function render(embed, live) {
    if (embed === "twitter" && window.twttr && window.twttr.widgets) {
      window.twttr.widgets.load(live);
    } else if (embed === "instagram" && window.instgrm && window.instgrm.Embeds) {
      window.instgrm.Embeds.process();
    } else if (embed === "codepen" && typeof window.__CPEmbed === "function") {
      window.__CPEmbed();
    }
  }

  // Resolves once the provider script has loaded; a second embed of the same kind
  // reuses the first request, even while it is still in flight.
  function loadScript(src) {
    if (!scriptLoads.has(src)) {
      scriptLoads.set(
        src,
        new Promise(function (resolve) {
          var existing = document.querySelector('script[src="' + CSS.escape(src) + '"]');
          if (existing) {
            resolve();
            return;
          }
          var script = document.createElement("script");
          script.src = src;
          script.async = true;
          script.onload = resolve;
          document.body.append(script);
        })
      );
    }
    return scriptLoads.get(src);
  }

  document.addEventListener("click", function (event) {
    var button = event.target.closest(".mw-embed-load");
    if (!button) return;
    var wrapper = button.closest(".mw-embed");
    if (!wrapper || wrapper.dataset.mwVersion !== SUPPORTED_VERSION) return;
    var template = wrapper.querySelector("template.mw-embed-content");
    if (!template) return;

    var live = document.createElement("div");
    live.className = "mw-embed-live";
    live.tabIndex = -1;
    live.append(template.content.cloneNode(true));
    var embed = wrapper.dataset.mwEmbed;
    var src = wrapper.dataset.mwScript;
    wrapper.replaceWith(live);
    // The button is gone; keep keyboard focus on the embed instead of dropping it to <body>.
    live.focus({ preventScroll: true });

    if (src) {
      loadScript(src).then(function () {
        render(embed, live);
      });
    }
  });
})();
