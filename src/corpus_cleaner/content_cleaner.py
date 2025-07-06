import os
import re
from unicodedata import category
from utils.stream.stream import StreamFileProcessor


def replace_markdown_images(text):
    def replacer(match):
        prefix = match.group(1)
        alt = match.group(2).strip()
        url = match.group(3).strip()

        # 判断是否有“放大”前缀
        prefix = prefix or ""
        prefix = prefix.strip()

        # 清理空图
        if not alt and not url:
            return ""

        # 生成描述
        if alt:
            desc = alt
        elif url:
            desc = os.path.basename(url)
        else:
            return ""

        # 是否去除“放大”
        if prefix == "放大":
            return f"[[IMAGE:{desc}]]"
        else:
            return f"{prefix}[[IMAGE:{desc}]]" if prefix else f"[[IMAGE:{desc}]]"

    # 支持前缀（如“放大”）
    pattern = r"(?:(放大)?\s*)?!\[(.*?)\]\((.*?)\)"
    return re.sub(pattern, replacer, text)


class ParagraphContentCleaner(StreamFileProcessor):
    # 清洗函数
    def clean_content(self, content):
        content = re.sub(r"<!-- TOC -->.*?<!-- /TOC -->", "", content, flags=re.DOTALL)
        content = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", content)

        # 规则 1 & 2: 去掉单独一行的“展开”或“**父主题：** xxx”
        lines = content.splitlines()
        cleaned_lines = []
        for line in lines:
            if line.strip() == "展开":
                continue
            if re.match(r"^\*\*父主题：\*\* .*?$", line.strip()):
                continue
            if re.match(r"^[\W_]{2,}$", line.strip()):  # 规则3: 全是相同的标点符号（粗略）
                continue
            cleaned_lines.append(line)

        content = "\n".join(cleaned_lines)

        # 规则 4: 移除所有控制字符，保留 \n
        content = "".join(ch for ch in content if ch == "\n" or category(ch) != "Cc")

        # 规则 5: 去除中文全角空格和不可见空格
        content = content.replace("\u3000", "").replace("\xa0", "")

        # 规则 6: 清除 ASCII 控制字符
        content = re.sub(r"[\x00-\x09\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", content)

        # 规则 7: 删除多余空行
        content = re.sub(r"\n{2,}", "\n", content)
        
        # 规则 8: 清理图片
        content = replace_markdown_images(content)

        return content.strip()

    def process(self, paragraph_list: list[dict]) -> str:
        for paragraph in paragraph_list:
            paragraph["content"] = self.clean_content(paragraph["content"])
        return paragraph_list


if __name__ == "__main__":
    paragraphContentCleaner = ParagraphContentCleaner("a", "b")
    output = paragraphContentCleaner.process([{"content": "点击展开>>这是一段测试文本\n\ntest\n\n\n父主题：Test文本"}])
    print(output)
