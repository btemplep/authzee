/**
 * Docs page behavior: highlight the "On this page" TOC entry for the section
 * currently in view (scrollspy). Plain browser JS, no dependencies.
 */
(function () {
  "use strict";

  var tocLinks = Array.prototype.slice.call(
    document.querySelectorAll(".toc a")
  );

  addCopyButtons();

  if (tocLinks.length === 0) {
    return;
  }

  var linkById = {};
  var headings = [];

  tocLinks.forEach(function (link) {
    var id = decodeURIComponent(link.getAttribute("href").slice(1));
    var heading = document.getElementById(id);
    if (heading) {
      linkById[id] = link;
      headings.push(heading);
    }
  });

  function clearActive() {
    tocLinks.forEach(function (link) {
      link.classList.remove("active");
    });
  }

  function setActive(id) {
    if (!id || !linkById[id]) {
      return;
    }

    clearActive();
    linkById[id].classList.add("active");
  }

  if ("IntersectionObserver" in window) {
    var visible = {};
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          visible[entry.target.id] = entry.isIntersecting;
        });

        // Pick the first heading (document order) currently visible.
        for (var i = 0; i < headings.length; i++) {
          if (visible[headings[i].id]) {
            setActive(headings[i].id);
            return;
          }
        }
      },
      {
        rootMargin: "-72px 0px -70% 0px",
        threshold: 0
      }
    );

    headings.forEach(function (heading) {
      observer.observe(heading);
    });
  }

  // Reflect the clicked entry immediately.
  tocLinks.forEach(function (link) {
    link.addEventListener("click", function () {
      var id = decodeURIComponent(link.getAttribute("href").slice(1));
      setActive(id);
    });
  });
})();

/**
 * Add a "Copy" button to every code block in the docs content. Each <pre> is
 * wrapped so the button can be positioned in its top-right corner. Clicking
 * copies the code block's text to the clipboard.
 */
function addCopyButtons() {
  "use strict";

  var blocks = Array.prototype.slice.call(
    document.querySelectorAll(".markdown-body pre")
  );

  blocks.forEach(function (pre) {
    var wrapper = document.createElement("div");
    wrapper.className = "code-wrapper";
    pre.parentNode.insertBefore(wrapper, pre);
    wrapper.appendChild(pre);

    var button = document.createElement("button");
    button.type = "button";
    button.className = "copy-btn";
    button.textContent = "Copy";
    button.setAttribute("aria-label", "Copy code to clipboard");
    wrapper.appendChild(button);

    var resetTimer = null;

    button.addEventListener("click", function () {
      var codeEl = pre.querySelector("code");
      var text = codeEl ? codeEl.innerText : pre.innerText;

      copyText(text).then(
        function () {
          showState("Copied");
        },
        function () {
          showState("Failed");
        }
      );
    });

    function showState(label) {
      button.textContent = label;
      button.classList.add("copied");
      if (resetTimer) {
        clearTimeout(resetTimer);
      }

      resetTimer = setTimeout(function () {
        button.textContent = "Copy";
        button.classList.remove("copied");
      }, 1600);
    }
  });
}

/** Copy text using the async Clipboard API, with a legacy fallback. */
function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    return navigator.clipboard.writeText(text);
  }

  return new Promise(function (resolve, reject) {
    var area = document.createElement("textarea");
    area.value = text;
    area.style.position = "fixed";
    area.style.top = "-9999px";
    document.body.appendChild(area);
    area.focus();
    area.select();
    try {
      var ok = document.execCommand("copy");
      document.body.removeChild(area);
      if (ok) {
        resolve();
      } else {
        reject(new Error("copy command failed"));
      }
    } catch (err) {
      document.body.removeChild(area);
      reject(err);
    }
  });
}
