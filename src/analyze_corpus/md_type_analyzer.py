import os
import re
import json
import jieba
import unicodedata


def normalize_markdown(content):
    content = re.sub(r"https?://[^\s)]+", " TOKEN ", content)
    content = re.sub(r"\[.*?\]\(#[^\)]+\)", " TOKEN ", content)
    content = re.sub(r"!\[.*?\]\([^\)]+\)", " TOKEN ", content)
    return content


def is_chinese_token(token):
    if any("\u4e00" <= c <= "\u9fff" for c in token):
        return True
    if all(
        unicodedata.category(c).startswith(("P", "Z", "S")) or c.isspace()
        for c in token
    ):
        return True
    return False


def extract_contexts(pattern, text, window=30):
    matches = []
    for match in re.finditer(pattern, text):
        start, end = match.span()
        context = text[max(0, start - window) : min(len(text), end + window)]
        matches.append(context.strip())
    return matches


def count_elements_and_flags(file_path):
    reasons = []
    context_info = {}

    with open(file_path, "r", encoding="utf-8") as f:
        raw_content = f.read()

    # URLs
    url_pattern = r"https?://[^\s)]+"
    urls = re.findall(url_pattern, raw_content)
    if len(urls) > 3:
        reasons.append("url > 3")
        context_info["urls"] = extract_contexts(url_pattern, raw_content)

    # Anchors
    anchor_pattern = r"\[.*?\]\(#[^\)]+\)"
    anchors = re.findall(anchor_pattern, raw_content)
    if len(anchors) > 3:
        reasons.append("anchor > 3")
        context_info["anchors"] = extract_contexts(anchor_pattern, raw_content)

    # Images
    image_pattern = r"!\[.*?\]\([^\)]+\)"
    images = re.findall(image_pattern, raw_content)
    if len(images) > 3:
        reasons.append("image > 3")
    if images:
        context_info["images"] = extract_contexts(image_pattern, raw_content)

        # 提取 "图" + 编号 及相关表达的上下文
        figure_patterns = [
            r"图\s*\d+(\.\d+)?",  # 图1，图3.1
            r"如图\s*\d*\s*所示",  # 如图所示，如图3所示
            r"如[上下]图",  # 如上图，如下图
            r"[上下]图所示",  # 上图所示，下图所示
            r"参考图\s*\d*",  # 参考图3，参考图
            r"参考下图",  # 参考下图
            r"请看图\s*\d*",  # 请看图1
            r"见[上下]图",  # 见上图，见下图
            r"图示",  # 图示
            r"as\s+shown\s+in\s+Fig\.?\s*\d+",  # as shown in Fig. 2
            r"see\s+Fig\.?\s*\d+",  # see Fig. 3
            r"refer\s+to\s+the\s+figure\s+below",  # refer to the figure below
        ]

        figure_mentions = []
        for pattern in figure_patterns:
            figure_mentions += extract_contexts(pattern, raw_content)

        if figure_mentions:
            context_info["figure_mentions"] = figure_mentions

    # Code block ratio
    code_blocks = re.findall(r"```.*?\n(.*?)```", raw_content, re.DOTALL)
    code_text = "\n".join(code_blocks)
    if len(raw_content) > 0 and (len(code_text) / len(raw_content)) > 0.4:
        reasons.append("code block > 40%")

    # Non-Chinese content ratio
    norm_content = normalize_markdown(raw_content)
    tokens = list(jieba.cut(norm_content))
    if tokens:
        non_chinese_count = sum(
            1 for token in tokens if not any(is_chinese_token(c) for c in token)
        )
        if (non_chinese_count / len(tokens)) > 0.3:
            reasons.append("non-Chinese > 30%")

    return reasons, context_info


def scan_markdown_files(root_dir, output_json):
    results = {}

    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith(".md"):
                file_path = os.path.join(dirpath, filename)
                reasons, context_info = count_elements_and_flags(file_path)
                if reasons:
                    results[file_path] = {"reasons": reasons, "context": context_info}

    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    scan_markdown_files(
        "/Users/caixiaomeng/Projects/Python/DataBuilder/data/md_format/kunpeng",
        "./stats/kunpeng_md_stats.json",
    )
    scan_markdown_files(
        "/Users/caixiaomeng/Projects/Python/DataBuilder/data/md_format/ascend",
        "./stats/ascend_md_stats.json",
    )

