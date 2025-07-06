import os
import re
from tqdm import tqdm
from collections import defaultdict

# 定义要检测的 Markdown 语法及其正则表达式
# blockquote说明相关的，所在行删除
# link和html_tag，把当前所在的句子删掉
SYNTAX_PATTERNS = {
    "blockquote": r"^\s*> .+",
    "link": r"\[.*?\]\(.*?\)",
    "image": r"!\[.*?\]\(.*?\)",
    "html_tag": r"<[^>]+>",
    "toc": r"\[TOC\]",
    "mermaid": r"```mermaid[\s\S]*?```",
}


# 检测语法使用情况并返回是否匹配及示例
def detect_syntax(text):
    result = {}
    for key, pattern in SYNTAX_PATTERNS.items():
        match = re.search(pattern, text, re.MULTILINE)
        result[key] = match.group(0).strip() if match else None
    return result


# 扫描目录并统计语法使用情况
def scan_markdown_files(folder):
    summary_count = defaultdict(int)
    syntax_file_flags = []

    md_files = [
        os.path.join(root, file)
        for root, _, files in os.walk(folder)
        for file in files
        if file.endswith(".md")
    ]

    for path in tqdm(md_files, desc="🔍 正在分析 Markdown 文件"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except UnicodeDecodeError:
            print(f"WARNING: 无法解析文件（编码错误）: {path}")
            continue
        except Exception as e:
            print(f"WARNING: 读取文件失败 {path}：{e}")
            continue

        flags = detect_syntax(text)
        syntax_file_flags.append((path, flags))

        any_matched = False
        for syntax, example in flags.items():
            if example:
                summary_count[syntax] += 1
                any_matched = True

        if not any_matched:
            summary_count["none"] += 1

    return syntax_file_flags, summary_count


# 打印统计结果和示例
def print_summary(syntax_file_flags, summary_count):
    print("\n📊 每个文件语法使用情况：")
    for path, flags in syntax_file_flags:
        used = [k for k, v in flags.items() if v]
        print(f"{path} ➜ {'、'.join(used) if used else '未使用指定语法'}")

    print("\n📈 每种语法被使用的文件数：")
    for syntax in SYNTAX_PATTERNS.keys():
        print(f"{syntax:12} : {summary_count[syntax]}")

    print(f"{'none':12} : {summary_count['none']}（未使用任何指定语法的文件）")

    print("\n🧪 每种语法提取到的第一个示例：")
    printed = set()
    for _, flags in syntax_file_flags:
        for syntax, example in flags.items():
            if example and syntax not in printed:
                print(f"\n【{syntax} 示例】\n{example}")
                printed.add(syntax)


if __name__ == "__main__":
    folder = "/Users/caixiaomeng/Projects/Python/DataBuilder/data/md_format"  # <-- 替换为你的 Markdown 文件夹路径
    syntax_flags, counts = scan_markdown_files(folder)
    print_summary(syntax_flags, counts)
