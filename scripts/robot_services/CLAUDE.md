# scripts/robot_services/

> 티원(t1) systemd 유저 서비스 원본 백업 (2026-07-08 설치, linger 활성 — 재부팅 생존).
> 4종: endpoint(:10000) / scanfix(scan_fixed restamp) / posepub(/tb3_1/pose) / bridge(Unity 순찰·출동 수신).
> 재설치: scp *.service t1:~/.config/systemd/user/ && ssh t1 'systemctl --user daemon-reload && systemctl --user enable --now urhynix-*'
> bringup/AMCL/nav2는 의도적으로 제외 — 하드웨어 초기화 순서·lifecycle 수동 절차 유지(스킬 참조).

> **readyd (2026-07-09 설치·검증됨, active+enabled)**: `readyd.py` + `urhynix-readyd.service` — "주행준비 원버튼"
> 온디맨드 트리거. Unity `/tb3_1/prepare_drive`(Bool) 수신 → `~/t1_drive_ready.sh` 1회 실행 →
> `/tb3_1/drive_ready_status`(String, latched) 진행 회신. **bringup을 상주로 만들지 않음**(버튼 시 1회 실행)이라
> 위 "수동 lifecycle 보존" 원칙과 충돌 안 함. 검증: node `/urhynix_readyd`가 prepare_drive 구독 + drive_ready_status 발행 확인.
> ⚠️ 백엔드만 배포됨 — Unity UI에 prepare_drive 발행 버튼은 아직 미바인딩(수동 트리거: `ros2 topic pub --once /tb3_1/prepare_drive std_msgs/msg/Bool "{data: true}"`).
> 재설치: `scp readyd.py t1:~/ && scp urhynix-readyd.service t1:~/.config/systemd/user/ && ssh t1 'systemctl --user daemon-reload && systemctl --user enable --now urhynix-readyd'`
