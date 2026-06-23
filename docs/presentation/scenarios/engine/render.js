// 렌더러 — dagre 로 좌표 계산 → D3 SVG 그리기. 노드에 수동 좌표(x,y)가 있으면 그 위치로 오버라이드(에디터 드래그).
// 전역: window.Render. 의존: dagre, d3. 그린 뒤 모델을 Render.L 에 보관(nav/editor 가 조회·바인딩).
(function () {
  "use strict";

  var RISK_COLOR = {
    safe:   { fill: "#0f2e22", stroke: "#2bb673", text: "#9be7c4" },
    watch:  { fill: "#33290a", stroke: "#f5c518", text: "#f7e08a" },
    check:  { fill: "#3a230c", stroke: "#f58220", text: "#f9c08a" },
    danger: { fill: "#3a1414", stroke: "#e23b3b", text: "#f5a3a3" },
    evac:   { fill: "#2a0808", stroke: "#8b1a1a", text: "#ff7b7b" },
    none:   { fill: "#16202c", stroke: "#3a4b5e", text: "#cdd9e5" }
  };
  var TYPE_STYLE = {
    start:    { fill: "#10243a", stroke: "#4ea0ff", text: "#bcd9ff" },
    end:      { fill: "#241038", stroke: "#a06bff", text: "#d6bcff" },
    decision: { fill: "#1d1a0e", stroke: "#cdb24a", text: "#ecdc9a" }
  };
  var CHAR_W = 8.0, LINE_H = 18, PAD_X = 18, PAD_Y = 14;

  function nodeBox(n) {
    var lines = String(n.label).split("\n");
    var maxLen = lines.reduce(function (m, l) { return Math.max(m, l.length); }, 0);
    var w = Math.max(120, maxLen * CHAR_W + PAD_X * 2);
    var h = lines.length * LINE_H + PAD_Y * 2;
    if (n.type === "decision") { w += 36; h += 24; }
    return { w: w, h: h, lines: lines };
  }
  function tint(hex) {
    var c = String(hex).replace("#", "");
    if (c.length === 3) c = c[0] + c[0] + c[1] + c[1] + c[2] + c[2];
    var r = parseInt(c.substr(0, 2), 16), g = parseInt(c.substr(2, 2), 16), b = parseInt(c.substr(4, 2), 16);
    if (isNaN(r) || isNaN(g) || isNaN(b)) return "#16202c";
    return "rgba(" + r + "," + g + "," + b + ",0.18)";
  }
  function colorFor(n) {
    if (n.color) return { fill: tint(n.color), stroke: n.color, text: n.color };   // 사용자 색 오버라이드
    if (n.type === "start") return TYPE_STYLE.start;
    if (n.type === "end") return TYPE_STYLE.end;
    if (n.type === "decision") return TYPE_STYLE.decision;
    return RISK_COLOR[n.risk] || RISK_COLOR.none;
  }
  function diamondPath(w, h) {
    var x = w / 2, y = h / 2;
    return "M0," + (-y) + " L" + x + ",0 L0," + y + " L" + (-x) + ",0 Z";
  }
  function roundRectPath(w, h, r) {
    var x = -w / 2, y = -h / 2;
    r = Math.min(r, h / 2, w / 2);
    return "M" + (x + r) + "," + y +
      " h" + (w - 2 * r) + " a" + r + "," + r + " 0 0 1 " + r + "," + r +
      " v" + (h - 2 * r) + " a" + r + "," + r + " 0 0 1 " + (-r) + "," + r +
      " h" + (-(w - 2 * r)) + " a" + r + "," + r + " 0 0 1 " + (-r) + "," + (-r) +
      " v" + (-(h - 2 * r)) + " a" + r + "," + r + " 0 0 1 " + r + "," + (-r) + " Z";
  }
  // 노드 사각 경계에서 (tx,ty) 방향으로 나가는 점 (수동 위치 엣지 클립용)
  function borderPoint(nd, tx, ty) {
    var dx = tx - nd.x, dy = ty - nd.y;
    if (dx === 0 && dy === 0) return { x: nd.x, y: nd.y };
    var hw = nd.width / 2 + 2, hh = nd.height / 2 + 2;
    var sx = dx === 0 ? Infinity : hw / Math.abs(dx);
    var sy = dy === 0 ? Infinity : hh / Math.abs(dy);
    var s = Math.min(sx, sy);
    return { x: nd.x + dx * s, y: nd.y + dy * s };
  }

  var Render = {
    L: null,
    colorFor: colorFor,

    layout: function (scn) {
      var g = new dagre.graphlib.Graph({ multigraph: true });
      g.setGraph({ rankdir: "TB", nodesep: 45, ranksep: 55, marginx: 24, marginy: 24 });
      g.setDefaultEdgeLabel(function () { return {}; });
      scn.nodes.forEach(function (n) {
        var b = nodeBox(n);
        g.setNode(n.id, { width: b.w, height: b.h, lines: b.lines, ref: n });
      });
      scn.edges.forEach(function (e, i) {
        g.setEdge(e.from, e.to, { label: e.label || "", ref: e }, "e" + i);
      });
      dagre.layout(g);
      // 수동 좌표 오버라이드
      var moved = {};
      scn.nodes.forEach(function (n) {
        if (typeof n.x === "number" && typeof n.y === "number") {
          var nd = g.node(n.id); nd.x = n.x; nd.y = n.y; moved[n.id] = true;
        }
      });
      // 경계 박스 재계산(수동 노드 포함)
      var minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
      g.nodes().forEach(function (id) {
        var nd = g.node(id);
        minX = Math.min(minX, nd.x - nd.width / 2); maxX = Math.max(maxX, nd.x + nd.width / 2);
        minY = Math.min(minY, nd.y - nd.height / 2); maxY = Math.max(maxY, nd.y + nd.height / 2);
      });
      var pad = 24;
      var offX = pad - minX, offY = pad - minY;
      g.nodes().forEach(function (id) { var nd = g.node(id); nd.x += offX; nd.y += offY; });
      g.edges().forEach(function (eo) {
        var ed = g.edge(eo);
        if (moved[eo.v] || moved[eo.w]) ed.points = null;   // 직선 재계산 표시
        else ed.points = ed.points.map(function (p) { return { x: p.x + offX, y: p.y + offY }; });
      });
      var gw = (maxX - minX) + pad * 2, gh = (maxY - minY) + pad * 2;
      return { g: g, gw: gw, gh: gh, moved: moved };
    },

    draw: function (scn, svgSel) {
      var lay = Render.layout(scn);
      var g = lay.g, gw = lay.gw, gh = lay.gh;
      var svg = d3.select(svgSel)
        .attr("viewBox", "0 0 " + gw + " " + gh)
        .attr("preserveAspectRatio", "xMidYMid meet");
      svg.html("");
      var defs = svg.append("defs");
      defs.append("marker").attr("id", "arrow").attr("viewBox", "0 0 10 10")
        .attr("refX", 9).attr("refY", 5).attr("markerWidth", 7).attr("markerHeight", 7)
        .attr("orient", "auto-start-reverse")
        .append("path").attr("d", "M0,0 L10,5 L0,10 z").attr("fill", "#5a6e84");

      var line = d3.line().x(function (p) { return p.x; }).y(function (p) { return p.y; }).curve(d3.curveBasis);
      var edgeEl = {};
      var eLayer = svg.append("g").attr("class", "edges");
      g.edges().forEach(function (eo) {
        var ed = g.edge(eo);
        var pts = ed.points;
        if (!pts) {  // 수동 위치 → 직선 클립
          var a = g.node(eo.v), b = g.node(eo.w);
          var p1 = borderPoint(a, b.x, b.y), p2 = borderPoint(b, a.x, a.y);
          pts = [p1, { x: (p1.x + p2.x) / 2, y: (p1.y + p2.y) / 2 }, p2];
        }
        var path = eLayer.append("path")
          .attr("class", "scn-edge").attr("data-edge", eo.v + "->" + eo.w)
          .attr("d", line(pts)).attr("fill", "none")
          .attr("stroke", "#3a4b5e").attr("stroke-width", 2).attr("marker-end", "url(#arrow)");
        edgeEl[eo.v + "->" + eo.w] = path.node();
        if (ed.label) {
          var mid = pts[Math.floor(pts.length / 2)];
          var lg = eLayer.append("g").attr("transform", "translate(" + mid.x + "," + mid.y + ")");
          var txt = lg.append("text").attr("class", "scn-edge-label")
            .attr("text-anchor", "middle").attr("dy", "0.32em").text(ed.label);
          var bb = txt.node().getBBox();
          lg.insert("rect", "text").attr("x", bb.x - 4).attr("y", bb.y - 2)
            .attr("width", bb.width + 8).attr("height", bb.height + 4)
            .attr("rx", 4).attr("fill", "#0c141d").attr("opacity", 0.92);
        }
      });

      var nLayer = svg.append("g").attr("class", "nodes");
      var nodeSel = nLayer.selectAll("g.scn-node").data(g.nodes(), function (d) { return d; }).enter()
        .append("g").attr("class", "scn-node").attr("data-id", function (id) { return id; })
        .attr("transform", function (id) { var nd = g.node(id); return "translate(" + nd.x + "," + nd.y + ")"; });
      nodeSel.each(function (id) {
        var nd = g.node(id), n = nd.ref, c = colorFor(n);
        var sel = d3.select(this);
        var shape = n.type === "decision"
          ? sel.append("path").attr("d", diamondPath(nd.width, nd.height))
          : sel.append("path").attr("d", roundRectPath(nd.width, nd.height, n.type === "end" ? nd.height / 2 : 12));
        shape.attr("class", "scn-shape").attr("fill", c.fill).attr("stroke", c.stroke).attr("stroke-width", 2);
        var startY = -((nd.lines.length - 1) * LINE_H) / 2;
        var txt = sel.append("text").attr("text-anchor", "middle").attr("fill", c.text).attr("class", "scn-node-text");
        nd.lines.forEach(function (ln, k) {
          txt.append("tspan").attr("x", 0).attr("y", startY + k * LINE_H).attr("dy", "0.32em").text(ln);
        });
      });

      var pulse = svg.append("circle").attr("class", "scn-pulse")
        .attr("r", 6).attr("fill", "#ffe27a").attr("opacity", 0)
        .style("filter", "drop-shadow(0 0 6px #ffd54a)");

      Render.L = { g: g, gw: gw, gh: gh, svg: svg, nodeSel: nodeSel, edgeEl: edgeEl, pulse: pulse };
      return Render.L;
    },

    // 노드 중심/크기 조회
    nodeMeta: function (id) { return Render.L && Render.L.g.node(id); }
  };

  window.Render = Render;
})();
