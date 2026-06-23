// 컨트롤러 — UI(탭·범례·요약·무대·툴바) 배선, 키보드, 해시 라우팅, 발표/편집 모드 전환.
// 편집기(editor.js)가 로드돼 있으면 편집 UI/드래그를 위임한다(없어도 발표 모드는 동작).
// 전역: window.ScenarioApp. 의존: Store, Render, Nav, (옵션)Editor, d3.
(function () {
  "use strict";

  var App = {
    mount: function (rootSel) {
      Store.init();
      var root = d3.select(rootSel); root.html("");

      var tabs = root.append("div").attr("class", "scn-tabs");

      var legend = root.append("div").attr("class", "scn-legend");
      window.RISK_LEGEND.forEach(function (r) {
        var c = Render.colorFor({ type: "process", risk: r.key });
        var item = legend.append("span").attr("class", "scn-legend-item");
        item.append("span").attr("class", "scn-dot").style("background", c.stroke);
        item.append("b").text(r.tag); item.append("i").text(" " + r.ko);
      });

      var head = root.append("div").attr("class", "scn-head");
      head.append("div").attr("class", "scn-summary");
      head.append("div").attr("class", "scn-stepinfo");

      root.append("div").attr("class", "scn-stage").append("svg").attr("class", "scn-svg");

      // 툴바
      var ctl = root.append("div").attr("class", "scn-ctl");
      var nav = ctl.append("div").attr("class", "scn-ctl-grp");
      nav.append("button").attr("class", "scn-btn").text("◀ 이전").on("click", Nav.left);
      nav.append("button").attr("class", "scn-btn scn-next").text("다음 ▶").on("click", Nav.forward);
      nav.append("button").attr("class", "scn-btn").text("↺ 처음").on("click", function () { Nav.rebind(); });
      nav.append("button").attr("class", "scn-btn").text("⤢ 전체보기").on("click", Nav.toggleFit);

      var play = ctl.append("div").attr("class", "scn-ctl-grp");
      play.append("button").attr("class", "scn-btn scn-play").text("▶ 자동재생").on("click", Nav.togglePlay);
      play.append("button").attr("class", "scn-btn").text("✦ 경로강조").on("click", Nav.showFullPath);
      var sp = play.append("label").attr("class", "scn-range").text("속도");
      sp.append("input").attr("type", "range").attr("min", 500).attr("max", 3000).attr("step", 100).attr("value", Nav.speed)
        .on("input", function () { Nav.setSpeed(+this.value); });
      var lp = play.append("label").attr("class", "scn-check");
      lp.append("input").attr("type", "checkbox").on("change", function () { Nav.setLoop(this.checked); });
      lp.append("span").text(" 반복");

      var edit = ctl.append("div").attr("class", "scn-ctl-grp");
      edit.append("button").attr("class", "scn-btn scn-modebtn").text("✎ 편집 모드").on("click", function () { Store.toggleMode(); });
      edit.append("button").attr("class", "scn-btn").text("⤓ 내보내기").on("click", Store.exportJSON);
      var imp = edit.append("label").attr("class", "scn-btn").text("⤒ 가져오기");
      imp.append("input").attr("type", "file").attr("accept", ".json").style("display", "none")
        .on("change", function () {
          var f = this.files[0]; if (!f) return;
          Store.importJSON(f, function (err) { if (err) alert("가져오기 실패: " + err.message); });
        });
      edit.append("button").attr("class", "scn-btn").text("♻ 기본값").on("click", function () {
        if (confirm("편집 내용을 버리고 기본 시나리오로 되돌릴까요?")) Store.resetToDefault();
      });

      // 편집 패널 마운트 지점(editor.js 가 채움)
      root.append("div").attr("class", "scn-editor-host");

      App.buildTabs(tabs);
      App.bindKeys();
      App.bindHash();

      Store.on(function (kind) {
        if (kind === "select") { App.renderCurrent(); App.syncTabs(); window.location.hash = Store.curId; }
        else if (kind === "data") { App.renderCurrent(); }
        else if (kind === "mode") { App.syncMode(); }
      });

      if (window.Editor) Editor.mount(".scn-editor-host");
      App.applyHash();
      App.renderCurrent();
      App.syncTabs();
      App.syncMode();
    },

    buildTabs: function (tabs) {
      tabs.selectAll("*").remove();
      Store.list().forEach(function (s) {
        tabs.append("button").attr("class", "scn-tab").attr("data-id", s.id).text(s.title)
          .on("click", function () { Store.select(s.id); });
      });
    },
    syncTabs: function () {
      d3.selectAll(".scn-tab").classed("active", function () { return this.getAttribute("data-id") === Store.curId; });
    },
    syncMode: function () {
      var editing = Store.mode === "edit";
      d3.select(".scn-editor-host").classed("open", editing);
      d3.select(".scn-modebtn").classed("on", editing).text(editing ? "▣ 발표 모드" : "✎ 편집 모드");
      d3.select(".scn-svg").classed("editing", editing);
      if (window.Editor) Editor.onMode(editing);
    },

    renderCurrent: function () {
      var scn = Store.current();
      d3.select(".scn-summary").text(scn.summary || "");
      Render.draw(scn, ".scn-svg");
      App.bindNodeEvents();
      Nav.rebind();
      if (window.Editor && Store.mode === "edit") { Editor.afterRender(); Editor.renderPanel(); Editor.markSel(); }
    },

    bindNodeEvents: function () {
      Render.L.nodeSel.style("cursor", "pointer").on("click", function (ev, id) {
        if (Store.mode === "edit" && window.Editor) Editor.selectNode(id);
        else Nav.jumpToNode(id);
      });
    },

    bindKeys: function () {
      d3.select(window).on("keydown.scn", function (ev) {
        var t = ev.target; if (t && /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName)) return;
        var k = ev.key;
        if (k === "ArrowRight" || k === "ArrowDown" || k === " ") { Nav.forward(); ev.preventDefault(); }
        else if (k === "ArrowLeft") { Nav.left(); ev.preventDefault(); }
        else if (k === "Backspace" || k === "ArrowUp") { Nav.back(); ev.preventDefault(); }
        else if (k === "Home") { Nav.rebind(); }
        else if (k === "End") { Nav.showFullPath(); }
        else if (k === "f" || k === "F") { Nav.toggleFit(); }
        else if (k === "p" || k === "P") { Nav.togglePlay(); }
        else if (k === "e" || k === "E") { Store.toggleMode(); }
        else if (/^[1-9]$/.test(k)) { Store.selectIndex(+k - 1); }
      });
    },

    bindHash: function () {
      d3.select(window).on("hashchange.scn", function () { App.applyHash(); });
    },
    applyHash: function () {
      var h = (window.location.hash || "").replace(/^#/, "");
      if (!h) return;
      var parts = h.split("/");
      var s = Store.list().find(function (x) { return x.id === parts[0]; });
      if (s && s.id !== Store.curId) { Store.curId = s.id; App.renderCurrent(); App.syncTabs(); }
      if (parts[1] === "play") setTimeout(Nav.play, 300);
    }
  };

  window.ScenarioApp = App;
})();
