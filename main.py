import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import requests
from bs4 import BeautifulSoup
import dataframe_image as dfi
import os
from datetime import datetime

# ------------------------
# 日本語フォント設定
# ------------------------
matplotlib.rcParams['font.family'] = 'Noto Sans CJK JP'
matplotlib.rcParams['axes.unicode_minus'] = False

# ------------------------
# ① 現在順位取得
# ------------------------
def fetch_current_ranks():
    url = "https://baseball.yahoo.co.jp/npb/standings/"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    res.encoding = "utf-8"
    soup = BeautifulSoup(res.text, "html.parser")
    tables = soup.find_all("table")

    central = [row.find_all("td")[1].text.strip() for row in tables[0].find_all("tr")[1:]]
    pacific = [row.find_all("td")[1].text.strip() for row in tables[1].find_all("tr")[1:]]
    return central + pacific

# ------------------------
# ② CSV読み込み
# ------------------------
def load_prediction_csv(csv_path="ranking_export.csv"):
    columns = ["名前"] + [f"セ{i+1}" for i in range(6)] + [f"パ{i+1}" for i in range(6)]
    df_pred = pd.read_csv(csv_path, header=None, names=columns)

    team_replace = {
        "横浜": "DeNA",
        "ＤｅＮＡ": "DeNA",
        "DeNa": "DeNA",
        "日ハム": "日本ハム"
    }
    df_pred = df_pred.replace(team_replace)
    return df_pred

# ------------------------
# ③ 順位表画像
# ------------------------
def create_ranking_table_image(current_ranks, df_pred, output_path, current_date):
    names = df_pred["名前"].tolist()
    pred_matrix = df_pred.drop(columns="名前").T
    pred_matrix.columns = names

    row_labels = [f"セ{i+1}" for i in range(6)] + [f"パ{i+1}" for i in range(6)]
    pred_matrix.index = row_labels

    pred_matrix.insert(0, "現在順位", current_ranks)

    # 正解数
    correct_counts = []
    for _, row in df_pred.iterrows():
        pred_list = row[1:].tolist()
        count = sum([pred_list[i] == current_ranks[i] for i in range(len(current_ranks))])
        correct_counts.append(count)

    pred_matrix.loc["正解数"] = [""] + correct_counts

    def highlight_cells(row):
        if row.name == "正解数":
            return [''] * len(row)

        colors = []
        row_idx = pred_matrix.index.get_loc(row.name)
        for col in row.index:
            if col == "現在順位":
                colors.append('')
            elif row[col] == current_ranks[row_idx]:
                colors.append('background-color: lightgreen')
            else:
                colors.append('')
        return colors

    counts_row = pred_matrix.loc["正解数", pred_matrix.columns[1:]]
    sorted_cols = ["現在順位"] + counts_row.sort_values(ascending=False).index.tolist()
    pred_matrix = pred_matrix[sorted_cols]

    caption = f"順位表（更新日: {current_date}）"
    styled = pred_matrix.style.apply(highlight_cells, axis=1).set_caption(caption)

    # フォルダ対応（ルートでもOKにする）
    dir_name = os.path.dirname(output_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    dfi.export(styled, output_path)
    print(f"{output_path} に保存しました")

# ------------------------
# ④ 履歴管理
# ------------------------
def load_or_create_score_history(csv_path, current_date, correct_counts, names):
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
    else:
        df = pd.DataFrame()

    new_row = pd.Series(data=correct_counts, index=names)
    new_row.name = pd.to_datetime(current_date)

    df = pd.concat([df, new_row.to_frame().T])
    df = df[~df.index.duplicated(keep='last')]
    df.sort_index(inplace=True)
    df.to_csv(csv_path)

    return df

# ------------------------
# ⑤ グラフ
# ------------------------
def create_score_history_plot(df, output_path, current_date):
    import matplotlib.dates as mdates

    df.index = pd.to_datetime(df.index)

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = plt.cm.tab20.colors

    for i, user in enumerate(df.columns):
        color = colors[i % 20]
        ax.plot(df.index, df[user], marker='o', color=color, label=user)
        ax.text(df.index[-1], df[user].iloc[-1], str(df[user].iloc[-1]),
                fontsize=9, color=color)

    ax.set_ylim(0, 12)
    ax.set_yticks(range(13))
    ax.set_title(f"予想 正解数 推移（更新日: {current_date}）")
    ax.legend()

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))

    plt.xticks(rotation=45)
    plt.grid()
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

    print(f"{output_path} に保存しました")

# ------------------------
# メイン
# ------------------------
def main():
    current_date = datetime.now().strftime("%Y-%m-%d")

    current_ranks = fetch_current_ranks()
    df_pred = load_prediction_csv()

    # ★ ルートに1枚だけ保存
    ranking_path = "ranking_table.jpeg"
    create_ranking_table_image(current_ranks, df_pred, ranking_path, current_date)

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

    create_score_history_plot(
        df_history,
        "score_history_plot.jpeg",
        current_date
    )

if __name__ == "__main__":
    main()
