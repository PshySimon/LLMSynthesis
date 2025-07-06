import os
import json
import glob
import shutil
import requests
from tqdm import tqdm
from PIL import Image
import imagehash
from pathlib import Path
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Tuple
from utils.prompts import IMG_PROMPT
from utils.llm import QwenVLPipeline

domain_map = {
    "ascend": "https://www.hiascend.com/",
    "kunpeng": "https://www.hikunpeng.com/",
    "openeuler": "/Users/caixiaomeng/Projects/Python/DataBuilder/data/raw/",
}

def download_images(image_map, target_dir):
    os.makedirs(target_dir, exist_ok=True)
    failed_record = []

    for url, info in tqdm(image_map.items()):
        save_path = info["save_path"]
        dest_path = target_dir + save_path
        directory = os.path.dirname(dest_path)

        # 如果目录不存在，则创建目录
        if not os.path.exists(directory) and directory:  # 确保directory非空
            os.makedirs(directory)

        parsed = urlparse(url)
        if parsed.scheme in ("http", "https"):
            # 网络地址，下载文件
            try:
                resp = requests.get(url, stream=True)
                resp.raise_for_status()
                with open(dest_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
            except Exception as e:
                failed_record.append({url: info, "reason": str(e)})
                print(f"下载失败：{url} <- 错误：{e}")
        else:
            # 可能是本地文件路径，直接拷贝
            # 注意url可能是相对路径，需要根据你的实际情况确定基准路径
            local_path = url
            if not os.path.isabs(local_path):
                # 如果不是绝对路径，这里可以根据需要拼接基准目录
                # 例如基准目录为当前工作目录
                local_path = os.path.abspath(local_path)
            if os.path.exists(local_path):
                try:
                    shutil.copy(local_path, dest_path)
                except Exception as e:
                    failed_record.append({url: info, "reason": str(e)})
            else:
                failed_record.append({url: info, "reason": "Local file not found"})
                print(f"本地文件不存在：{local_path}, 跳过 {url}")
    return failed_record


def build_full_path(path: str, suffix: str) -> str:
    # 去除开头的斜杠，再切分路径
    parts = path.lstrip("/").split("/")
    if not parts:
        raise ValueError("路径格式错误，无法提取第一个层级目录")

    first_level = parts[0]
    prefix = domain_map.get(first_level)
    if prefix is None:
        raise KeyError(f"domain_map 中未找到目录 {first_level}")

    # 判断 prefix 是否是网络URL
    if prefix.startswith("http://") or prefix.startswith("https://"):
        # urljoin可以帮忙处理拼接，避免重复斜杠
        return urljoin(prefix, suffix)
    else:
        # 本地路径拼接，确保目录分隔符正确
        import os

        # 拼接 prefix + path + suffix，path前面去掉第一个层级目录（已包含在prefix里）
        # 其实题目描述是拼接 prefix + path + suffix，保持原样
        # 但这里 path 是相对路径，且 prefix 可能是绝对路径，所以这里直接拼接
        return os.path.join(prefix, path.lstrip("/"), suffix)


def analyze_images_in_jsonl(folder_path: str) -> Tuple[int, int, int, List[Dict]]:
    img_map = {}
    freqs = {}

    # 查找所有 jsonl 文件（递归）
    jsonl_files = glob.glob(f"{folder_path}/**/*.jsonl", recursive=True)

    for file_path in jsonl_files:
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    data = json.loads(line)
                    images = data.get("extra_info", {}).get("images", [])
                    path = data.get("path", "")
                    if not path:
                        continue
                    for img in images:
                        alt = img.get("alt", "").strip()
                        if not alt:
                            continue
                        # 还原url
                        url = img.get("url", "").strip()
                        full_path = build_full_path(path, url)
                        filename = os.path.basename(url)
                        save_path = os.path.join(path, filename)

                        if full_path not in freqs:
                            freqs[full_path] = 0
                        freqs[full_path] += 1
                        img_map[full_path] = {
                            "alt": alt,
                            "save_path": save_path
                        }
                except json.JSONDecodeError:
                    print(f"[警告] JSON解析失败: {file_path} 第 {line_num} 行")
    return img_map, freqs


def transform_image_to_text(folder_path):

    pass


def save_json_to_file(data, filepath):
    # 确保目录存在
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"已保存 JSON 到 {filepath}")


def is_image_file(path):
    return path.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif"))


def calculate_hashes(image_path):
    try:
        img = Image.open(image_path).convert("RGB")
        return {
            "phash": imagehash.phash(img),
            "dhash": imagehash.dhash(img),
            "size": img.size,
        }
    except Exception:
        return None


def is_too_small(size, min_width=32, min_height=32):
    width, height = size
    return width < min_width or height < min_height


def filter_images(folder, output_json_path, phash_threshold=5, dhash_threshold=5):
    seen_hashes = []
    results = []

    files = glob.glob(os.path.join(folder, "**", "*.*"), recursive=True)
    image_files = [f for f in files if is_image_file(f)]

    for path in tqdm(image_files, desc="Filtering images"):
        entry = {"path": path, "keep": True, "reason": ""}

        hashes = calculate_hashes(path)
        if not hashes:
            entry["keep"] = False
            entry["reason"] = "无法打开或识别"
            results.append(entry)
            continue

        size = hashes["size"]
        if is_too_small(size):
            entry["keep"] = False
            entry["reason"] = "尺寸过小"
        else:
            is_duplicate = False
            for seen in seen_hashes:
                phash_dist = hashes["phash"] - seen["phash"]
                dhash_dist = hashes["dhash"] - seen["dhash"]
                if phash_dist <= phash_threshold and dhash_dist <= dhash_threshold:
                    is_duplicate = True
                    entry["keep"] = False
                    entry["reason"] = f"重复图片"
                    entry["similar_to"] = seen["path"]
                    break

            if not is_duplicate:
                seen_hashes.append({**hashes, "path": path})

        results.append(entry)

    # 保存为 JSON
    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n✅ 已保存过滤结果到 {output_json_path}")
    return results


def process_image_descriptions_to_jsonl(
    input_json: str = './stats/filter_image.json',
    output_jsonl: str = './stats/img_desc.jsonl'
):
    with open(input_json, 'r') as f:
        image_entries: List[Dict] = json.load(f)

    # 过滤出 keep 为 True 且路径存在的项
    valid_entries = [
        (item["path"], IMG_PROMPT)
        for item in image_entries
        if isinstance(item, dict)
        and item.get("keep") is True
        and Path(item.get("path", "")).exists()
    ]

    resource_pool = QwenVLPipeline()
    resource_pool.submit_all_and_wait(valid_entries)

    print(f"\n全部描述追加保存至: {output_jsonl}")


if __name__ == "__main__":
    # img_map, img_freqs = analyze_images_in_jsonl(
    #     "/Users/caixiaomeng/Projects/Python/DataBuilder/data/cleaned"
    # )
    # save_json_to_file(img_map, "./stats/img_map.json")
    # save_json_to_file(img_freqs, "./stats/img_freqs.json")
    # failed_record = download_images(img_map, "/Users/caixiaomeng/Projects/Python/DataBuilder/data/images")
    # save_json_to_file(failed_record, "./stats/failed_record.json")
    # all_imgs = filter_images(
    #     "/Users/caixiaomeng/Projects/Python/DataBuilder/data/images",
    #     "./stats/filter_image.json",
    # )
    process_image_descriptions_to_jsonl()
