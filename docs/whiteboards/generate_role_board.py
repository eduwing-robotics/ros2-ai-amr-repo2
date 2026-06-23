"""URHYNIX 역할 분배 보드 PNG 생성기.

두 장의 PNG를 만든다.
  1) role_matrix.png  — 모듈 × 사람 매트릭스 (한눈에 누가 어디에 들어가는지)
  2) role_graph.png   — 사람 ↔ 모듈 연결 그래프 (협업 라인)

생성된 PNG는 Confluence Whiteboard에 이미지로 드래그&드롭해서 그대로 사용 가능.
"""
from __future__ import annotations

import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import patches
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT_DIR = Path(__file__).resolve().parent

# 한글 폰트 자동 탐색
KOREAN_FONT_CANDIDATES = [
    "AppleSDGothicNeo",
    "Apple SD Gothic Neo",
    "Apple Gothic",
    "Noto Sans CJK KR",
    "NanumGothic",
    "Malgun Gothic",
]
available = {f.name for f in font_manager.fontManager.ttflist}
for name in KOREAN_FONT_CANDIDATES:
    if name in available:
        matplotlib.rcParams["font.family"] = name
        break
matplotlib.rcParams["axes.unicode_minus"] = False


PEOPLE = ["김주영", "김선일", "박태진", "임현찬"]

# 모듈명 → (담당자 리스트, 색상)
MODULES = [
    ("백엔드 DB / ROS-TCP 라벨링 / AI",
        ["김주영", "김선일"], "#4C7CF3"),
    ("아두이노 (메인 보드/통신)",
        ["박태진", "임현찬", "김주영"], "#F39C4C"),
    ("유니티 관제UI · ROS 통신 · 영상 스트림",
        ["김선일", "박태진"], "#7C4CF3"),
    ("아두이노 센서",
        ["김주영", "임현찬", "박태진"], "#4CC2F3"),
    ("터틀봇 — LiDAR · 카메라 · SLAM · 네비게이션",
        ["임현찬", "김선일"], "#21C07A"),
]

PERSON_COLOR = {
    "김주영": "#1F6FEB",
    "김선일": "#9333EA",
    "박태진": "#F59E0B",
    "임현찬": "#10B981",
}


def draw_matrix() -> Path:
    """모듈 × 사람 매트릭스 PNG."""
    n_rows = len(MODULES)
    n_cols = len(PEOPLE)

    fig, ax = plt.subplots(figsize=(15, 8), dpi=200)
    fig.patch.set_facecolor("#FAFAF7")
    ax.set_facecolor("#FAFAF7")

    cell_w, cell_h = 1.6, 1.0
    label_w = 5.0  # 모듈 라벨 박스 폭
    x0, y0 = 0.0, 0.0
    counts = {p: sum(1 for _, owners, _ in MODULES if p in owners) for p in PEOPLE}

    # 헤더 (사람) — 이름 + 모듈 수 같이 표시
    header_h = cell_h * 0.95
    for j, person in enumerate(PEOPLE):
        cx = x0 + (j + 0.5) * cell_w
        ax.add_patch(FancyBboxPatch(
            (x0 + j * cell_w + 0.06, y0 + n_rows * cell_h + 0.05),
            cell_w - 0.12, header_h,
            boxstyle="round,pad=0.02",
            linewidth=0,
            facecolor=PERSON_COLOR[person],
        ))
        ax.text(cx, y0 + n_rows * cell_h + header_h * 0.68,
                person,
                ha="center", va="center", fontsize=15,
                color="white", fontweight="bold")
        ax.text(cx, y0 + n_rows * cell_h + header_h * 0.28,
                f"모듈 {counts[person]}개",
                ha="center", va="center", fontsize=10,
                color="white", alpha=0.92)

    # 행 (모듈) + 셀
    for i, (mod_name, owners, color) in enumerate(MODULES):
        row_y = y0 + (n_rows - 1 - i) * cell_h
        # 모듈 라벨 박스 (왼쪽)
        ax.add_patch(FancyBboxPatch(
            (x0 - label_w - 0.2, row_y + cell_h * 0.05),
            label_w, cell_h * 0.9,
            boxstyle="round,pad=0.02",
            linewidth=0,
            facecolor=color, alpha=0.92,
        ))
        ax.text(x0 - label_w / 2 - 0.2, row_y + cell_h * 0.5, mod_name,
                ha="center", va="center",
                fontsize=11, color="white", fontweight="bold")

        # 셀
        for j, person in enumerate(PEOPLE):
            cell_x = x0 + j * cell_w
            assigned = person in owners
            if assigned:
                ax.add_patch(FancyBboxPatch(
                    (cell_x + 0.08, row_y + 0.08),
                    cell_w - 0.16, cell_h - 0.16,
                    boxstyle="round,pad=0.02",
                    linewidth=0,
                    facecolor=color, alpha=0.85,
                ))
                ax.text(cell_x + cell_w / 2, row_y + cell_h / 2, "●",
                        ha="center", va="center",
                        fontsize=24, color="white")
            else:
                ax.add_patch(patches.Rectangle(
                    (cell_x + 0.08, row_y + 0.08),
                    cell_w - 0.16, cell_h - 0.16,
                    linewidth=1, edgecolor="#E0DCD0",
                    facecolor="white",
                ))

    # 제목
    ax.text(x0 - label_w / 2 - 0.2,
            y0 + n_rows * cell_h + header_h + 0.45,
            "URHYNIX · 역할 분배 매트릭스",
            ha="center", va="center", fontsize=18, fontweight="bold",
            color="#222")
    ax.text(x0 + (n_cols * cell_w) / 2,
            y0 + n_rows * cell_h + header_h + 0.45,
            "● = 담당   ·   빈 칸 = 미담당",
            ha="center", va="center", fontsize=11, color="#666")

    ax.set_xlim(-label_w - 0.4, n_cols * cell_w + 0.2)
    ax.set_ylim(-0.4, n_rows * cell_h + header_h + 1.0)
    ax.set_aspect("equal")
    ax.axis("off")

    out = OUT_DIR / "role_matrix.png"
    fig.savefig(out, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return out


def draw_graph() -> Path:
    """사람 ↔ 모듈 연결 그래프 PNG."""
    fig, ax = plt.subplots(figsize=(16, 9), dpi=200)
    fig.patch.set_facecolor("#FAFAF7")
    ax.set_facecolor("#FAFAF7")

    # 사람 노드 (왼쪽) — 위에서부터 등간격
    person_gap = 1.6
    person_x = 0.0
    person_ys = {p: (len(PEOPLE) - 1 - i) * person_gap for i, p in enumerate(PEOPLE)}

    # 모듈 노드 (오른쪽)
    module_x = 8.0
    module_gap = 1.4
    module_pos = {}
    for i, (mod_name, _, _) in enumerate(MODULES):
        module_pos[mod_name] = (len(MODULES) - 1 - i) * module_gap

    # 연결선 (사람 색)
    for mod_name, owners, _ in MODULES:
        mx, my = module_x, module_pos[mod_name]
        for p in owners:
            px, py = person_x, person_ys[p]
            arrow = FancyArrowPatch(
                (px + 1.05, py), (mx - 0.05, my),
                arrowstyle="-",
                linewidth=2.4,
                color=PERSON_COLOR[p],
                alpha=0.6,
                connectionstyle="arc3,rad=0.08",
            )
            ax.add_patch(arrow)

    # 사람 노드
    counts = {p: sum(1 for _, owners, _ in MODULES if p in owners) for p in PEOPLE}
    for p, y in person_ys.items():
        ax.add_patch(FancyBboxPatch(
            (person_x - 1.0, y - 0.45),
            2.0, 0.9,
            boxstyle="round,pad=0.05",
            linewidth=0,
            facecolor=PERSON_COLOR[p],
        ))
        ax.text(person_x, y + 0.12, p,
                ha="center", va="center",
                fontsize=16, color="white", fontweight="bold")
        ax.text(person_x, y - 0.22, f"모듈 {counts[p]}개",
                ha="center", va="center",
                fontsize=10, color="white", alpha=0.92)

    # 모듈 노드
    mod_box_w = 6.4
    for mod_name, owners, color in MODULES:
        y = module_pos[mod_name]
        ax.add_patch(FancyBboxPatch(
            (module_x - 0.05, y - 0.5),
            mod_box_w, 1.0,
            boxstyle="round,pad=0.05",
            linewidth=0,
            facecolor=color, alpha=0.92,
        ))
        ax.text(module_x + mod_box_w / 2 - 0.05, y + 0.18, mod_name,
                ha="center", va="center",
                fontsize=12, color="white", fontweight="bold")
        ax.text(module_x + mod_box_w / 2 - 0.05, y - 0.22,
                "담당: " + ", ".join(owners),
                ha="center", va="center",
                fontsize=10, color="white", alpha=0.95)

    # 제목/범례
    top_y = max(person_ys.values())
    ax.text(person_x - 1.0, top_y + 1.4,
            "URHYNIX · 역할 분배 그래프",
            ha="left", va="center", fontsize=18, fontweight="bold", color="#222")
    ax.text(person_x - 1.0, top_y + 0.9,
            "왼쪽 = 팀원   ·   오른쪽 = 모듈   ·   선 색 = 담당 팀원",
            ha="left", va="center", fontsize=11, color="#666")

    ax.set_xlim(-1.4, module_x + mod_box_w + 0.4)
    ax.set_ylim(-1.0, top_y + 2.0)
    ax.set_aspect("equal")
    ax.axis("off")

    out = OUT_DIR / "role_graph.png"
    fig.savefig(out, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return out


if __name__ == "__main__":
    m = draw_matrix()
    g = draw_graph()
    print(f"WROTE: {m}")
    print(f"WROTE: {g}")
