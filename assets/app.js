/* ==========================================================================
   still — docs interactivity (self-contained, no dependencies)
   - lightweight syntax highlighter for C++ / Slint / GLSL / bash
   - copy buttons, heading anchors, auto "on this page" TOC, mobile nav,
     active-section tracking, active sidebar link
   Loaded as a classic <script> (not a module) on purpose: ES modules and
   fetch() are blocked over file://, so everything here runs from the tag.
   ========================================================================== */
(function () {
    "use strict";

    // ---- Syntax highlighter ------------------------------------------------
    // Code lives inside <figure class="code" data-lang=".." data-ref="..">
    //   <script type="text/plain"> ...raw code... </script>
    // Using a <script> element means the browser does NOT parse the code as
    // HTML, so we never have to escape <, >, & by hand in the source.

    function esc(s) {
        return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    var CPP_KW = "alignas|alignof|and|auto|break|case|catch|class|constexpr|const_cast|consteval|constinit|const|continue|decltype|default|delete|do|dynamic_cast|else|enum|explicit|export|extern|false|final|for|friend|goto|if|inline|mutable|namespace|new|noexcept|nullptr|operator|override|private|protected|public|register|reinterpret_cast|return|sizeof|static_assert|static_cast|static|struct|switch|template|this|thread_local|throw|true|try|typedef|typename|union|using|virtual|volatile|while";
    var CPP_TYPE = "bool|char|double|float|int|long|short|signed|unsigned|void|size_t|wchar_t|uint8_t|uint16_t|uint32_t|uint64_t|int8_t|int16_t|int32_t|int64_t|std|GLuint|GLint|GLenum|GLfloat|GLchar|GLboolean";

    var SLINT_KW = "import|from|export|component|inherits|struct|enum|global|property|callback|in|out|in-out|private|public|if|for|in|return|self|root|parent|animate|states|transitions|when";
    var SLINT_TYPE = "int|float|bool|string|color|brush|image|length|physical-length|duration|angle|percent|Window|Rectangle|Image|Text|TouchArea|VerticalBox|HorizontalBox|GridBox|VerticalLayout|HorizontalLayout";

    var GLSL_KW = "attribute|varying|uniform|in|out|inout|void|return|if|else|for|while|main|precision|highp|mediump|lowp|const";
    var GLSL_TYPE = "float|int|bool|vec2|vec3|vec4|mat2|mat3|mat4|sampler2D";
    var GLSL_FN = "clamp|mix|sin|cos|tan|abs|min|max|pow|length|normalize|dot|cross|floor|fract|mod|sqrt|texture|texture2D|gl_Position|gl_FragColor|gl_FragCoord";

    // Per-site extra tokens from site.toml [highlight.<lang>], injected as a
    // global before this script. Shape: { cpp: { type: [...], keyword: [...] } }.
    // words() appends them to the built-in vocab for that language + category.
    var EXTRA = window.stillHighlight || {};
    function escRe(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }
    function words(lang, cat, base) {
        var ex = (EXTRA[lang] && EXTRA[lang][cat]) || [];
        var all = ex.length ? base + "|" + ex.map(escRe).join("|") : base;
        return new RegExp("\\b(?:" + all + ")\\b");
    }

    function rule(lang) {
        // Order matters: longer/greedier tokens (raw strings, strings, comments)
        // must come before words so their contents aren't re-tokenized.
        if (lang === "slint") {
            return [
                ["com",  /\/\/[^\n]*|\/\*[\s\S]*?\*\//],
                ["str",  /"(?:\\.|[^"\\])*"/],
                ["num",  /#[0-9a-fA-F]{3,8}\b|@[a-z-]+|\b\d+\.?\d*(?:px|phx|ms|s|deg|%)?\b/],
                ["kw",   words(lang, "keyword", SLINT_KW)],
                ["type", words(lang, "type", SLINT_TYPE)],
            ];
        }
        if (lang === "glsl") {
            return [
                ["com",  /\/\/[^\n]*|\/\*[\s\S]*?\*\//],
                ["pre",  /#[a-zA-Z]+[^\n]*/],
                ["num",  /\b\d+\.?\d*\b/],
                ["fn",   words(lang, "fn", GLSL_FN)],
                ["kw",   words(lang, "keyword", GLSL_KW)],
                ["type", words(lang, "type", GLSL_TYPE)],
            ];
        }
        if (lang === "bash") {
            return [
                ["com",  /#[^\n]*/],
                ["str",  /"(?:\\.|[^"\\])*"|'[^']*'/],
                ["pre",  /\$\w+|\$\{[^}]*\}/],
                ["num",  /\b\d+\b/],
            ];
        }
        // default: cpp
        return [
            ["str",  /R"\([\s\S]*?\)"/],            // raw string literal R"(...)"
            ["str",  /"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'/],
            ["com",  /\/\/[^\n]*|\/\*[\s\S]*?\*\//],
            ["pre",  /^[ \t]*#[a-zA-Z]+/m],         // preprocessor directive
            ["num",  /\b(?:0x[0-9a-fA-F]+|\d+\.?\d*[fuUlL]*)\b/],
            ["kw",   words(lang, "keyword", CPP_KW)],
            ["type", words(lang, "type", CPP_TYPE)],
        ];
    }

    function highlight(code, lang) {
        var rules = rule(lang);
        // Build one combined regex with a capture group per rule.
        var parts = rules.map(function (r) { return "(" + r[1].source + ")"; });
        // include the 'm' flag if any rule used it (preprocessor)
        var combined = new RegExp(parts.join("|"), "gm");
        var out = "", last = 0, m;
        while ((m = combined.exec(code)) !== null) {
            if (m.index > last) out += esc(code.slice(last, m.index));
            // find which group matched
            var cls = null, txt = m[0];
            for (var g = 1; g < m.length; g++) {
                if (m[g] !== undefined) { cls = rules[g - 1][0]; break; }
            }
            out += '<span class="t-' + cls + '">' + esc(txt) + "</span>";
            last = m.index + txt.length;
            if (txt.length === 0) combined.lastIndex++; // guard against zero-width
        }
        out += esc(code.slice(last));
        return out;
    }

    function renderCodeBlocks() {
        document.querySelectorAll("figure.code").forEach(function (fig) {
            var script = fig.querySelector('script[type="text/plain"]');
            if (!script) return;
            var lang = fig.getAttribute("data-lang") || "cpp";
            var ref = fig.getAttribute("data-ref") || "";
            var raw = script.textContent.replace(/^\n/, "").replace(/\s+$/, "");

            var head = document.createElement("div");
            head.className = "code-head";
            var refHtml = ref ? '<span class="ref">' + ref.replace(/^([^·]+)(·.*)?$/, "<b>$1</b>$2") + "</span>" : "";
            head.innerHTML =
                '<span class="lang">' + lang + "</span>" + refHtml +
                '<button class="copy" type="button">copy</button>';

            var pre = document.createElement("pre");
            var codeEl = document.createElement("code");
            codeEl.innerHTML = highlight(raw, lang);
            pre.appendChild(codeEl);

            head.querySelector(".copy").addEventListener("click", function () {
                navigator.clipboard.writeText(raw).then(function () {
                    var b = head.querySelector(".copy");
                    b.textContent = "copied!";
                    setTimeout(function () { b.textContent = "copy"; }, 1200);
                });
            });

            fig.textContent = "";
            fig.appendChild(head);
            fig.appendChild(pre);
        });
    }

    // ---- Heading anchors ---------------------------------------------------
    function slug(s) { return s.toLowerCase().replace(/[^\w]+/g, "-").replace(/^-+|-+$/g, ""); }

    function addAnchors() {
        document.querySelectorAll(".content h2, .content h3").forEach(function (h) {
            if (!h.id) h.id = slug(h.textContent);
            var a = document.createElement("a");
            a.className = "h-anchor";
            a.href = "#" + h.id;
            a.textContent = "#";
            h.appendChild(a);
        });
    }

    // ---- Auto "on this page" TOC ------------------------------------------
    function buildToc() {
        var content = document.querySelector(".content");
        if (!content) return;
        var heads = content.querySelectorAll("h2, h3");
        if (heads.length < 3) return;
        var toc = document.createElement("nav");
        toc.className = "toc";
        var html = "<h5>On this page</h5>";
        heads.forEach(function (h) {
            var lvl = h.tagName === "H3" ? " lvl3" : "";
            var label = h.textContent.replace(/#$/, "");
            html += '<a class="toc-link' + lvl + '" href="#' + h.id + '">' + label + "</a>";
        });
        toc.innerHTML = html;
        var wrap = document.querySelector(".content-wrap");
        if (wrap) wrap.appendChild(toc);

        // scroll-spy
        var links = toc.querySelectorAll(".toc-link");
        var map = {};
        links.forEach(function (l) { map[l.getAttribute("href").slice(1)] = l; });
        var obs = new IntersectionObserver(function (entries) {
            entries.forEach(function (e) {
                if (e.isIntersecting) {
                    links.forEach(function (l) { l.classList.remove("active"); });
                    if (map[e.target.id]) map[e.target.id].classList.add("active");
                }
            });
        }, { rootMargin: "-10% 0px -75% 0px" });
        heads.forEach(function (h) { obs.observe(h); });
    }

    // ---- Active sidebar link ----------------------------------------------
    function markActiveNav() {
        var here = location.pathname.split("/").pop() || "index.html";
        document.querySelectorAll(".sidebar a[href]").forEach(function (a) {
            var href = a.getAttribute("href");
            if (href === here || (here === "" && href === "index.html")) a.classList.add("active");
        });
    }

    // ---- Mobile nav --------------------------------------------------------
    function mobileNav() {
        var btn = document.querySelector(".menu-btn");
        if (!btn) return;
        btn.addEventListener("click", function () { document.body.classList.toggle("nav-open"); });
        document.querySelectorAll(".sidebar a").forEach(function (a) {
            a.addEventListener("click", function () { document.body.classList.remove("nav-open"); });
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        renderCodeBlocks();
        addAnchors();
        buildToc();
        markActiveNav();
        mobileNav();
    });
})();
