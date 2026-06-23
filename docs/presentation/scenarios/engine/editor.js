// 편집기 (P1 폼 편집 + P2 드래그) — 노드/엣지 추가·수정·삭제, 드래그 이동, 연결(🔗 연결모드 / Shift-드래그),
// Delete 키 삭제, Ctrl/⌘+Z 실행취소, 노드 색 직접 지정. 모든 변경은 Store.commit()(localStorage 저장 + 재렌더).
// 영구 반영은 툴바 「내보내기」 다운로드 → 레포 반영. 전역: window.Editor. 의존: Store, Render, Nav, d3.
(function () {
  "use strict";
  var TYPES = ["start", "process", "decision", "end"];
  var RISKS = ["none", "safe", "watch", "check", "danger", "evac"];

  var Editor = {
    host: null, sel: null, selEdge: null, linkFrom: null, linkMode: false,

    mount: function (hostSel) {
      Editor.host = d3.select(hostSel);
      Editor.bindKeys();
      Editor.renderPanel();
    },

    onMode: function (editing) {
      if (editing) { Nav.follow = false; Nav.rebind(); Editor.afterRender(); }
      else { Editor.sel = null; Editor.selEdge = null; Editor.linkMode = false; }
      Editor.renderPanel();
    },

    // 편집 전용 단축키: Delete=선택 삭제, Ctrl/⌘+Z=실행취소
    bindKeys: function () {
      d3.select(window).on("keydown.sced", function (ev) {
        if (Store.mode !== "edit") return;
        var t = ev.target; if (t && /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName)) return;
        if (ev.key === "Delete") {
          if (Editor.selEdge) { Editor.delEdge(Editor.selEdge.from, Editor.selEdge.to); Editor.selEdge = null; ev.preventDefault(); }
          else if (Editor.sel) { Editor.delNode(); ev.preventDefault(); }
        } else if ((ev.metaKey || ev.ctrlKey) && (ev.key === "z" || ev.key === "Z")) {
          if (Store.undo()) ev.preventDefault();
        }
      });
    },

    // 매 재렌더 후(편집 모드) 드래그·클릭 핸들러 재부착
    afterRender: function () {
      if (Store.mode !== "edit" || !Render.L) return;
      var svg = Render.L.svg;
      svg.classed("linking", Editor.linkMode);

      var drag = d3.drag()
        .on("start", function (ev, id) {
          Editor.selectNode(id);
          if (Editor.linkMode || ev.sourceEvent.shiftKey) { Editor.linkFrom = id; Editor.tempLine(svg); }
        })
        .on("drag", function (ev, id) {
          var p = d3.pointer(ev.sourceEvent, svg.node());
          if (Editor.linkFrom) { Editor.moveTemp(p); return; }
          d3.select(this).attr("transform", "translate(" + p[0] + "," + p[1] + ")");
          var nd = Render.L.g.node(id); if (nd) { nd.x = p[0]; nd.y = p[1]; }
        })
        .on("end", function (ev, id) {
          var p = d3.pointer(ev.sourceEvent, svg.node());
          if (Editor.linkFrom) {
            var tgt = Editor.nodeAtPoint(p[0], p[1]);
            Editor.clearTemp(); Render.L.nodeSel.classed("linktarget", false);
            if (tgt && tgt !== Editor.linkFrom) Editor.addEdge(Editor.linkFrom, tgt);
            Editor.linkFrom = null; return;
          }
          var n = Editor.node(id); if (n) { n.x = p[0]; n.y = p[1]; Store.commit(); }
        });
      Render.L.nodeSel.call(drag);

      // 엣지 클릭 선택(Delete 로 삭제 가능)
      d3.selectAll(".scn-edge").on("click", function (ev) {
        ev.stopPropagation();
        var parts = (this.getAttribute("data-edge") || "").split("->");
        if (parts.length === 2) Editor.selectEdge(parts[0], parts[1]);
      });
      Editor.markSel(); Editor.markSelEdge();
    },

    nodeAtPoint: function (x, y) {
      var g = Render.L.g, hit = null;
      g.nodes().forEach(function (id) {
        var nd = g.node(id);
        if (x >= nd.x - nd.width / 2 && x <= nd.x + nd.width / 2 &&
            y >= nd.y - nd.height / 2 && y <= nd.y + nd.height / 2) hit = id;
      });
      return hit;
    },
    tempLine: function (svg) {
      svg.append("line").attr("class", "scn-templine").attr("stroke", "#62e08a")
        .attr("stroke-width", 2.5).attr("stroke-dasharray", "6 4").attr("pointer-events", "none");
    },
    // 포인터 위치로 임시선을 끌되, 노드 위면 그 중심으로 스냅 + 초록 강조
    moveTemp: function (p) {
      var nd = Render.L.g.node(Editor.linkFrom), ex = p[0], ey = p[1];
      var over = Editor.nodeAtPoint(p[0], p[1]);
      Render.L.nodeSel.classed("linktarget", function (d) { return d === over && d !== Editor.linkFrom; });
      if (over && over !== Editor.linkFrom) { var t = Render.L.g.node(over); ex = t.x; ey = t.y; }
      d3.select(".scn-templine").attr("x1", nd.x).attr("y1", nd.y).attr("x2", ex).attr("y2", ey);
    },
    clearTemp: function () { d3.select(".scn-templine").remove(); },

    // ===== 데이터 헬퍼 =====
    scn: function () { return Store.current(); },
    node: function (id) { return Editor.scn().nodes.find(function (n) { return n.id === id; }); },
    newId: function () {
      var ids = Editor.scn().nodes.map(function (n) { return n.id; });
      for (var i = 1; i < 999; i++) { if (ids.indexOf("n" + i) < 0) return "n" + i; }
    },

    selectNode: function (id) { Editor.sel = id; Editor.selEdge = null; Editor.renderPanel(); Editor.markSel(); Editor.markSelEdge(); },
    selectEdge: function (from, to) { Editor.selEdge = { from: from, to: to }; Editor.sel = null; Editor.renderPanel(); Editor.markSel(); Editor.markSelEdge(); },
    markSel: function () {
      if (!Render.L) return;
      Render.L.nodeSel.classed("sel", function (d) { return d === Editor.sel; });
    },
    markSelEdge: function () {
      var e = Editor.selEdge;
      d3.selectAll(".scn-edge").classed("sel", function () {
        return e && this.getAttribute("data-edge") === e.from + "->" + e.to;
      });
    },

    addNode: function () {
      var s = Editor.scn(), id = Editor.newId();
      s.nodes.push({ id: id, type: "process", risk: "none", label: "새 노드" });
      Editor.sel = id; Editor.selEdge = null; Store.commit();
    },
    delNode: function () {
      var s = Editor.scn(), id = Editor.sel; if (!id) return;
      s.nodes = s.nodes.filter(function (n) { return n.id !== id; });
      s.edges = s.edges.filter(function (e) { return e.from !== id && e.to !== id; });
      if (s.tour) s.tour = s.tour.filter(function (t) { return t !== id; });
      Editor.sel = null; Store.commit();
    },
    addEdge: function (from, to) {
      var s = Editor.scn();
      if (s.edges.some(function (e) { return e.from === from && e.to === to; })) return;
      s.edges.push({ from: from, to: to, label: "" }); Store.commit();
    },
    delEdge: function (from, to) {
      var s = Editor.scn();
      s.edges = s.edges.filter(function (e) { return !(e.from === from && e.to === to); }); Store.commit();
    },
    autoLayout: function () {
      Editor.scn().nodes.forEach(function (n) { delete n.x; delete n.y; }); Store.commit();
    },
    toggleLink: function () { Editor.linkMode = !Editor.linkMode; if (Render.L) Render.L.svg.classed("linking", Editor.linkMode); Editor.renderPanel(); },

    // ===== 발표 단계 순서(tour) =====
    tourSet: function (arr) { Editor.scn().tour = arr; Store.commit(); },
    tourMove: function (i, dir) {
      var t = (Editor.scn().tour || []).slice(), j = i + dir;
      if (j < 0 || j >= t.length) return;
      var tmp = t[i]; t[i] = t[j]; t[j] = tmp; Editor.tourSet(t);
    },
    tourRemove: function (i) { var t = (Editor.scn().tour || []).slice(); t.splice(i, 1); Editor.tourSet(t); },
    tourAdd: function (id) { if (!id) return; var t = (Editor.scn().tour || []).slice(); t.push(id); Editor.tourSet(t); },

    defaultStroke: function (n) {
      var c = Render.colorFor({ type: n.type, risk: n.risk });   // 색 오버라이드 무시한 기본 등급/타입 색
      return (c.stroke && c.stroke[0] === "#") ? c.stroke : "#4ea0ff";
    },

    // ===== 패널 =====
    renderPanel: function () {
      var host = Editor.host; if (!host) return;
      host.html("");
      if (Store.mode !== "edit") return;
      var s = Editor.scn();
      host.append("h3").attr("class", "ed-h").text("✎ 시나리오 편집");

      // 메타
      var meta = host.append("div").attr("class", "ed-sec");
      Editor.field(meta, "제목", s.title, function (v) { s.title = v; Store.commit(); });
      Editor.field(meta, "요약", s.summary || "", function (v) { s.summary = v; Store.commit(); });

      host.append("div").attr("class", "ed-row").call(function (r) {
        r.append("button").attr("class", "scn-btn").text("+ 노드 추가").on("click", Editor.addNode);
        r.append("button").attr("class", "scn-btn").text("⤧ 자동정렬").on("click", Editor.autoLayout);
      });
      host.append("div").attr("class", "ed-row").call(function (r) {
        r.append("button").attr("class", "scn-btn").property("disabled", !Store.canUndo())
          .text("↶ 실행취소").on("click", function () { Store.undo(); });
        r.append("button").attr("class", "scn-btn").classed("on", Editor.linkMode)
          .text(Editor.linkMode ? "🔗 연결: 켜짐" : "🔗 연결 모드").on("click", Editor.toggleLink);
      });

      // 발표 단계 순서(→키 진행 순서) — 사용자가 직접 배열
      var ts = host.append("div").attr("class", "ed-sec");
      ts.append("div").attr("class", "ed-sub").text("▶ 발표 단계 순서 (→키 진행)");
      var tour = s.tour || [];
      if (!tour.length) ts.append("p").attr("class", "ed-hint").text("단계가 없어요. 아래에서 노드를 추가하세요.");
      tour.forEach(function (id, i) {
        var nd = Editor.node(id);
        var row = ts.append("div").attr("class", "ed-edge");
        row.append("span").attr("class", "ed-to").style("min-width", "18px").text((i + 1) + ".");
        row.append("span").style("flex", "1").style("font-size", "11.5px")
          .style("color", nd ? "var(--ink)" : "#f87171")
          .text(nd ? (id + " · " + nd.label.split("\n")[0]) : (id + " (삭제됨)"));
        row.append("button").attr("class", "ed-x").attr("title", "위로").text("↑").on("click", function () { Editor.tourMove(i, -1); });
        row.append("button").attr("class", "ed-x").attr("title", "아래로").text("↓").on("click", function () { Editor.tourMove(i, 1); });
        row.append("button").attr("class", "ed-x").attr("title", "제거").text("✕").on("click", function () { Editor.tourRemove(i); });
      });
      var tadd = ts.append("div").attr("class", "ed-edge");
      var tsel = tadd.append("select").attr("class", "ed-in");
      s.nodes.forEach(function (x) { tsel.append("option").attr("value", x.id).text(x.id + " · " + x.label.split("\n")[0]); });
      tadd.append("button").attr("class", "scn-btn").text("+ 단계").on("click", function () { Editor.tourAdd(tsel.node().value); });

      // 선택한 엣지
      if (Editor.selEdge) {
        var eb = host.append("div").attr("class", "ed-sec");
        eb.append("div").attr("class", "ed-sub").text("선택한 선: " + Editor.selEdge.from + " → " + Editor.selEdge.to);
        eb.append("button").attr("class", "scn-btn ed-del").text("✕ 선 삭제 (Delete)")
          .on("click", function () { Editor.delEdge(Editor.selEdge.from, Editor.selEdge.to); Editor.selEdge = null; });
      }

      var n = Editor.node(Editor.sel);
      if (!n) {
        host.append("p").attr("class", "ed-hint")
          .text("노드 클릭=선택 · 드래그=이동 · Shift+드래그/🔗연결모드=선 잇기 · 선 클릭 후 Delete=삭제 · ⌘/Ctrl+Z=실행취소 · 위 ▶단계 순서로 →키 진행 순서 지정");
        return;
      }

      var box = host.append("div").attr("class", "ed-sec ed-node");
      box.append("div").attr("class", "ed-sub").text("선택: " + n.id);
      Editor.field(box, "라벨(줄바꿈 \\n)", n.label, function (v) { n.label = v; Store.commit(); }, true);
      Editor.selectField(box, "타입", TYPES, n.type, function (v) { n.type = v; Store.commit(); });
      Editor.selectField(box, "위험등급", RISKS, n.risk || "none", function (v) { n.risk = v; Store.commit(); });

      // 노드 색 직접 지정(등급색 위 오버라이드)
      var cf = box.append("label").attr("class", "ed-field");
      cf.append("span").text("노드 색 (등급색 덮어쓰기)");
      var cw = cf.append("div").attr("class", "ed-color");
      cw.append("input").attr("type", "color").attr("class", "ed-in")
        .property("value", n.color || Editor.defaultStroke(n))
        .on("input", function () { n.color = this.value; Store.commit(); });
      cw.append("button").attr("class", "scn-btn").text("등급색")
        .on("click", function () { delete n.color; Store.commit(); });

      box.append("button").attr("class", "scn-btn ed-del").text("✕ 노드 삭제 (Delete)").on("click", Editor.delNode);

      // 나가는 엣지
      var es = host.append("div").attr("class", "ed-sec");
      es.append("div").attr("class", "ed-sub").text("나가는 엣지 (← 없음 / → 있음 순서)");
      var outs = s.edges.filter(function (e) { return e.from === n.id; });
      outs.forEach(function (e) {
        var row = es.append("div").attr("class", "ed-edge");
        row.append("span").attr("class", "ed-to").text("→ " + e.to);
        row.append("input").attr("class", "ed-in").attr("placeholder", "라벨").property("value", e.label || "")
          .on("change", function () { e.label = this.value; Store.commit(); });
        row.append("button").attr("class", "ed-x").text("✕").on("click", function () { Editor.delEdge(e.from, e.to); });
      });
      var add = es.append("div").attr("class", "ed-edge");
      var selTo = add.append("select").attr("class", "ed-in");
      s.nodes.filter(function (x) { return x.id !== n.id; }).forEach(function (x) {
        selTo.append("option").attr("value", x.id).text(x.id + " · " + x.label.split("\n")[0]);
      });
      add.append("button").attr("class", "scn-btn").text("+ 연결").on("click", function () {
        if (selTo.node().value) Editor.addEdge(n.id, selTo.node().value);
      });
    },

    field: function (parent, label, val, onCommit, multi) {
      var w = parent.append("label").attr("class", "ed-field");
      w.append("span").text(label);
      var inp = multi ? w.append("textarea").attr("rows", 2) : w.append("input");
      inp.attr("class", "ed-in").property("value", val).on("change", function () { onCommit(this.value); });
    },
    selectField: function (parent, label, opts, val, onCommit) {
      var w = parent.append("label").attr("class", "ed-field");
      w.append("span").text(label);
      var sel = w.append("select").attr("class", "ed-in").on("change", function () { onCommit(this.value); });
      opts.forEach(function (o) { sel.append("option").attr("value", o).property("selected", o === val).text(o); });
    }
  };

  window.Editor = Editor;
})();
