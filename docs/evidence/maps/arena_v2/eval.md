# SLAM arena 평가 — arena_v2

- 일시: 2026-06-17 11:27 KST
- 장소: 주차구역 주변 (경기장 미진입)
- 대상: 젠지(tb3_2) + LDS-03, cartographer(apt, /opt/ros/jazzy), ROS_DOMAIN_ID=210
- 매핑: 듀얼 풀스택 검증 세션 중 짧은 teleop 주행

## 정량 지표
| 지표 | 측정 | 목표 | 판정 |
|---|---|---|---|
| resolution (m/px) | 0.05 | 0.05 | PASS |
| 그리드 (px) | 58 × 57 | — | — |
| 실제 크기 (m) | 2.90 × 2.85 | 경기장 전체 | **FAIL (주변만)** |
| 벽(occupied) | 14.7% | — | — |
| 통로(free) | 38.9% | — | — |
| 미매핑(unknown) | **46.4%** | < 20% | **FAIL** |
| origin | [-2.037, -0.990, 0] | — | — |

## 정성 평가 / 근본 원인
- 주행 거리 짧음 + 경기장 미진입 → unknown 46.4%.
- **근본 한계 (arena_v1 2026-05-29 평가와 동일)**: LDS-03 스캔 평면(~192mm 지상고) > 경기장 **가벽 높이** → 낮은 가벽이 라이다에 안 잡힘. 주행을 늘려도 2D 라이다만으로는 가벽 매핑 불가.
- 좌표(odom/TF/map)는 정상 → Unity 로봇 위치 추적은 유효.

## 판정
- 저장·재사용 파이프라인 검증용 **베이스라인 PASS**, 경기장 맵으로는 **FAIL**.
- **권장 방향**: 2D 라이다 단독 대신 **RealSense(D435) depth 기반 3D 매핑(RTAB-Map) 또는 depth로 가벽 보강** + 디지털트윈은 height-extrusion/3D로. [[urhynix-dual-fullstack-unity]] · slam-nav2-arena-survey.

## 첨부
- arena_v2.pgm (P5, 58×57) · arena_v2.yaml · arena_v2.png

## 비고
- arena_v1(158×151, 2026-05-29)은 덮어쓰기 사고 후 git에서 복구함. 오늘 맵은 arena_v2로 분리.
