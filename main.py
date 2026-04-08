import pandas as pd
import requests
from bs4 import BeautifulSoup
import dataframe_image as dfi
import os
from datetime import datetime
import matplotlib.pyplot as plt
from PIL import Image
import glob

# ------------------------
# 日本語フォント対応
# ------------------------
plt.rcParams['font.family'] = 'IPAGothic'

# ------------------------
# ディレクトリ作成
# ------------------------
os.makedirs("weekly_tables", exist_ok=True)
os.makedirs("score_frames", exist_ok=True)

# ------------------------
# ① 現在順位取得
# ------------------------
url = "https://baseball.yahoo.co.jp/npb/standings/"
res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
res.encoding = "utf-8"
soup = BeautifulSoup(res.text, "html.parser")
tables = soup.find_all("table")
central = [row.find_all("td")[1].text.strip() for row in tables[0].find_all("tr")[1:]]
pacific = [row.find_all("td")[1].text.strip() for row in tables[1].find_all("tr")[1:]]
current_ranks = central + pacific

# ------------------------
# ② CSV読み込み（ヘッダーなし）
# ------------------------
columns = ["名前"] + [f"セ{i+1}" for i in range(6)] + [f"パ{i+1}" for i in range(6)]
df_pred = pd.read_csv("ranking_export.csv", header=None, names=columns)

# ------------------------
# ③ チーム名を正規化
# ------------------------
team_replace = {
    "横浜": "DeNA",
    "ＤｅＮＡ": "DeNA",
    "DeNa": "DeNA",
    "日ハム": "日本ハム"
}
df_pred = df_pred.replace(team_replace)

# ------------------------
# ④ データ整形
# ------------------------
names = df_pred["名前"].tolist()
pred_matrix = df_pred.drop(columns="名前").T
pred_matrix.columns = names
row_labels = [f"セ{i+1}" for i in range(6)] + [f"パ{i+1}" for i in range(6)]
pred_matrix.index = row_labels

# ------------------------
# ⑤ 現在順位列追加
# ------------------------
pred_matrix.insert(0, "現在順位", current_ranks)

# ------------------------
# ⑥ 正解数計算
# ------------------------
correct_counts = []
for col in pred_matrix.columns[1:]:
    count = sum(pred_matrix[col] == current_ranks)
    correct_counts.append(count)
pred_matrix.loc["正解数"] = [""] + correct_counts

# ------------------------
# ⑦ 正解ハイライト関数
# ------------------------
def highlight_cells(row):
    if row.name == "正解数":
        return [''] * len(row)
    colors = []
    row_idx = pred_matrix.index.get_loc(row.name)
    for col in row.index:
        if col == "現在順位":
            colors.append('')
        else:
            if row[col] == current_ranks[row_idx]:
                colors.append('background-color: lightgreen')
            else:
                colors.append('')
    return colors

# ------------------------
# ⑧ PNG 出力（上段表）
# ------------------------
today = datetime.now().strftime("%Y-%m-%d")
png_path = f"weekly_tables/ranking_table_{today}.png"
styled = pred_matrix.style.apply(highlight_cells, axis=1)
dfi.export(styled, png_path)
print(f"{png_path} に保存しました")

# ------------------------
# ⑨ 累積スコア計算
# ------------------------
# CSV 形式で履歴を保存しておく
history_file = "score_history.csv"
score_rows = []
for col in pred_matrix.columns[1:]:
    score = sum(pred_matrix[col] == current_ranks)
    score_rows.append({"date": today, "name": col, "score": score})

df_score_new = pd.DataFrame(score_rows)
if os.path.exists(history_file):
    df_score_history = pd.read_csv(history_file)
    df_score = pd.concat([df_score_history, df_score_new], ignore_index=True)
else:
    df_score = df_score_new

df_score["cum"] = df_score.groupby("name")["score"].cumsum()
df_score.to_csv(history_file, index=False)

# ------------------------
# ⑩ スコア推移GIF生成（下段アニメ）
# ------------------------
names = df_score["name"].unique()
color_map = {name: f"C{i%10}" for i,name in enumerate(names)}

dates = sorted(df_score["date"].unique())
frame_files = []
for d in dates:
    plt.figure(figsize=(8,5))
    sub = df_score[df_score["date"] <= d]
    for name in names:
        g = sub[sub["name"] == name]
        plt.plot(g["date"], g["cum"], marker="o", label=name, color=color_map[name])
    plt.legend(bbox_to_anchor=(1.05,1))
    plt.title(f"累積スコア推移（〜{d}）")
    plt.xticks(rotation=45)
    plt.tight_layout()
    frame_path = f"score_frames/score_{d}.png"
    plt.savefig(frame_path)
    plt.close()
    frame_files.append(frame_path)

imgs = [Image.open(f) for f in frame_files]
if imgs:
    imgs[0].save("score.gif", save_all=True, append_images=imgs[1:], duration=800, loop=0)

print("score.gif に保存しました")
