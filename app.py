import streamlit as st
import matplotlib.pyplot as plt
from mplsoccer import Pitch
import pandas as pd
import numpy as np
from PIL import Image
from io import BytesIO
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch
from streamlit_image_coordinates import streamlit_image_coordinates

# ==========================
# Page Configuration
# ==========================
st.set_page_config(layout="wide", page_title="Pass Map Dashboard (Interactive)")
st.title("Pass Map Dashboard")
st.caption("Clique na bolinha no início do passe para ver o vídeo (se houver).")

# ==========================
# Configuration
# ==========================
FINAL_THIRD_LINE_X = 80

# Box dimensions for StatsBomb pitch
BOX_X_MIN = 102
BOX_Y_MIN = 18
BOX_Y_MAX = 62

# ==========================
# DATA
# ==========================
matches_data = {
    "Vs Connecticut": [
        ("PASS WON", 41.05, 44.99, 32.74, 63.94, None),
        ("PASS WON", 25.26, 26.70, 15.95, 11.08, None),

        ("PASS LOST", 68.81, 44.32, 47.20, 32.19, None),
        ("PASS LOST", 59.34, 37.84, 39.72, 35.51, None),
        ("PASS LOST", 46.20, 52.80, 27.75, 44.99, None),
        ("PASS LOST", 42.05, 66.43, 31.24, 58.45, None),
        ("PASS LOST", 23.26, 63.44, 14.78, 48.31, None),
        ("PASS LOST", 71.14, 75.24, 36.56, 73.91, None),
        ("PASS LOST", 35.73, 3.93, 12.79, 32.52, None),
    ],
    "Vs Nashville": [
        ("PASS WON", 89.42, 33.68, 95.41, 38.34, None),
        ("PASS WON", 118.51, 9.08, 107.38, 4.76, None),
        ("PASS WON", 67.31, 21.71, 88.76, 22.05, None),

        ("PASS LOST", 67.48, 25.70, 98.90, 26.70, None),
        ("PASS LOST", 38.22, 34.02, 80.45, 30.69, None),
    ],
    "Vs Seongnam": [
        ("PASS WON", 74.79, 19.55, 110.04, 19.22, None),
        ("PASS WON", 91.58, 66.43, 95.24, 52.30, None),
        ("PASS WON", 111.86, 56.46, 112.86, 68.76, None),
        ("PASS WON", 117.52, 72.58, 109.21, 52.47, None),
    ],
    "Vs Red Bull": [
        ("PASS WON", 78.29, 14.90, 69.14, 22.05, None),
        ("PASS WON", 62.49, 40.83, 81.44, 14.07, None),

        ("PASS LOST", 39.72, 44.82, 86.26, 43.82, None),
        ("PASS LOST", 78.12, 19.89, 86.26, 24.37, None),
        ("PASS LOST", 96.74, 11.41, 106.38, 7.75, None),
        ("PASS LOST", 108.71, 58.95, 117.85, 44.32, None),
    ],
    "Vs Seattle": [
        ("PASS WON", 50.19, 10.08, 55.18, 1.93, None),
        ("PASS WON", 84.94, 60.95, 91.09, 74.41, None),
        ("PASS WON", 76.96, 71.92, 117.68, 59.28, None),
    ],
}

# ==========================
# Build DataFrames
# ==========================
dfs_by_match = {}
for match_name, events in matches_data.items():
    dfm = pd.DataFrame(
        events,
        columns=["type", "x_start", "y_start", "x_end", "y_end", "video"]
    )
    dfm["numero"] = np.arange(1, len(dfm) + 1)
    dfm["match"] = match_name
    dfs_by_match[match_name] = dfm

df_all = pd.concat(dfs_by_match.values(), ignore_index=True)
full_data = {"All Matches": df_all}
full_data.update(dfs_by_match)

# ==========================
# Helpers
# ==========================
def has_video_value(v) -> bool:
    return pd.notna(v) and str(v).strip() != ""

def compute_stats(df: pd.DataFrame) -> dict:
    total_passes = len(df)
    successful = int(df["type"].str.contains("WON", case=False).sum())
    unsuccessful = int(df["type"].str.contains("LOST", case=False).sum())
    accuracy = (successful / total_passes * 100.0) if total_passes else 0.0

    in_final_third = df["x_end"] >= FINAL_THIRD_LINE_X
    final_third_total = int(in_final_third.sum())
    final_third_success = int((in_final_third & df["type"].str.contains("WON", case=False)).sum())
    final_third_unsuccess = int((in_final_third & df["type"].str.contains("LOST", case=False)).sum())
    final_third_accuracy = (final_third_success / final_third_total * 100.0) if final_third_total else 0.0

    to_box = (
        (df["x_end"] >= BOX_X_MIN) &
        (df["y_end"] >= BOX_Y_MIN) &
        (df["y_end"] <= BOX_Y_MAX)
    )
    box_total = int(to_box.sum())
    box_success = int((to_box & df["type"].str.contains("WON", case=False)).sum())
    box_unsuccess = int((to_box & df["type"].str.contains("LOST", case=False)).sum())
    box_accuracy = (box_success / box_total * 100.0) if box_total else 0.0

    return {
        "total_passes": total_passes,
        "successful_passes": successful,
        "unsuccessful_passes": unsuccessful,
        "accuracy_pct": round(accuracy, 2),
        "assists": 1,
        "final_third_total": final_third_total,
        "final_third_success": final_third_success,
        "final_third_unsuccess": final_third_unsuccess,
        "final_third_accuracy_pct": round(final_third_accuracy, 2),
        "box_total": box_total,
        "box_success": box_success,
        "box_unsuccess": box_unsuccess,
        "box_accuracy_pct": round(box_accuracy, 2),
    }

# ==========================
# Draw pass map
# ==========================
def draw_pass_map(df: pd.DataFrame, title: str):
    pitch = Pitch(pitch_type="statsbomb", pitch_color="#f5f5f5", line_color="#4a4a4a")
    fig, ax = pitch.draw(figsize=(7.9, 5.3))
    fig.set_dpi(110)

    ax.axvline(x=FINAL_THIRD_LINE_X, color="#FFD54F", linewidth=1.2, alpha=0.25)

    START_DOT_SIZE = 45

    for _, row in df.iterrows():
        is_lost = "LOST" in row["type"].upper()
        has_vid = has_video_value(row["video"])

        if is_lost:
            color = (0.95, 0.18, 0.18, 0.65)
        else:
            color = (0.18, 0.8, 0.18, 0.65)

        pitch.arrows(
            row["x_start"], row["y_start"],
            row["x_end"], row["y_end"],
            color=color,
            width=1.55,
            headwidth=2.25,
            headlength=2.25,
            ax=ax,
            zorder=3,
        )

        if has_vid:
            pitch.scatter(
                row["x_start"], row["y_start"],
                s=95,
                marker="o",
                facecolors="none",
                edgecolors="#FFD54F",
                linewidths=2.0,
                ax=ax,
                zorder=4,
            )

        pitch.scatter(
            row["x_start"], row["y_start"],
            s=START_DOT_SIZE,
            marker="o",
            color=color,
            edgecolors="white",
            linewidths=0.8,
            ax=ax,
            zorder=5,
        )

    ax.set_title(title, fontsize=12)

    legend_elements = [
        Line2D([0], [0], color=(0.18, 0.8, 0.18, 0.65), lw=2.5, label="Successful Pass"),
        Line2D([0], [0], color=(0.95, 0.18, 0.18, 0.65), lw=2.5, label="Unsuccessful Pass"),
        Line2D([0], [0], marker="o", color="w",
               markerfacecolor="gray", markeredgecolor="white",
               markersize=6, label="Start point (click)"),
        Line2D([0], [0], marker="o", color="w",
               markerfacecolor="gray", markeredgecolor="#FFD54F",
               markeredgewidth=2, markersize=7, label="Has video"),
    ]
    legend = ax.legend(
        handles=legend_elements,
        loc="upper left",
        bbox_to_anchor=(0.01, 0.99),
        frameon=True,
        facecolor="white",
        edgecolor="#cccccc",
        shadow=False,
        fontsize="x-small",
        labelspacing=0.5,
        borderpad=0.5,
    )
    legend.get_frame().set_alpha(1.0)

    arrow = FancyArrowPatch(
        (0.45, 0.05),
        (0.55, 0.05),
        transform=fig.transFigure,
        arrowstyle="-|>",
        mutation_scale=15,
        linewidth=2,
        color="#333333",
    )
    fig.patches.append(arrow)
    fig.text(
        0.5,
        0.02,
        "Attack Direction",
        ha="center",
        va="center",
        fontsize=9,
        color="#333333",
    )

    fig.tight_layout()

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    buf.seek(0)
    img_obj = Image.open(buf)
    return img_obj, ax, fig

# ==========================
# Sidebar
# ==========================
st.sidebar.header("Match selection")
selected_match = st.sidebar.radio("Choose the match", list(full_data.keys()), index=0)

st.sidebar.header("Pass filter")
pass_filter = st.sidebar.radio(
    "Filter passes",
    ["All Passes", "Successful Only", "Unsuccessful Only"],
    index=0
)

df = full_data[selected_match].copy()

if pass_filter == "Successful Only":
    df = df[df["type"].str.contains("WON", case=False)].reset_index(drop=True)
elif pass_filter == "Unsuccessful Only":
    df = df[df["type"].str.contains("LOST", case=False)].reset_index(drop=True)

stats = compute_stats(df)

# ==========================
# Layout
# ==========================
col_stats, col_right = st.columns([1, 2], gap="large")

with col_stats:
    st.subheader("Statistics")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Passes", stats["total_passes"])
    c2.metric("Successful", stats["successful_passes"])
    c3.metric("Accuracy", f'{stats["accuracy_pct"]:.1f}%')
    c4.metric("Assists", stats["assists"])

    st.divider()

    st.subheader("Final Third")
    c7, c8, c9 = st.columns(3)
    c7.metric("Total", stats["final_third_total"])
    c8.metric("Successful", stats["final_third_success"])
    c9.metric("Unsuccessful", stats["final_third_unsuccess"])
    st.metric("Accuracy", f'{stats["final_third_accuracy_pct"]:.1f}%')

    st.divider()

    st.subheader("Passes to the Box")
    d1, d2, d3 = st.columns(3)
    d1.metric("Total", stats["box_total"])
    d2.metric("Successful", stats["box_success"])
    d3.metric("Unsuccessful", stats["box_unsuccess"])
    st.metric("Accuracy", f'{stats["box_accuracy_pct"]:.1f}%')

with col_right:
    st.subheader("Pass Map (click the start dot)")

    img_obj, ax, fig = draw_pass_map(df, title=f"Pass Map - {selected_match}")
    click = streamlit_image_coordinates(img_obj, width=780)

    selected_pass = None

    if click is not None:
        real_w, real_h = img_obj.size
        disp_w, disp_h = click["width"], click["height"]

        pixel_x = click["x"] * (real_w / disp_w)
        pixel_y = click["y"] * (real_h / disp_h)

        mpl_pixel_y = real_h - pixel_y
        coords_clicked = ax.transData.inverted().transform((pixel_x, mpl_pixel_y))
        field_x, field_y = coords_clicked[0], coords_clicked[1]

        df_sel = df.copy()
        df_sel["dist"] = np.sqrt(
            (df_sel["x_start"] - field_x) ** 2 +
            (df_sel["y_start"] - field_y) ** 2
        )

        RADIUS = 7.0
        candidates = df_sel[df_sel["dist"] < RADIUS].copy()

        if not candidates.empty:
            candidates["has_video"] = candidates["video"].apply(has_video_value)
            candidates = candidates.sort_values(
                by=["has_video", "dist"],
                ascending=[False, True]
            )
            selected_pass = candidates.iloc[0]

    plt.close(fig)

    st.divider()
    st.subheader("Video")

    if selected_pass is None:
        st.info("Clique na bolinha no início do passe para ver o vídeo (se houver).")
    else:
        st.success(
            f"Selected pass: #{int(selected_pass['numero'])} "
            f"({selected_pass['type']}) - {selected_pass['match']}"
        )
        st.write(
            f"Start: ({selected_pass['x_start']:.2f}, {selected_pass['y_start']:.2f})  \n"
            f"End: ({selected_pass['x_end']:.2f}, {selected_pass['y_end']:.2f})"
        )

        if has_video_value(selected_pass["video"]):
            try:
                st.video(selected_pass["video"])
            except Exception:
                st.error(f"Video file not found: {selected_pass['video']}")
        else:
            st.warning("Não há vídeo carregado para este evento.")
