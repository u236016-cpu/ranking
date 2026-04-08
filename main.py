import pandas as pd
import matplotlib.pyplot as plt
import requests
from bs4 import BeautifulSoup
import dataframe_image as dfi
import os
from datetime import datetime

# 日本語フォント設定（UbuntuのIPAゴシック）
plt.rcParams["font.family"] = "IPAGothic"

# ------------------------ 現在順位取得
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

# ------------------------ CSV読み込み
def load_prediction_csv(csv_path="ranking_export.csv"):
    columns = ["名前"] + [f"セ{i+1}" for i in range(6)] + [f"パ{i+1}" for i in range(6)]
    df_pred = pd.read_csv(csv_path, header=None, names=columns)
    team_replace = {
        "横浜": "DeNA",
        "ＤｅＮＡ": "DeNA",
        "DeNa": "DeNA",
        "日ハム": "日本ハム"
    }
    return df_pred.replace(team_replace)

# ------------------------ 順位表作成
def create_ranking_table_image(current_ranks, df_pred, output_path="weekly_tables/ranking_table.png"):
    names = df_pred["名前"].tolist()
    pred_matrix = df_pred.drop(columns="名前").T
    pred_matrix.columns = names
    row_labels = [f"セ{i+1}" for i in range(6)] + [f"パ{i+1}" for i in range(6)]
    pred_matrix.index = row_labels
    pred_matrix.insert(0, "現在順位", current_ranks)

    correct_counts = []
    for idx, row in df_pred.iterrows():
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
            else:
                colors.append('background-color: lightgreen' if row[col] == current_ranks[row_idx] else '')
        return colors

    counts_row = pred_matrix.loc["正解数", pred_matrix.columns[1:]]
    sorted_cols = ["現在順位"] + counts_row.sort_values(ascending=False).index.tolist()
    pred_matrix = pred_matrix[sorted_cols]

    styled = pred_matrix.style.apply(highlight_cells, axis=1)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    dfi.export(styled, output_path)
    print(f"{output_path} に保存しました")

# ------------------------ 正解数履歴
def load_or_create_score_history(csv_path="score_history.csv", current_date=None, correct_counts=None, names=None):
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
    else:
        df = pd.DataFrame()

    if current_date is None or correct_counts is None or names is None:
        return df

    new_row = pd.Series(data=correct_counts, index=names)
    new_row.name = pd.to_datetime(current_date)
    df = pd.concat([df, new_row.to_frame().T])
    df = df[~df.index.duplicated(keep='last')]
    df.sort_index(inplace=True)
    df.to_csv(csv_path)
    print(f"{csv_path} を更新しました")
    return df

# ------------------------ 正解数推移グラフ
def create_score_history_plot(df_score_history, output_path="score_history_plot.png"):
    fig, ax = plt.subplots(figsize=(10,5))
    for user in df_score_history.columns:
        ax.plot(df_score_history.index, df_score_history[user], marker='o', label=user)
    ax.set_ylim(0, 12)
    ax.set_yticks(range(0,13))
    ax.set_ylabel("正解数")
    ax.set_xlabel("日付")
    ax.set_title("予想 正解数 推移")
    ax.legend(loc="upper left")
    plt.xticks(rotation=45)
    plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%m/%d"))
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    print(f"{output_path} に保存しました")

# ------------------------ メイン
def main():
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_ranks = fetch_current_ranks()
    df_pred = load_prediction_csv()
    create_ranking_table_image(current_ranks, df_pred, f"weekly_tables/ranking_table_{current_date}.png")

    names = df_pred["名前"].tolist()
    correct_counts = [
        sum([row[i+1] == current_ranks[i] for i in range(len(current_ranks))])
        for idx, row in df_pred.iterrows()
    ]

    df_score_history = load_or_create_score_history("score_history.csv", current_date, correct_counts, names)
    create_score_history_plot(df_score_history, "score_history_plot.png")

if __name__ == "__main__":
    main()
