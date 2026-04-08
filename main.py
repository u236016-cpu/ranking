import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
from PIL import Image
import glob

# ------------------------
# ① 順位取得
# ------------------------
url = "https://baseball.yahoo.co.jp/npb/standings/"
headers = {"User-Agent": "Mozilla/5.0"}

res = requests.get(url, headers=headers)
res.encoding = "utf-8"

soup = BeautifulSoup(res.text, "html.parser")
tables = soup.find_all("table")

central = [row.find_all("td")[1].text.strip() for row in tables[0].find_all("tr")[1:]]
pacific = [row.find_all("td")[1].text.strip() for row in tables[1].find_all("tr")[1:]]

teams = central + pacific

# ------------------------
# ② 日付付きで保存
# ------------------------
today = datetime.now().strftime("%Y-%m-%d")

df_now = pd.DataFrame({
    "date": today,
    "rank": range(1, 13),
    "team": teams
})

file = "rank_history.csv"

if os.path.exists(file):
    df_now.to_csv(file, mode="a", header=False, index=False)
else:
    df_now.to_csv(file, index=False)

# ------------------------
# ③ フレーム画像作成
# ------------------------
os.makedirs("frames", exist_ok=True)

df_hist = pd.read_csv(file)

for date, group in df_hist.groupby("date"):
    table = group.sort_values("rank")[["rank", "team"]]

    img_path = f"frames/{date}.png"

    # シンプル画像生成
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(4,6))
    ax.axis('off')

    for i, row in table.iterrows():
        ax.text(0.1, 1 - row["rank"]/13, f"{row['rank']}位  {row['team']}", fontsize=12)

    plt.title(date)
    plt.savefig(img_path)
    plt.close()

# ------------------------
# ④ GIF作成
# ------------------------
files = sorted(glob.glob("frames/*.png"))

images = [Image.open(f) for f in files]

if images:
    images[0].save(
        "ranking.gif",
        save_all=True,
        append_images=images[1:],
        duration=800,
        loop=0
    )

print("完了")