from datetime import datetime
import os

png_dir = "weekly_tables"
gif_file = "score.gif"
readme_file = "README.md"

# 最新 PNG を取得
png_files = [f for f in os.listdir(png_dir) if f.endswith(".png")]
latest_png = sorted(png_files)[-1]

# README に埋め込む Markdown
content = f"""
# 観戦コンテンツ

## 最新順位表
![順位表]({png_dir}/{latest_png})

## 予想スコア推移
![スコア推移]({gif_file})
"""

# 更新
with open(readme_file, "w", encoding="utf-8") as f:
    f.write(content)

print(f"README.md を更新しました（{latest_png} + {gif_file}）")
