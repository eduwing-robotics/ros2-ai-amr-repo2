# vendor/

> URHYNIX가 의존하는 외부 도구/플러그인의 영구 스냅샷. git 추적 대상.

## 무엇이 들어가는가

- `unityctl-plugin/` — [Jason-hub-star/unityctl](https://github.com/Jason-hub-star/unityctl) 0.2.0 미러 (`.git` 제외). Unity Editor IPC 자동화용. `unity/ControlRoom/Packages/manifest.json`에서 `file:../../../vendor/unityctl-plugin/src/Unityctl.Plugin`로 참조.

## 왜 vendor에 박나

- `/tmp/`는 macOS 재부팅 시 휘발 → 매 세션마다 Editor IPC 죽음.
- 외부 도구라 `Packages/`(Unity 자동 관리)에 직접 두지 않음.
- 절대경로 회피 → repo clone 시 즉시 동작.

## 갱신 절차

```bash
rsync -a --exclude='.git' /path/to/upstream-clone/ vendor/<tool>/
```

원본 repo는 별도 clone 위치 유지. vendor/는 read-only 스냅샷.
