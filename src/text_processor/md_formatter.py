import markdown
from bs4 import BeautifulSoup
from utils.stream.stream import StreamFileProcessor


class MarkdownFileToHtml(StreamFileProcessor):
    def process(self, content: str) -> str:
        html = markdown.markdown(content, extensions=["extra", "tables", "toc"])
        content = BeautifulSoup(html, "html.parser")
        return content
