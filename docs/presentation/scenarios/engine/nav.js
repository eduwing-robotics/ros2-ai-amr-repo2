// 탐색/발표 엔진 (P0) — 좌우 분기 이동 · 자동재생 · 활성 노드 줌인 카메라 · 엣지 점 흐름 · 경로 하이라이트.
// 강조의 단일 진실원천 = Nav.path(방문 노드 순서). 수동 키와 자동재생이 모두 이 path 를 갱신한다.
// 전역: window.Nav. 의존: window.Render(L), window.Store, d3.
(function () {
  "use strict";

  var Nav = {
    path: [],
    follow: true,
    playing: false,
    timer: null,
    speed: 1400,
    loop: false,
    _k: 0,

    scn: function () { return Store.current(); },
    node: function (id) { return Nav.scn().nodes.find(function (n) { return n.id === id; }); },
    isDecision: function (id) { var n = Nav.node(id); return n && n.type === "decision"; },
    outEdges: function (id) { return Nav.scn().edges.filter(function (e) { return e.from === id; }); },
    startNode: function () {
      var s = Nav.scn();
      var st = s.nodes.find(function (n) { return n.type === "start"; });
      return st ? st.id : (s.tour && s.tour[0]) || s.nodes[0].id;
    },
    cur: function () { return Nav.path[Nav.path.length - 1]; },

    // 새 시나리오/재렌더 후 초기화
    rebind: function () { Nav.stop(); Nav.path = []; Nav.update(); Nav.camera(); },

    start: function () { Nav.path = [Nav.startNode()]; Nav.update(); Nav.camera(); },

    // → : 발표 순서(tour)를 그대로 따라간다. tour 밖/끝이면 엣지 흐름으로 폴백(분기 탐색).
    forward: function () {
      if (!Nav.path.length) return Nav.start();
      var cur = Nav.cur();
      var tour = Nav.scn().tour || [];
      var ti = tour.indexOf(cur);
      if (ti >= 0 && ti < tour.length - 1) {
        var nextId = tour[ti + 1];
        var e = Nav.outEdges(cur).find(function (x) { return x.to === nextId; });
        if (e) return Nav.go(e);
        Nav.path.push(nextId); Nav.update(); Nav.camera(); return;   // 엣지 없어도 순서 보장
      }
      var outs = Nav.outEdges(cur);
      if (!outs.length) return;
      var ed = (Nav.isDecision(cur) && outs.length >= 2) ? outs[1] : outs[0];
      Nav.go(ed);
    },
    // 결정 노드: ← = 첫 분기(없음). 일반 노드: ← = 뒤로.
    left: function () {
      if (!Nav.path.length) return Nav.start();
      var cur = Nav.cur(), outs = Nav.outEdges(cur);
      if (Nav.isDecision(cur) && outs.length >= 2) Nav.go(outs[0]);
      else Nav.back();
    },
    go: function (edge) { Nav.path.push(edge.to); Nav.update(); Nav.flow(edge.from, edge.to); Nav.camera(); },
    back: function () { if (Nav.path.length) Nav.path.pop(); Nav.update(); Nav.camera(); },

    update: function () {
      var L = Render.L; if (!L) return;
      var path = Nav.path, active = Nav.cur();
      var inPath = {}; path.forEach(function (id) { inPath[id] = true; });
      L.nodeSel
        .classed("active", function (id) { return id === active; })
        .classed("visited", function (id) { return inPath[id] && id !== active; })
        .classed("dim", function (id) { return !inPath[id]; });
      d3.selectAll(".scn-edge").classed("hot", false);
      for (var i = 0; i < path.length - 1; i++) {
        var el = L.edgeEl[path[i] + "->" + path[i + 1]];
        if (el) d3.select(el).classed("hot", true);
      }
      Nav.info();
    },

    info: function () {
      var el = d3.select(".scn-stepinfo"); if (el.empty()) return;
      if (!Nav.path.length) { el.text("→/Space 시작 · ← 분기/뒤로 · ▶ 자동재생 · 1~6 전환 · 노드 클릭 점프"); return; }
      var cur = Nav.cur(), outs = Nav.outEdges(cur);
      var tour = Nav.scn().tour || [], ti = tour.indexOf(cur);
      if (ti >= 0) {
        var branch = (Nav.isDecision(cur) && outs.length >= 2) ? " · <b>← " + (outs[0].label || "분기") + "</b>" : " · ← 뒤로";
        if (ti < tour.length - 1) el.html("단계 <b>" + (ti + 1) + " / " + tour.length + "</b> · → 다음" + branch);
        else el.html("마지막 단계 <b>" + tour.length + " / " + tour.length + "</b> · ← 뒤로 · ↺ 처음");
        return;
      }
      if (Nav.isDecision(cur) && outs.length >= 2) {
        el.html("결정 — <b>← " + (outs[0].label || "분기1") + "</b> &nbsp;|&nbsp; <b>→ " + (outs[1].label || "분기2") + "</b>");
      } else if (!outs.length) {
        el.text("종료 노드 · ← 뒤로 · ↺ 처음");
      } else {
        el.text("자유 이동 · → 다음 · ← 뒤로");
      }
    },

    flow: function (from, to) {
      var L = Render.L; var el = L && L.edgeEl[from + "->" + to];
      if (!el) return;
      var len = el.getTotalLength();
      L.pulse.interrupt().attr("opacity", 1)
        .transition().duration(620).ease(d3.easeCubicInOut)
        .attrTween("transform", function () {
          return function (t) { var p = el.getPointAtLength(t * len); return "translate(" + p.x + "," + p.y + ")"; };
        })
        .on("end", function () { L.pulse.transition().duration(160).attr("opacity", 0); });
    },

    camera: function () {
      var L = Render.L; if (!L) return;
      var svg = L.svg, full = "0 0 " + L.gw + " " + L.gh, target = full;
      if (Nav.follow && Nav.path.length) {
        var ids = Nav.path.length >= 2 ? [Nav.path[Nav.path.length - 2], Nav.cur()] : [Nav.cur()];
        var x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
        ids.forEach(function (id) {
          var nd = L.g.node(id); if (!nd) return;
          x0 = Math.min(x0, nd.x - nd.width / 2); x1 = Math.max(x1, nd.x + nd.width / 2);
          y0 = Math.min(y0, nd.y - nd.height / 2); y1 = Math.max(y1, nd.y + nd.height / 2);
        });
        var pad = 70; x0 -= pad; y0 -= pad; x1 += pad; y1 += pad;
        var w = x1 - x0, h = y1 - y0, minW = L.gw * 0.6;
        if (w < minW) { x0 -= (minW - w) / 2; w = minW; }
        x0 = Math.max(0, Math.min(x0, L.gw - w)); y0 = Math.max(0, Math.min(y0, L.gh - h));
        target = x0 + " " + y0 + " " + w + " " + h;
      }
      var cur = svg.attr("viewBox") || full;
      svg.transition("cam").duration(600).ease(d3.easeCubicInOut)
        .attrTween("viewBox", function () { return d3.interpolateString(cur, target); });
    },
    toggleFit: function () { Nav.follow = !Nav.follow; Nav.camera(); },

    jumpToNode: function (id) {
      // 시작~id 까지 tour 경로가 있으면 그 경로로, 없으면 단독 강조
      var tour = Nav.scn().tour || [];
      var idx = tour.indexOf(id);
      if (idx >= 0) { Nav.path = tour.slice(0, idx + 1); }
      else { Nav.path = [id]; }
      Nav.update(); Nav.camera();
      if (Nav.path.length >= 2) Nav.flow(Nav.path[Nav.path.length - 2], id);
    },

    // 전체 시나리오 경로(tour)를 한 번에 강조
    showFullPath: function () {
      var tour = Nav.scn().tour || [];
      if (!tour.length) return;
      Nav.stop(); Nav.path = tour.slice(); Nav.follow = false; Nav.update(); Nav.camera();
    },

    // ===== 자동재생 =====
    play: function () {
      Nav.stop(); Nav.playing = true; Nav.follow = true; Nav.path = []; Nav._k = 0;
      Nav._tick();
      Nav.timer = setInterval(Nav._tick, Nav.speed);
      Nav.emitPlay();
    },
    _tick: function () {
      var tour = Nav.scn().tour || [];
      if (Nav._k >= tour.length) {
        if (Nav.loop) { Nav.path = []; Nav._k = 0; }
        else { Nav.pause(); return; }
      }
      var id = tour[Nav._k];
      Nav.path.push(id);
      Nav.update(); Nav.camera();
      if (Nav._k > 0) Nav.flow(tour[Nav._k - 1], id);
      Nav._k++;
    },
    pause: function () { Nav.playing = false; if (Nav.timer) { clearInterval(Nav.timer); Nav.timer = null; } Nav.emitPlay(); },
    stop: function () { Nav.pause(); },
    togglePlay: function () { Nav.playing ? Nav.pause() : Nav.play(); },
    setSpeed: function (ms) { Nav.speed = ms; if (Nav.playing) { Nav.pause(); Nav.timer = setInterval(Nav._tick, Nav.speed); Nav.playing = true; Nav.emitPlay(); } },
    setLoop: function (v) { Nav.loop = v; },
    emitPlay: function () { d3.select(".scn-play").text(Nav.playing ? "⏸ 일시정지" : "▶ 자동재생").classed("on", Nav.playing); }
  };

  window.Nav = Nav;
})();
