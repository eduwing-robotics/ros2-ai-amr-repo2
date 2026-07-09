# scripts/robot_services/

> 티원(t1) systemd 유저 서비스 원본 백업 (2026-07-08 설치, linger 활성 — 재부팅 생존).
> 4종: endpoint(:10000) / scanfix(scan_fixed restamp) / posepub(/tb3_1/pose) / bridge(Unity 순찰·출동 수신).
> 재설치: scp *.service t1:~/.config/systemd/user/ && ssh t1 'systemctl --user daemon-reload && systemctl --user enable --now urhynix-*'
> bringup/AMCL/nav2는 의도적으로 제외 — 하드웨어 초기화 순서·lifecycle 수동 절차 유지(스킬 참조).
