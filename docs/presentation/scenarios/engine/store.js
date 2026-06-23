// 상태 저장소 — 작업본 시나리오(기본 + localStorage 오버라이드), 현재 선택, 편집 모드, 가져오기/내보내기.
// file:// 에선 원본 파일을 못 쓰므로(보안) 편집은 localStorage 에 저장하고, 영구 반영은 내보내기 다운로드로 한다.
// 전역: window.Store. 의존: data/scenarios.js (window.SCENARIOS, window.RISK_LEGEND).
(function () {
  "use strict";
  var LS_KEY = "urhynix.scenarios.v1";

  function clone(o) { return JSON.parse(JSON.stringify(o)); }

  var Store = {
    scenarios: null,   // 작업본(편집 대상)
    curId: null,
    mode: "present",   // present | edit
    dirty: false,
    listeners: [],
    undoStack: [],     // 실행취소 히스토리(이전 상태 스냅샷)
    _last: null,       // 직전 커밋 상태(스냅샷 소스)

    init: function () {
      var saved = null;
      try { saved = JSON.parse(localStorage.getItem(LS_KEY)); } catch (e) { saved = null; }
      Store.scenarios = (saved && Array.isArray(saved.scenarios) && saved.scenarios.length)
        ? saved.scenarios : clone(window.SCENARIOS);
      Store.curId = Store.scenarios[0].id;
      Store.dirty = !!(saved && saved.scenarios);
      Store._resetHistory();
      return Store;
    },

    _resetHistory: function () { Store.undoStack = []; Store._last = clone(Store.scenarios); },
    canUndo: function () { return Store.undoStack.length > 0; },
    undo: function () {
      if (!Store.undoStack.length) return false;
      Store.scenarios = Store.undoStack.pop();
      Store._last = clone(Store.scenarios);
      if (!Store.current()) Store.curId = Store.scenarios[0].id;
      Store.dirty = true; Store.persist(); Store.emit("data"); Store.emit("select");
      return true;
    },

    on: function (fn) { Store.listeners.push(fn); },
    emit: function (kind) { Store.listeners.forEach(function (fn) { fn(kind); }); },

    list: function () { return Store.scenarios; },
    current: function () { return Store.scenarios.find(function (s) { return s.id === Store.curId; }); },
    index: function () { return Store.scenarios.findIndex(function (s) { return s.id === Store.curId; }); },
    select: function (id) { Store.curId = id; Store.emit("select"); },
    selectIndex: function (i) {
      var s = Store.scenarios[i]; if (s) Store.select(s.id);
    },

    setMode: function (m) { Store.mode = m; Store.emit("mode"); },
    toggleMode: function () { Store.setMode(Store.mode === "edit" ? "present" : "edit"); },

    // 편집 후 호출 — 직전 상태를 undo 스택에 적재 + 화면 갱신 + 자동 저장.
    commit: function () {
      if (Store._last) { Store.undoStack.push(Store._last); if (Store.undoStack.length > 50) Store.undoStack.shift(); }
      Store._last = clone(Store.scenarios);
      Store.dirty = true; Store.persist(); Store.emit("data");
    },
    persist: function () {
      try { localStorage.setItem(LS_KEY, JSON.stringify({ scenarios: Store.scenarios, savedAt: Date.now() })); }
      catch (e) { /* 용량 초과 등 무시 */ }
    },

    resetToDefault: function () {
      Store.scenarios = clone(window.SCENARIOS);
      Store.curId = Store.scenarios[0].id;
      Store.dirty = false;
      try { localStorage.removeItem(LS_KEY); } catch (e) {}
      Store._resetHistory();
      Store.emit("data"); Store.emit("select");
    },

    exportJSON: function () {
      var blob = new Blob([JSON.stringify({ scenarios: Store.scenarios }, null, 2)], { type: "application/json" });
      var url = URL.createObjectURL(blob);
      var a = document.createElement("a");
      a.href = url; a.download = "scenarios.export.json"; a.click();
      setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
    },

    importJSON: function (file, done) {
      var r = new FileReader();
      r.onload = function () {
        try {
          var obj = JSON.parse(r.result);
          var arr = Array.isArray(obj) ? obj : obj.scenarios;
          if (!Array.isArray(arr) || !arr.length) throw new Error("scenarios 배열 없음");
          Store.scenarios = arr; Store.curId = arr[0].id; Store._resetHistory(); Store.commit(); Store.emit("select");
          done && done(null);
        } catch (e) { done && done(e); }
      };
      r.readAsText(file);
    }
  };

  window.Store = Store;
})();
