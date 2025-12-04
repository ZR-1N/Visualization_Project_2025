import json
import os

# 获取当前 .py 文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# JSON 文件夹路径：当前目录下的 games 文件夹
input_dir = os.path.join(current_dir, "data2(raw)")

# 输出文件路径：当前目录
output_file = os.path.join(current_dir, "games_all.json")

all_games = []

# 遍历 games 目录，合并所有 JSON
for filename in os.listdir(input_dir):
    if filename.endswith(".json"):
        filepath = os.path.join(input_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                all_games.append(data)
            except Exception as e:
                print("读取文件出错:", filename, e)

# 输出合并后的 JSON
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(all_games, f, indent=2, ensure_ascii=False)

print(f"合并完成！共合并 {len(all_games)} 个游戏数据")
print("输出文件：", output_file)
