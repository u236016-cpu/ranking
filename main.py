import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import glob
from PIL import Image
import matplotlib.pyplot as plt

# ------------------------
# 日本語フォント対応
# ------------------------
plt.rcParams['font.family'] = 'IPAGothic'

# ------------------------
# 設定
# ------------------------
TEAM_REPLACE = {
    "横浜": "DeNA",
    "ＤｅＮＡ": "DeNA",
    "DeNa": "DeNA",
    "日ハム": "日本ハム"
}

COLORS = [
    "#e41a1c","#377eb8","#4daf4a","#984ea3","#ff7f00",
    "#ffff33","#a65628","#f781bf","#999999","#66c2a5"
]

# ------------------------
# ① 順位取得
# ------------------------
url = "https://baseball.yahoo.co.jp/npb/standings/"
res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
soup = BeautifulSoup(res.text, "html.parser")

tables = soup.find_all("table")

central = [row.find_all("td")[1].text.strip() for row in tables[0].find_all("tr")[1:]]
pacific = [row.find_all("td")[1].text.strip() for row in tables[1].find_all("tr")[1:]]

teams = [TEAM_REPLACE.get(t, t) for t in (central + pacific)]

# ------------------------
# ② 履歴保存
# ------------------------
today = datetime.now().strftime("%Y-%m-%d")

df_now = pd.DataFrame({
    "date": today,
    "rank": range(1, 13),
    "team": teams
})

if os.path.exists("rank_history.csv"):
    df_now.to_csv("rank_history.csv", mode="a", header=False, index=False)
else:
    df_now.to_csv("rank_history.csv", index=False)

# ------------------------
# ③ 順位GIF用フレーム
# ------------------------
os.makedirs("frames", exist_ok=True)

df_hist = pd.read_csv("rank_history.csv")

for date, group in df_hist.groupby("date"):
    table = group.sort_values("rank")

    fig, ax = plt.subplots(figsize=(4,6))
    ax.axis('off')

    for i, row in table.iterrows():
        ax.text(0.1, 1 - row["rank"]/13,
                f"{row['rank']}位  {row['team']}",
                fontsize=12)

    plt.title(date)
    plt.savefig(f"frames/{date}.png")
    plt.close()

# GIF化
files = sorted(glob.glob("frames/*.png"))
imgs = [Image.open(f) for f in files]

if imgs:
    imgs[0].save("ranking.gif",
        save_all=True,
        append_images=imgs[1:],
        duration=600,
        loop=0
    )

# ------------------------
# ④ スコア計算
# ------------------------
columns = ["名前"] + [f"順位{i+1}" for i in range(12)]
df_pred = pd.read_csv("ranking_export.csv", header=None, names=columns)
df_pred = df_pred.replace(TEAM_REPLACE)

scores = []

for date, group in df_hist.groupby("date"):
    actual = group.sort_values("rank")["team"].tolist()

    for _, row in df_pred.iterrows():
        pred = row[1:].tolist()
        score = sum(p == a for p, a in zip(pred, actual))

        scores.append({
            "date": date,
            "name": row["名前"],
            "score": score
        })

df_score = pd.DataFrame(scores)
df_score["cum"] = df_score.groupby("name")["score"].cumsum()

# ------------------------
# ⑤ スコアGIF
# ------------------------
os.makedirs("score_frames", exist_ok=True)

names = df_score["name"].unique()
color_map = {name: COLORS[i % len(COLORS)] for i, name in enumerate(names)}

dates = sorted(df_score["date"].unique())

for d in dates:
    plt.figure(figsize=(8,5))

    sub = df_score[df_score["date"] <= d]

    for name in names:
        g = sub[sub["name"] == name]
        plt.plot(g["date"], g["cum"],
                 marker="o",
                 label=name,
                 color=color_map[name])

    plt.legend(bbox_to_anchor=(1.05,1))
    plt.title(f"スコア推移（〜{d}）")
    plt.xticks(rotation=45)
    plt.tight_layout()

    plt.savefig(f"score_frames/{d}.png")
    plt.close()

files = sorted(glob.glob("score_frames/*.png"))
imgs = [Image.open(f) for f in files]

if imgs:
    imgs[0].save("score.gif",
        save_all=True,
        append_images=imgs[1:],
        duration=800,
        loop=0
    )

print("ランキング＆スコアGIF完成！")
