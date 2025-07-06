import os
import sys
import json
from collections import defaultdict
from tqdm import tqdm
from rapidfuzz.distance import Levenshtein


def collect_folder_names(root_dir):
    """遍历目录，统计所有子文件夹名"""
    name_count = defaultdict(int)
    all_names = []

    for dirpath, dirnames, _ in os.walk(root_dir):
        for dirname in dirnames:
            name_count[dirname] += 1
            all_names.append(dirname)

    return name_count


def group_similar_names_fast(name_count, max_distance=2):
    """快速分组：使用 rapidfuzz + 长度分桶"""
    all_names = list(name_count.keys())
    length_buckets = defaultdict(list)
    visited = set()
    groups = []

    for name in all_names:
        length_buckets[len(name)].append(name)

    for name in tqdm(all_names, desc="分组中"):
        if name in visited:
            continue

        group = [name]
        visited.add(name)

        name_len = len(name)
        # 只比较长度差不超过2的 name
        candidates = []
        for delta in range(-2, 3):
            candidates.extend(length_buckets.get(name_len + delta, []))

        for other in candidates:
            if other in visited or other == name:
                continue
            if Levenshtein.distance(name, other) <= max_distance:
                group.append(other)
                visited.add(other)

        groups.append(group)
    return groups


def save_results(groups, name_count, output_path):
    result = []
    for group in groups:
        total = sum(name_count[name] for name in group)
        result.append({"group": group, "total_frequency": total})

    # ✅ 按照 total_frequency 降序排列
    result.sort(key=lambda x: x["total_frequency"], reverse=True)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n✅ 文件夹名分组结果已保存至: {output_path}")


def main(target_dir, output_path):
    name_count = collect_folder_names(target_dir)
    groups = group_similar_names_fast(name_count)
    save_results(groups, name_count, output_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python group_folder_names.py <目录路径> [输出路径]")
        sys.exit(1)

    target_dir = sys.argv[1]
    target_name = target_dir.split("/")[-1]
    output_path = (
        sys.argv[2] if len(sys.argv) >= 3 else f"./stats/{target_name}_dir.json"
    )
    if not os.path.isdir(target_dir):
        print(f"错误：目录不存在 -> {target_dir}")
        sys.exit(1)

    if sys.platform.startswith("win"):
        import ctypes

        ctypes.windll.kernel32.SetConsoleOutputCP(65001)

    main(target_dir, output_path)
