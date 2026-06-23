/*
 * deck-engine.js — 재사용 발표 엔진.
 * 역할: registerDeck 로 등록된 deck 들을 드롭다운에 노출하고, 슬라이드 블록(slot)을 type 별로 렌더링한다.
 *       + 키보드/버튼 네비, URL 해시 동기화, 용어 자동 툴팁(GLOSSARY), diagram/flow 흐름 단계 강조.
 * 입력: window.URHYNIX_DECKS (decks/*.js 가 registerDeck 로 push). 의존: glossary.js, annotate.js(선택).
 */
window.URHYNIX_DECKS = window.URHYNIX_DECKS || [];
window.registerDeck = function (deck) { window.URHYNIX_DECKS.push(deck); };

window.DeckEngine = (function () {
  // KEYWORD_MODE: 슬라이드는 키워드만 크게 보여주고, 설명 산문(lead/d/note/subtitle/body)은
  //   슬라이드에서 빼서 별도 대본(presentation-script.md)으로 분리한다. false 로 두면 원래대로 복원.
  var KEYWORD_MODE = true;
  var deckIdx = 0, slideIdx = 0, step = 0, maxStep = 0;
  var host, fill, counter, sel;

  function esc(s) { return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
  // 인라인 마크업 허용: **굵게**, `코드`, [표시](링크)
  function md(s) {
    return esc(s)
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>")
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a class="link" href="$2" target="_blank" rel="noopener">$1</a>');
  }
  var slotN = 0;
  function slot(inner, cls) { // 메모 앵커가 붙는 슬롯 래퍼
    return '<div class="anno-slot ' + (cls || "") + '" data-anno-key="el:' + (slotN++) + '">' + inner + "</div>";
  }

  // ---------- 블록 렌더러 ----------
  var R = {
    cover: function (s) {
      var tags = (s.tags || []).map(function (t) { return '<span class="tag">' + md(t) + "</span>"; }).join("");
      return '<div class="slide cover">' +
        "<h1>" + md(s.title) + "</h1>" +
        (!KEYWORD_MODE && s.subtitle ? '<div class="sub">' + md(s.subtitle) + "</div>" : "") +
        (tags ? '<div class="tags">' + tags + "</div>" : "") +
        (!KEYWORD_MODE && s.note ? '<div class="lead">' + md(s.note) + "</div>" : "") +
        "</div>";
    },
    bullets: function (s) {
      var lis = (s.items || []).map(function (it) {
        var body = typeof it === "string" ? md(it) : ("<b>" + md(it.h) + "</b>" + (!KEYWORD_MODE && it.d ? '<span class="d">' + md(it.d) + "</span>" : ""));
        return "<li>" + slotInner(body) + "</li>";
      }).join("");
      return shell(s, '<ul class="bul">' + lis + "</ul>");
    },
    cards: function (s) {
      var cols = "c" + (s.cols || 3);
      var cs = (s.cards || []).map(function (c) {
        var badge = c.badge ? ' <span class="badge ' + (c.badge.kind || "accent") + '">' + esc(c.badge.text) + "</span>" : "";
        return slot('<div class="card"><h3>' + md(c.title) + badge + "</h3>" +
          (!KEYWORD_MODE && c.body ? "<p>" + md(c.body) + "</p>" : "") +
          (c.sub ? '<div class="sub">' + md(c.sub) + "</div>" : "") + "</div>");
      }).join("");
      return shell(s, '<div class="grid ' + cols + '">' + cs + "</div>");
    },
    diagram: function (s) {
      var parts = [], i = 0;
      (s.nodes || []).forEach(function (n, idx) {
        if (idx > 0) parts.push('<div class="arrow">→</div>');
        parts.push(slot('<div class="node" data-step="' + i + '"><div class="nlabel">' + md(n.label) + "</div>" +
          (n.sub ? '<div class="nsub">' + md(n.sub) + "</div>" : "") + "</div>"));
        i++;
      });
      maxStepHint = i;
      return shell(s, '<div class="diagram">' + parts.join("") + "</div>" +
        (!KEYWORD_MODE && s.note ? '<div class="lead">' + md(s.note) + "</div>" : ""), true);
    },
    flow: function (s) {
      var i = 0, rows = (s.chains || []).map(function (ch) {
        var steps = (ch.steps || []).map(function (st, idx) {
          var arr = idx > 0 ? '<div class="arrow">→</div>' : "";
          var box = slot('<div class="step" data-step="' + (i) + '">' +
            (st.k ? '<div class="k">' + esc(st.k) + "</div>" : "") +
            '<div class="v">' + md(st.v) + "</div></div>");
          i++;
          return arr + box;
        }).join("");
        return '<div class="chain">' + (ch.label ? '<div class="clabel">' + md(ch.label) + "</div>" : "") + steps + "</div>";
      }).join("");
      maxStepHint = i;
      return shell(s, rows, true);
    },
    filetree: function (s) {
      function node(n) {
        if (n.children && n.children.length) {
          var kids = n.children.map(node).join("");
          return slot('<details ' + (n.open ? "open" : "") + ' class="dir"><summary><span class="fname">' + esc(n.name) + "</span>" +
            (n.desc ? '<span class="fdesc">' + esc(n.desc) + "</span>" : "") + "</summary>" + kids + "</details>");
        }
        return slot('<div class="leaf"><span class="fname">' + esc(n.name) + "</span>" +
          (n.desc ? '<span class="fdesc">' + esc(n.desc) + "</span>" : "") + "</div>");
      }
      var t = (s.tree || []).map(node).join("");
      return shell(s, '<div class="tree">' + t + "</div>");
    },
    table: function (s) {
      var head = "<tr>" + (s.columns || []).map(function (c) { return "<th>" + esc(c) + "</th>"; }).join("") + "</tr>";
      var body = (s.rows || []).map(function (r) {
        var tds = r.map(function (cell) {
          if (cell && typeof cell === "object") return '<td class="cell-' + (cell.kind || "") + '">' + md(cell.v) + "</td>";
          return "<td>" + md(cell) + "</td>";
        }).join("");
        return slot("<tr>" + tds + "</tr>", "");
      }).join("");
      return shell(s, '<table class="tbl"><thead>' + head + "</thead><tbody>" + body + "</tbody></table>");
    },
    progress: function (s) {
      var rows = (s.items || []).map(function (it) {
        var pct = it.total ? Math.round((it.done / it.total) * 100) : (it.pct || 0);
        var cls = it.status === "완료" ? "" : (it.status === "진행" ? "warn" : "idle");
        return slot('<div class="row ' + cls + '"><div class="top"><span class="plabel">' + md(it.label) +
          ' <span class="badge ' + (it.status === "완료" ? "ok" : it.status === "진행" ? "warn" : "info") + '">' + esc(it.status || "") + "</span></span>" +
          '<span class="psub">' + (it.total ? it.done + " / " + it.total : pct + "%") + (it.sub ? " · " + md(it.sub) : "") + "</span></div>" +
          '<div class="bar"><div style="width:' + pct + '%"></div></div></div>');
      }).join("");
      return shell(s, '<div class="prog">' + rows + "</div>");
    },
    // image: 사진/스크린샷 슬롯. 파일이 없으면 점선 placeholder + 올릴 경로를 보여준다.
    //   { type:"image", title, lead, src:"img/x.png", caption, label }  또는
    //   { type:"image", images:[{src,caption,label}], cols:2 }
    image: function (s) {
      var ims = s.images || (s.src ? [{ src: s.src, caption: s.caption, label: s.label }] : []);
      var cells = ims.map(function (im) {
        return slot('<figure class="figure">' +
          '<img class="shot" src="' + esc(im.src) + '" alt="' + esc(im.caption || "") + '" ' +
          'onerror="this.closest(\'.figure\').classList.add(\'ph\')" />' +
          '<div class="ph-box"><div class="ph-ic">🖼</div>' +
          '<div class="ph-t">' + esc(im.label || "여기에 이미지 업로드") + "</div>" +
          '<div class="ph-p"><code>' + esc(im.src) + "</code></div></div>" +
          (im.caption ? '<figcaption>' + md(im.caption) + "</figcaption>" : "") +
          "</figure>");
      }).join("");
      var cols = s.cols || (ims.length > 1 ? 2 : 1);
      return shell(s, '<div class="figs c' + cols + '">' + cells + "</div>");
    }
  };

  function slotInner(body) { return '<span class="anno-slot" data-anno-key="el:' + (slotN++) + '">' + body + "</span>"; }

  var maxStepHint = 0;
  function shell(s, inner, steppable) {
    var hint = steppable ? '<div class="hl-hint"><button onclick="DeckEngine.stepHl(1)">▶ 흐름 강조 (↓)</button></div>' : "";
    return '<div class="slide">' + hint +
      (s.title ? "<h2>" + md(s.title) + "</h2>" : "") +
      (!KEYWORD_MODE && s.lead ? '<div class="lead">' + md(s.lead) + "</div>" : "") +
      inner +
      '<div class="slide-foot"><span></span><span></span></div></div>';
  }

  // ---------- 용어 자동 툴팁 ----------
  var rx = null;
  function buildRx() {
    var keys = Object.keys(window.GLOSSARY || {}).sort(function (a, b) { return b.length - a.length; });
    if (!keys.length) return;
    var body = keys.map(function (k) { return k.replace(/[.*+?^${}()|[\]\\\/]/g, "\\$&"); }).join("|");
    // 영문/숫자에 둘러싸인 부분일치 방지(예: RobotPoseSubscriber 안의 Subscriber 미매칭)
    rx = new RegExp("(?<![A-Za-z0-9])(" + body + ")(?![A-Za-z0-9])");
  }
  // deck 전체를 미리 훑어, 각 용어가 "처음 등장하는 슬라이드"를 기록한다.
  function computeFirstSeen(deck) {
    if (!rx) return {};
    var seen = {}, res = {};
    for (var i = 0; i < deck.slides.length; i++) {
      var hay = JSON.stringify(deck.slides[i]).replace(/`[^`]*`/g, " ").replace(/\[[^\]]*\]\([^)]*\)/g, " ");
      var re = new RegExp(rx.source, "g"), m;
      while ((m = re.exec(hay))) { if (!seen[m[0]]) { seen[m[0]] = 1; res[m[0]] = i; } }
    }
    return res;
  }
  // allowed: 이 슬라이드에서 처음 등장하는 용어만. 같은 슬라이드 안에서도 첫 1회만 감싼다.
  function applyGlossary(root, allowed) {
    if (!rx) return;
    var skip = { SCRIPT: 1, STYLE: 1, CODE: 1, A: 1, TEXTAREA: 1, BUTTON: 1 };
    var wrapped = {};
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
    var targets = [], node;
    while ((node = walker.nextNode())) {
      var p = node.parentNode;
      if (!p || skip[p.nodeName] || p.classList && p.classList.contains("term")) continue;
      if (rx.test(node.nodeValue)) targets.push(node);
    }
    targets.forEach(function (tn) {
      var txt = tn.nodeValue, re = new RegExp(rx.source, "g"), m, last = 0, frag = null;
      while ((m = re.exec(txt))) {
        var term = m[0];
        if (!allowed[term] || wrapped[term]) continue; // 처음 등장 슬라이드의 첫 1회만
        if (!frag) frag = document.createDocumentFragment();
        if (m.index > last) frag.appendChild(document.createTextNode(txt.slice(last, m.index)));
        var span = document.createElement("span");
        span.className = "term"; span.textContent = term;
        span.setAttribute("data-tip", window.GLOSSARY[term]);
        frag.appendChild(span);
        wrapped[term] = true;
        last = m.index + term.length;
      }
      if (frag) {
        if (last < txt.length) frag.appendChild(document.createTextNode(txt.slice(last)));
        tn.parentNode.replaceChild(frag, tn);
      }
    });
  }

  // ---------- 흐름 강조 ----------
  function stepHl(dir) {
    if (!maxStep) return;
    step = Math.max(0, Math.min(maxStep, step + dir));
    var nodes = host.querySelectorAll("[data-step]");
    nodes.forEach(function (n) {
      var k = +n.getAttribute("data-step");
      n.classList.toggle("is-hl", k < step);
      n.classList.toggle("is-cur", k === step - 1);
    });
  }

  // ---------- 렌더 ----------
  function render() {
    var deck = URHYNIX_DECKS[deckIdx]; if (!deck) return;
    document.body.className = "theme-" + (deck.theme || "cyan");
    var s = deck.slides[slideIdx]; if (!s) return;
    slotN = 0; maxStepHint = 0; step = 0;
    var fn = R[s.type] || R.bullets;
    host.innerHTML = fn(s);
    maxStep = maxStepHint;
    if (!deck._firstSeen) deck._firstSeen = computeFirstSeen(deck);
    var allowed = {};
    Object.keys(deck._firstSeen).forEach(function (t) { if (deck._firstSeen[t] === slideIdx) allowed[t] = true; });
    applyGlossary(host, allowed);
    // foot
    var foot = host.querySelector(".slide-foot");
    if (foot) foot.innerHTML = "<span>" + esc(deck.title) + "</span><span>" + (slideIdx + 1) + " / " + deck.slides.length + "</span>";
    fill.style.width = ((slideIdx + 1) / deck.slides.length * 100) + "%";
    counter.textContent = (slideIdx + 1) + " / " + deck.slides.length;
    location.hash = deck.id + "/" + slideIdx;
    if (window.Annotate) Annotate.onRender(deck.id, slideIdx);
  }

  function goSlide(i) {
    var deck = URHYNIX_DECKS[deckIdx];
    slideIdx = Math.max(0, Math.min(deck.slides.length - 1, i));
    render();
  }
  function goDeck(i, keepSlide) {
    deckIdx = Math.max(0, Math.min(URHYNIX_DECKS.length - 1, i));
    sel.value = deckIdx;
    if (!keepSlide) slideIdx = 0;
    render();
  }
  function next() {
    var deck = URHYNIX_DECKS[deckIdx];
    if (slideIdx < deck.slides.length - 1) goSlide(slideIdx + 1);
    else if (deckIdx < URHYNIX_DECKS.length - 1) goDeck(deckIdx + 1);
  }
  function prev() {
    if (slideIdx > 0) goSlide(slideIdx - 1);
    else if (deckIdx > 0) { deckIdx--; sel.value = deckIdx; slideIdx = URHYNIX_DECKS[deckIdx].slides.length - 1; render(); }
  }

  // ---------- 툴팁 위치 ----------
  function bindTip() {
    var tip = document.getElementById("tip");
    document.addEventListener("mouseover", function (e) {
      var t = e.target.closest && e.target.closest(".term"); if (!t) return;
      tip.innerHTML = "<b>" + esc(t.textContent) + "</b> — " + esc(t.getAttribute("data-tip"));
      tip.classList.add("show"); posTip(e);
    });
    document.addEventListener("mousemove", function (e) { if (tip.classList.contains("show")) posTip(e); });
    document.addEventListener("mouseout", function (e) {
      if (e.target.closest && e.target.closest(".term")) tip.classList.remove("show");
    });
    function posTip(e) {
      var x = e.clientX + 14, y = e.clientY + 16;
      if (x + 330 > innerWidth) x = e.clientX - 330;
      tip.style.left = x + "px"; tip.style.top = y + "px";
    }
  }

  function init() {
    host = document.getElementById("slideHost");
    fill = document.getElementById("progFill");
    counter = document.getElementById("counter");
    sel = document.getElementById("deckSelect");
    buildRx(); bindTip();

    URHYNIX_DECKS.forEach(function (d, i) {
      var o = document.createElement("option"); o.value = i; o.textContent = d.title; sel.appendChild(o);
    });
    sel.addEventListener("change", function () { goDeck(+sel.value); });
    document.getElementById("nextBtn").onclick = next;
    document.getElementById("prevBtn").onclick = prev;
    document.getElementById("fsBtn").onclick = function () {
      if (!document.fullscreenElement) document.documentElement.requestFullscreen(); else document.exitFullscreen();
    };
    if (window.Annotate) Annotate.init();

    document.addEventListener("keydown", function (e) {
      if (/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) return;
      if (e.key === "ArrowRight" || e.key === "PageDown") next();
      else if (e.key === "ArrowLeft" || e.key === "PageUp") prev();
      else if (e.key === " ") { e.preventDefault(); next(); }
      else if (e.key === "ArrowDown" || e.key === "h" || e.key === "H") { e.preventDefault(); stepHl(1); }
      else if (e.key === "ArrowUp") { e.preventDefault(); stepHl(-1); }
      else if (e.key === "Home") goSlide(0);
      else if (e.key === "End") goSlide(URHYNIX_DECKS[deckIdx].slides.length - 1);
      else if (e.key === "m" || e.key === "M") { if (window.Annotate) Annotate.toggle(); }
    });

    // 해시 복원: #deckId/slideIdx
    var h = decodeURIComponent(location.hash.replace("#", ""));
    if (h) {
      var parts = h.split("/"), di = URHYNIX_DECKS.findIndex(function (d) { return d.id === parts[0]; });
      if (di >= 0) { deckIdx = di; slideIdx = +parts[1] || 0; }
    }
    sel.value = deckIdx;
    render();
  }

  return { init: init, next: next, prev: prev, goSlide: goSlide, goDeck: goDeck, stepHl: stepHl,
           current: function () { return { deck: URHYNIX_DECKS[deckIdx], slideIdx: slideIdx }; } };
})();
