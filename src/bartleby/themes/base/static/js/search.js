/*
 * Bartleby search engine. Theme-neutral: fetches /search/search_index.json on
 * first use, queries it with lunr, and (with search.highlight on) marks matched
 * terms using DOM text nodes, never by assigning HTML strings.
 *
 * Loaded by base.html with `defer` ahead of Alpine when the `search` feature is
 * on. base.html sets data-highlight="true" on this script tag when the
 * `search.highlight` feature is on; this file reads it from document.currentScript.
 *
 * Public API: registers the Alpine component `bartlebySearch`. A theme's modal
 * markup binds to it with x-data="bartlebySearch()" and may use:
 *   state:    open (bool), query (string, bind with x-model), results (list of
 *             {title, snippet, href}), failed (bool), loading (bool)
 *   methods:  show() opens and loads the index, close() closes and refocuses the
 *             trigger, search() runs the query (call on input), go() follows the
 *             first result, status() returns a message for a live region,
 *             mark(element, text) fills element with text, wrapping query terms
 *             in <mark class="search-hit"> when highlighting is on
 *   refs:     x-ref="trigger" (the opening button) and x-ref="input" (the field)
 * The theme owns every class name and all presentation.
 */
(function () {
  var script = document.currentScript;
  var highlightEnabled = script !== null && script.dataset.highlight === "true";
  var index = null;
  var docs = [];

  function termsOf(text) {
    return text.toLowerCase().split(/[^\p{L}\p{N}]+/u).filter(Boolean);
  }

  function patternOf(terms) {
    var escaped = terms
      .slice()
      .sort(function (left, right) { return right.length - left.length; })
      .map(function (term) { return term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); });
    return escaped.length ? new RegExp(escaped.join("|"), "giu") : null;
  }

  // Split text into plain and matched pieces; callers turn the pieces into nodes.
  function pieces(text, pattern) {
    var result = [];
    var cursor = 0;
    if (pattern) {
      pattern.lastIndex = 0;
      var match;
      while ((match = pattern.exec(text)) !== null) {
        if (match[0] === "") { pattern.lastIndex += 1; continue; }
        if (match.index > cursor) { result.push({ text: text.slice(cursor, match.index), hit: false }); }
        result.push({ text: match[0], hit: true });
        cursor = match.index + match[0].length;
      }
    }
    if (cursor < text.length) { result.push({ text: text.slice(cursor), hit: false }); }
    return result;
  }

  function fragmentOf(text, pattern) {
    var fragment = document.createDocumentFragment();
    pieces(text, pattern).forEach(function (piece) {
      if (piece.hit) {
        var mark = document.createElement("mark");
        mark.className = "search-hit";
        mark.textContent = piece.text;
        fragment.appendChild(mark);
      } else {
        fragment.appendChild(document.createTextNode(piece.text));
      }
    });
    return fragment;
  }

  function markPage(terms) {
    var root = document.querySelector("main");
    var pattern = patternOf(terms);
    if (!root || !pattern) { return; }
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    var nodes = [];
    while (walker.nextNode()) {
      var parent = walker.currentNode.parentElement;
      if (parent && !parent.closest("script, style, textarea, mark")) { nodes.push(walker.currentNode); }
    }
    nodes.forEach(function (node) {
      var text = node.nodeValue || "";
      pattern.lastIndex = 0;
      if (pattern.test(text)) { node.replaceWith(fragmentOf(text, pattern)); }
    });
  }

  if (highlightEnabled) {
    document.addEventListener("DOMContentLoaded", function () {
      var carried = new URLSearchParams(window.location.search).get("h");
      if (carried) { markPage(termsOf(carried)); }
    });
  }

  document.addEventListener("alpine:init", function () {
    Alpine.data("bartlebySearch", function () {
      return {
        open: false,
        query: "",
        results: [],
        failed: false,
        loading: false,
        show: function () {
          this.open = true;
          this.load();
          this.$nextTick(function () { this.$refs.input.focus(); }.bind(this));
        },
        close: function () {
          this.open = false;
          this.$refs.trigger.focus();
        },
        load: function () {
          if (index || this.loading) { return Promise.resolve(); }
          this.loading = true;
          var component = this;
          return fetch("/search/search_index.json")
            .then(function (response) {
              if (!response.ok) { throw new Error("search index " + response.status); }
              return response.json();
            })
            .then(function (payload) {
              docs = payload.docs;
              index = lunr(function () {
                this.ref("id");
                this.field("title", { boost: 10 });
                this.field("tags", { boost: 5 });
                this.field("text");
                docs.forEach(function (doc, position) {
                  this.add({ id: String(position), title: doc.title, tags: (doc.tags || []).join(" "), text: doc.text });
                }, this);
              });
              component.failed = false;
              if (component.query) { component.search(); }
            })
            .catch(function () { component.failed = true; component.loading = false; });
        },
        search: function () {
          var terms = termsOf(this.query);
          if (!terms.length || !index) { this.results = []; return; }
          var pattern = patternOf(terms);
          var hits = index.query(function (query) {
            terms.forEach(function (term) {
              query.term(term, { wildcard: lunr.Query.wildcard.TRAILING, presence: lunr.Query.presence.REQUIRED });
            });
          });
          this.results = hits.slice(0, 10).map(function (hit) {
            var doc = docs[Number(hit.ref)];
            var lowered = doc.text.toLowerCase();
            var first = terms.reduce(function (best, term) {
              var found = lowered.indexOf(term);
              return found >= 0 && (best < 0 || found < best) ? found : best;
            }, -1);
            var start = Math.max(0, first - 60);
            var snippet = first < 0 ? doc.text.slice(0, 140) : doc.text.slice(start, start + 160);
            var parts = doc.location.split("#");
            var carried = highlightEnabled ? "?h=" + encodeURIComponent(terms.join(" ")) : "";
            return {
              title: doc.title,
              snippet: (start > 0 ? "..." : "") + snippet + (doc.text.length > start + 160 ? "..." : ""),
              href: parts[0] + carried + (parts.length > 1 ? "#" + parts[1] : "")
            };
          });
        },
        go: function () {
          if (this.results.length) { window.location.href = this.results[0].href; }
        },
        status: function () {
          if (this.failed) { return "Search is unavailable. Reload the page to try again."; }
          if (!termsOf(this.query).length) { return ""; }
          if (!this.results.length) { return "No results for \"" + this.query + "\""; }
          return this.results.length + (this.results.length === 1 ? " result" : " results");
        },
        mark: function (element, text) {
          element.replaceChildren(highlightEnabled ? fragmentOf(text, patternOf(termsOf(this.query))) : document.createTextNode(text));
        }
      };
    });
  });
})();
