import re
from utils.stream.stream import StreamFileFilter

JUMP_PATTERNS = [
    r"(更多信息|了解详情|相关内容|相关阅读|延伸阅读)[^\n]{0,50}",
    r"(点击(这里|此处)|访问链接|跳转至|前往)[^\n]{0,50}",
]


def is_jump_paragraph(paragraph: str) -> bool:
    for pattern in JUMP_PATTERNS:
        match = re.search(pattern, paragraph, re.IGNORECASE)
        if match:
            return True
    return False


class RuleBasedContentFilter(StreamFileFilter):
    def process(self, paragraph_list: list[dict]) -> str:
        filtered_paragraph_list = []
        for paragraph in paragraph_list:
            content = paragraph["content"]
            if is_jump_paragraph(content):
                continue
            filtered_paragraph_list.append(paragraph)
        return filtered_paragraph_list
