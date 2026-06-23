/*
 * annotate.js — 회의 중 메모(핀) 기능.
 * 역할: 메모 모드에서 슬라이드의 슬롯(노드/카드/트리 등) 또는 빈 좌표에 핀을 찍어 메모를 단다.
 *       localStorage(deck:slide 별) 저장 → 새로고침에도 복원. "복사"로 현재 deck 메모를 Markdown 클립보드 출력.
 * 입력: DeckEngine(현재 deck/slide), index.html 의 #stage/#slideHost/#annoLayer/#memoPanel + 상단 버튼.
 */
window.Annotate = (function () {
  var mode = false, deckId = "", slideIdx = 0;
  var stage, host, layer, panel, badge;
  var KINDS = [["note", "메모"], ["q", "질문"], ["todo", "할일"], ["decide", "결정"]];

  function key(d, i) { return "urhynix-anno:" + d + ":" + i; }
  function load(d, i) { try { return JSON.parse(localStorage.getItem(key(d, i)) || "[]"); } catch (e) { return []; } }
  function save(d, i, arr) { localStorage.setItem(key(d, i), JSON.stringify(arr)); }

  function init() {
    stage = document.getElementById("stage");
    host = document.getElementById("slideHost");
    layer = document.getElementById("annoLayer");
    panel = document.getElementById("memoPanel");
    badge = document.getElementById("memoCount");
    document.getElementById("memoBtn").onclick = toggle;
    document.getElementById("panelBtn").onclick = function () { panel.classList.toggle("open"); };
    document.getElementById("copyBtn").onclick = copyMarkdown;
    stage.addEventListener("click", onStageClick);
    window.addEventListener("resize", function () { renderPins(); });
  }

  function toggle() {
    mode = !mode;
    stage.classList.toggle("memo", mode);
    document.getElementById("memoBtn").classList.toggle("on", mode);
  }

  function onStageClick(e) {
    closePopup();
    if (!mode) return;
    if (e.target.closest(".pin") || e.target.closest(".anno-pop")) return;
    var rect = stage.getBoundingClientRect();
    var slotEl = e.target.closest("[data-anno-key]");
    var note = {
      id: "n" + Date.now() + Math.floor(Math.random() * 1000),
      slot: slotEl ? slotEl.getAttribute("data-anno-key") : null,
      xPct: ((e.clientX - rect.left) / rect.width) * 100,
      yPct: ((e.clientY - rect.top) / rect.height) * 100,
      kind: "note", text: ""
    };
    var arr = load(deckId, slideIdx); arr.push(note); save(deckId, slideIdx, arr);
    renderPins();
    openEditor(note.id);
  }

  function pinPos(note) {
    var rect = stage.getBoundingClientRect();
    if (note.slot) {
      var el = host.querySelector('[data-anno-key="' + note.slot + '"]');
      if (el) {
        var r = el.getBoundingClientRect();
        return { x: r.right - rect.left - 6, y: r.top - rect.top + 10 };
      }
    }
    return { x: note.xPct / 100 * rect.width, y: note.yPct / 100 * rect.height };
  }

  function renderPins() {
    if (!layer) return;
    layer.querySelectorAll(".pin").forEach(function (p) { p.remove() });
    var arr = load(deckId, slideIdx);
    arr.forEach(function (note, i) {
      var p = pinPos(note);
      var pin = document.createElement("div");
      pin.className = "pin " + note.kind;
      pin.style.left = p.x + "px"; pin.style.top = p.y + "px";
      pin.textContent = i + 1;
      pin.title = note.text || "(빈 메모)";
      pin.onclick = function (ev) { ev.stopPropagation(); openEditor(note.id); };
      layer.appendChild(pin);
    });
    renderPanel(); updateBadge();
  }

  function openEditor(id) {
    closePopup();
    var arr = load(deckId, slideIdx), note = arr.find(function (n) { return n.id === id; });
    if (!note) return;
    var p = pinPos(note);
    var pop = document.createElement("div");
    pop.className = "anno-pop"; pop.id = "annoPop";
    var left = Math.min(p.x + 14, stage.clientWidth - 274);
    var top = Math.min(p.y + 8, stage.clientHeight - 180);
    pop.style.left = Math.max(8, left) + "px"; pop.style.top = Math.max(8, top) + "px";
    pop.innerHTML =
      '<textarea placeholder="메모 입력…">' + (note.text || "").replace(/</g, "&lt;") + "</textarea>" +
      '<div class="knd">' + KINDS.map(function (k) {
        return '<button class="' + k[0] + (note.kind === k[0] ? " sel" : "") + '" data-k="' + k[0] + '">' + k[1] + "</button>";
      }).join("") + "</div>" +
      '<div class="act"><button class="del">삭제</button><button class="save">저장</button></div>';
    layer.appendChild(pop);
    var ta = pop.querySelector("textarea"); ta.focus();
    pop.addEventListener("click", function (e) { e.stopPropagation(); });
    pop.querySelectorAll(".knd button").forEach(function (b) {
      b.onclick = function () { note.kind = b.getAttribute("data-k"); persist(note); pop.querySelectorAll(".knd button").forEach(function (x) { x.classList.remove("sel"); }); b.classList.add("sel"); };
    });
    pop.querySelector(".save").onclick = function () { note.text = ta.value; persist(note); closePopup(); renderPins(); };
    pop.querySelector(".del").onclick = function () { remove(note.id); closePopup(); renderPins(); };
    function persist(n) {
      var a = load(deckId, slideIdx), idx = a.findIndex(function (x) { return x.id === n.id; });
      if (idx >= 0) { a[idx] = n; save(deckId, slideIdx, a); }
    }
  }
  function remove(id) {
    var a = load(deckId, slideIdx).filter(function (n) { return n.id !== id; });
    save(deckId, slideIdx, a);
  }
  function closePopup() { var p = document.getElementById("annoPop"); if (p) p.remove(); }

  function renderPanel() {
    var arr = load(deckId, slideIdx);
    var head = "<h4>이 슬라이드 메모 (" + arr.length + ")</h4>";
    var body = arr.length ? arr.map(function (n, i) {
      var kn = KINDS.find(function (k) { return k[0] === n.kind; });
      return '<div class="mitem" data-id="' + n.id + '"><span class="mk badge ' +
        (n.kind === "note" ? "accent" : n.kind === "q" ? "warn" : n.kind === "todo" ? "bad" : "ok") + '">' +
        (i + 1) + " " + (kn ? kn[1] : "") + "</span><div>" + (n.text ? esc(n.text) : "<i>(빈 메모)</i>") + "</div></div>";
    }).join("") : '<div class="empty">메모 모드(📌)에서 슬라이드를 클릭해 메모를 답니다.</div>';
    var actions = '<div class="row-act"><button id="mClear">이 슬라이드 비우기</button><button id="mCopy">deck 메모 복사</button></div>';
    panel.innerHTML = head + body + actions;
    panel.querySelectorAll(".mitem").forEach(function (m) {
      m.onclick = function () { openEditor(m.getAttribute("data-id")); panel.classList.remove("open"); };
    });
    panel.querySelector("#mClear").onclick = function () {
      if (confirm("이 슬라이드 메모를 모두 지울까요?")) { save(deckId, slideIdx, []); renderPins(); }
    };
    panel.querySelector("#mCopy").onclick = copyMarkdown;
  }

  function deckSlideCount() { var c = DeckEngine.current(); return c.deck ? c.deck.slides.length : 0; }
  function updateBadge() {
    var total = 0, n = deckSlideCount();
    for (var i = 0; i < n; i++) total += load(deckId, i).length;
    badge.textContent = total; badge.classList.toggle("show", total > 0);
  }

  function copyMarkdown() {
    var c = DeckEngine.current(), deck = c.deck; if (!deck) return;
    var lines = ["# 회의 메모 — " + deck.title, ""];
    var any = false;
    deck.slides.forEach(function (s, i) {
      var arr = load(deck.id, i); if (!arr.length) return;
      any = true;
      lines.push("## 슬라이드 " + (i + 1) + ": " + (s.title || s.type));
      arr.forEach(function (n) {
        var kn = KINDS.find(function (k) { return k[0] === n.kind; });
        lines.push("- [" + (kn ? kn[1] : "메모") + "] " + (n.text || "(빈 메모)"));
      });
      lines.push("");
    });
    if (!any) lines.push("_(메모 없음)_");
    var text = lines.join("\n");
    copyText(text).then(function () { flash("메모를 Markdown으로 복사했어요"); },
                        function () { flash("복사 실패 — 콘솔에 출력했어요"); console.log(text); });
  }
  function copyText(t) {
    if (navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(t);
    return new Promise(function (res, rej) {
      try { var ta = document.createElement("textarea"); ta.value = t; document.body.appendChild(ta); ta.select();
        document.execCommand("copy"); ta.remove(); res(); } catch (e) { rej(e); }
    });
  }
  function flash(msg) {
    var d = document.createElement("div");
    d.textContent = msg;
    d.style.cssText = "position:fixed;left:50%;bottom:28px;transform:translateX(-50%);background:#0a1224;color:#6ee7ff;border:1px solid #6ee7ff;padding:10px 18px;border-radius:10px;z-index:80;font-size:13px;font-weight:600;";
    document.body.appendChild(d); setTimeout(function () { d.remove(); }, 1800);
  }
  function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }

  function onRender(d, i) {
    deckId = d; slideIdx = i; closePopup();
    requestAnimationFrame(function () { renderPins(); });
  }

  return { init: init, toggle: toggle, onRender: onRender };
})();
