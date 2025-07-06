import os
import json
import re
import copy

root_dir = "/Users/caixiaomeng/Projects/Python/DataBuilder/data"
cleaned_dir = os.path.join(root_dir, "cleaned")
image_base = os.path.join(root_dir, "images")


input_file = "./stats/img_desc.jsonl"
output_file = "./imgs.jsonl"
refer_dict = {}

# 正则提取desc字段中的JSON块
json_block_pattern = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL)

with open(input_file, "r", encoding="utf-8") as fin, open(
    output_file, "w", encoding="utf-8"
) as fout:
    for line in fin:
        try:
            data = json.loads(line)
            path = data.get("path")
            desc_str = data.get("desc", "")

            match = json_block_pattern.search(desc_str)
            if not match:
                print(f"未找到JSON块：{desc_str}")
                continue

            inner_json_str = match.group(1)
            inner_data = json.loads(inner_json_str)
            if inner_data["filter"]:
                continue

            value = inner_data.get("details") or inner_data.get("log")
            if value is None:
                print(f"未找到details或log字段：{inner_data}")
                continue

            refer_dict[path] = value
        except Exception as e:
            print(f"处理失败：{e}\n原始行：{line}")


# 用于提取 [[IMAGE:xxx.png]] 中的 xxx.png
image_pattern = re.compile(r"\[\[IMAGE:(.*?)\]\]")

all_data = []

for dirpath, _, filenames in os.walk(cleaned_dir):
    for filename in filenames:
        if not filename.endswith(".jsonl"):
            continue
        jsonl_path = os.path.join(dirpath, filename)
        rel_path = os.path.relpath(dirpath, cleaned_dir)

        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    new_data = copy.deepcopy(data)
                    content = data.get("content", "")
                    matches = image_pattern.findall(content)
                    replaced = 0
                    for img_name in matches:
                        img_path = os.path.join(image_base, rel_path, img_name)
                        if img_path in refer_dict:
                            img_replace_symbol = f"[[IMAGE:{img_name}]]"
                            img_explained = refer_dict[img_path]
                            if isinstance(img_explained, dict):
                                img_explained = "\n".join([k+":"+v for k, v in img_explained.items()])
                            content = content.replace(img_replace_symbol, img_explained)
                            replaced += 1
                    if replaced != len(matches):
                        continue
                    new_data["content"] = content
                    all_data.append(new_data)
                except json.JSONDecodeError:
                    print(f"Error decoding line in {jsonl_path}")

with open("./data/cleaned_all.jsonl", "w", encoding="utf-8") as f:
    for item in all_data:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")
