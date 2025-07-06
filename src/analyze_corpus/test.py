import os
import re
import jieba
import unicodedata

def normalize_markdown(content):
    # 替换 URL、锚点、图片 为统一的 TOKEN
    content = re.sub(r"https?://[^\s)]+", " TOKEN ", content)
    content = re.sub(r"\[.*?\]\(#[^\)]+\)", " TOKEN ", content)
    content = re.sub(r"!\[.*?\]\([^\)]+\)", " TOKEN ", content)
    return content


def is_chinese_token(token):
    # 含中文字符：算中文
    if any("\u4e00" <= c <= "\u9fff" for c in token):
        return True
    # 全部是标点、符号、空格等：也算中文
    if all(
        unicodedata.category(c).startswith(("P", "Z", "S")) or c.isspace()
        for c in token
    ):
        return True
    # 否则算非中文
    return False


def analyze_file(file_path, output_path="./stats/output.txt"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    norm_content = normalize_markdown(content)
    tokens = list(jieba.cut(norm_content))

    result_lines = []
    non_chinese_count = 0

    for idx, token in enumerate(tokens, 1):
        is_chinese = any(is_chinese_token(c) for c in token)
        flag = "中文" if is_chinese else "非中文"
        if not is_chinese:
            non_chinese_count += 1
        result_lines.append(f"{idx:04d}\t{token}\t{flag}")

    total = len(tokens)
    ratio = non_chinese_count / total if total > 0 else 0

    result_lines.append("\n======== 统计信息 ========")
    result_lines.append(f"总词数: {total}")
    result_lines.append(f"非中文词数: {non_chinese_count}")
    result_lines.append(f"非中文比例: {ratio:.2%}")

    with open(output_path, "w", encoding="utf-8") as out:
        out.write("\n".join(result_lines))

    print(f"分析完成 ✅，结果保存至：{output_path}")


# 示例调用（你可以注释这行，在别处调用函数）
analyze_file(
    "/Users/caixiaomeng/Projects/Python/DataBuilder/data/md_format/kunpeng/鲲鹏术语表.md"
)
