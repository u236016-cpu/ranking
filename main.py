import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import matplotlib.dates as mdates
import matplotlib.patheffects as pe

from matplotlib.animation import FuncAnimation

import requests
from bs4 import BeautifulSoup

import dataframe_image as dfi

import os
from datetime import datetime

# =========================================================
# 日本語フォント
# =========================================================
matplotlib.rcParams['font.family'] = 'Noto Sans CJK JP'
matplotlib.rcParams['axes.unicode_minus'] = False

# =========================================================
# DAZN風テーマ
# =========================================================
BG_COLOR = "#0A0A0A"
GRID_COLOR = "#333333"
TEXT_COLOR = "#F5F5F5"

LINE_COLORS = [
    "#00E5FF", "#00FF85", "#FFD600", "#FF6B6B", "#9C6BFF",
    "#FF9F1C", "#4D96FF", "#B6FF00", "#FF4DDA", "#FFFFFF",
]

plt.style.use("dark_background")


# =========================================================
# ① 現在順位取得
# =========================================================
def fetch_current_ranks():
    url = "https://baseball.yahoo.co.jp/npb/standings/"
    headers = {"User-Agent": "Mozilla/5.0"}

    res = requests.get(url, headers=headers)
    res.encoding = "utf-8"

    soup = BeautifulSoup(res.text, "html.parser")
    tables = soup.find_all("table")

    central = [
        row.find_all("td")[1].text.strip()
        for row in tables[0].find_all("tr")[1:]
    ]
    pacific = [
        row.find_all("td")[1].text.strip()
        for row in tables[1].find_all("tr")[1:]
    ]

    return central + pacific


# =========================================================
# ② CSV読み込み
# =========================================================
def load_prediction_csv(csv_path="ranking_export.csv"):

    columns = (
        ["名前"] +
        [f"セ{i+1}" for i in range(6)] +
        [f"パ{i+1}" for i in range(6)]
    )

    df_pred = pd.read_csv(csv_path, header=None, names=columns)

    team_replace = {
        "横浜": "DeNA",
        "ＤｅＮＡ": "DeNA",
        "DeNa": "DeNA",
        "日ハム": "日本ハム"
    }

    return df_pred.replace(team_replace)


# =========================================================
# ③ 順位表JPEG
# =========================================================
def create_ranking_table_image(current_ranks, df_pred, output_path, current_date):

    names = df_pred["名前"].tolist()

    pred_matrix = df_pred.drop(columns="名前").T
    pred_matrix.columns = names

    row_labels = [f"セ{i+1}" for i in range(6)] + [f"パ{i+1}" for i in range(6)]
    pred_matrix.index = row_labels

    pred_matrix.insert(0, "現在順位", current_ranks)

    correct_counts = []
    for _, row in df_pred.iterrows():
        pred_list = row[1:].tolist()
        correct_counts.append(
            sum(pred_list[i] == current_ranks[i] for i in range(len(current_ranks)))
        )

    pred_matrix.loc["正解数"] = [""] + correct_counts

    counts_row = pred_matrix.loc["正解数", pred_matrix.columns[1:]]
    sorted_cols = ["現在順位"] + counts_row.sort_values(ascending=False).index.tolist()
    pred_matrix = pred_matrix[sorted_cols]

    def highlight_cells(row):
        if row.name == "正解数":
            return [""] * len(row)

        colors = []
        idx = pred_matrix.index.get_loc(row.name)

        for col in row.index:
            if col == "現在順位":
                colors.append("")
            elif row[col] == current_ranks[idx]:
                colors.append("background-color: #00FF85")
            else:
                colors.append("")
        return colors

    styled = (
        pred_matrix.style
        .apply(highlight_cells, axis=1)
        .set_caption(f"順位表（更新日: {current_date}）")
    )

    dfi.export(styled, output_path)
    print(f"{output_path} に保存しました")


# =========================================================
# ④ 履歴管理
# =========================================================
def load_or_create_score_history(csv_path, current_date, correct_counts, names):

    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
    else:
        df = pd.DataFrame()

    new_row = pd.Series(
        correct_counts,
        index=names,
        name=pd.to_datetime(current_date)
    )

    df = pd.concat([df, new_row.to_frame().T])
    df = df[~df.index.duplicated(keep="last")]
    df.sort_index(inplace=True)
    df.to_csv(csv_path)

    return df


# =========================================================
# ⑤ DAZN風ラインGIF（FINALなし・1秒停止・1位強調・凡例あり）
# =========================================================
def create_dazn_style_race_chart(df_history, output_path, current_date):

    df = df_history.copy()
    df.index = pd.to_datetime(df.index)

    fig, ax = plt.subplots(figsize=(16, 9), facecolor=BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    users = df.columns.tolist()

    lines = {}
    points = {}
    labels = {}

    # 初期描画
    for i, user in enumerate(users):

        color = LINE_COLORS[i % len(LINE_COLORS)]

        line, = ax.plot([], [], linewidth=4, color=color, alpha=0.95)
        point, = ax.plot([], [], "o", color=color, markersize=12)
        label = ax.text(0, 0, "", fontsize=16, color=TEXT_COLOR, fontweight="bold")

        line.set_path_effects([
            pe.Stroke(linewidth=8, foreground=color, alpha=0.25),
            pe.Normal()
        ])

        lines[user] = line
        points[user] = point
        labels[user] = label

    # 軸設定
    ax.set_ylim(0, 12)
    ax.set_xlim(df.index.min(), df.index.max())
    ax.set_yticks(range(13))

    ax.tick_params(colors=TEXT_COLOR, labelsize=14)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))

    ax.grid(True, color=GRID_COLOR, linestyle="--", alpha=0.35)

    for spine in ax.spines.values():
        spine.set_visible(False)

    # 凡例（DAZN風・上部）
    from matplotlib.lines import Line2D

    legend_handles = [
        Line2D([0], [0], color=LINE_COLORS[i % len(LINE_COLORS)], lw=6)
        for i in range(len(users))
    ]

    legend = ax.legend(
        legend_handles,
        users,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.02),
        ncol=5,
        frameon=False,
        fontsize=12
    )

    for text in legend.get_texts():
        text.set_color(TEXT_COLOR)

    # 停止演出設定（最後1秒）
    fps = 8
    pause_seconds = 1
    extra_frames = fps * pause_seconds
    total_frames = len(df) + extra_frames

    # アニメーション更新
    def update(frame):

        actual_frame = min(frame, len(df) - 1)
        current_data = df.iloc[:actual_frame + 1]

        latest = current_data.iloc[-1].sort_values(ascending=False)
        sorted_users = latest.index.tolist()

        leader = sorted_users[0]

        for rank, user in enumerate(sorted_users):

            color = LINE_COLORS[users.index(user) % len(LINE_COLORS)]

            x = current_data.index
            y = current_data[user]

            # ライン（1位強調）
            lw = 4
            alpha = 0.95

            if user == leader:
                lw = 7
                alpha = 1.0

            lines[user].set_data(x, y)
            lines[user].set_linewidth(lw)
            lines[user].set_alpha(alpha)

            # 点（1位強調）
            points[user].set_data([x[-1]], [y.iloc[-1]])

            if user == leader:
                points[user].set_markersize(16)
            else:
                points[user].set_markersize(12)

            # ラベル
            labels[user].set_position((x[-1], y.iloc[-1]))
            labels[user].set_text(f"{rank+1}. {user} {int(y.iloc[-1])}")
            labels[user].set_color(color)

            if user == leader:
                labels[user].set_fontsize(20)
                labels[user].set_fontweight("bold")
            else:
                labels[user].set_fontsize(16)
                labels[user].set_fontweight("bold")

        return list(lines.values()) + list(points.values()) + list(labels.values())

    ani = FuncAnimation(
        fig,
        update,
        frames=total_frames,
        interval=150,
        blit=False,
        repeat=False
    )

    ani.save(output_path, writer="pillow", fps=fps)
    plt.close()

    print(f"{output_path} に保存しました")


# =========================================================
# メイン
# =========================================================
def main():

    current_date = datetime.now().strftime("%Y-%m-%d")

    current_ranks = fetch_current_ranks()
    df_pred = load_prediction_csv()

    create_ranking_table_image(
        current_ranks,
        df_pred,
        "ranking_table.jpeg",
        current_date
    )

    names = df_pred["名前"].tolist()

    correct_counts = [
        sum(row[1:].tolist()[i] == current_ranks[i] for i in range(len(current_ranks)))
        for _, row in df_pred.iterrows()
    ]

    df_history = load_or_create_score_history(
        "score_history.csv",
        current_date,
        correct_counts,
        names
    )

    create_dazn_style_race_chart(
        df_history,
        "dazn_race.gif",
        current_date
    )


if __name__ == "__main__":
    main()
