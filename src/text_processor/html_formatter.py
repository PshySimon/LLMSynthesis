import re
import os
import uuid
from typing import List, Dict
from bs4 import BeautifulSoup, Tag, NavigableString
from markdownify import markdownify as html_to_markdown
from utils.stream.stream import StreamFileProcessor


class HtmlStructureExtractor(StreamFileProcessor):
    def process(self, soup: BeautifulSoup):
        body = soup.body or soup
        min_heading_level = self._find_min_heading_level([body])
        result = []
        self._dfs(body, [], result, min_heading_level)
        return result

    def _dfs(self, node: Tag, heading_stack: List[str], result: List[Dict], base_level: int):
        children = list(node.children)
        i = 0
        while i < len(children):
            child = children[i]
            if not isinstance(child, Tag):
                i += 1
                continue

            level = self._get_heading_level(child)

            if level is not None and level >= base_level:
                title = child.get_text(strip=True)
                new_stack = heading_stack[: level - base_level] + [title]

                # 收集内容直到遇到更高或同级别的标题
                content_buffer = []
                i += 1
                while i < len(children):
                    sibling = children[i]
                    sibling_level = (
                        self._get_heading_level(sibling)
                        if isinstance(sibling, Tag)
                        else None
                    )
                    if sibling_level is not None and sibling_level <= level:
                        break  # 同级或更高，当前块结束
                    content_buffer.append(str(sibling))
                    i += 1

                html_content = "".join(content_buffer).strip()
                if html_content:
                    md_content = html_to_markdown(html_content)
                    result.append(
                        self._create_json_line(new_stack.copy(), md_content)
                    )

                # 递归当前标题块的内容（即 content_buffer）
                soup_fragment = BeautifulSoup(html_content, "html.parser")
                self._dfs(soup_fragment, new_stack.copy(), result, base_level)
            else:
                # 不是标题，继续递归处理其子节点
                self._dfs(child, heading_stack.copy(), result, base_level)
                i += 1


    def _is_heading(self, tag: Tag):
        return tag.name and tag.name.startswith("h") and tag.name[1:].isdigit()

    def _get_heading_level(self, tag: Tag):
        if self._is_heading(tag):
            return int(tag.name[1:])
        return None


    def _find_min_heading_level(self, nodes: List[Tag]) -> int:
        def collect_levels(nodes: List[Tag]) -> List[int]:
            levels = []
            for node in nodes:
                if isinstance(node, Tag):
                    if self._is_heading(node):
                        levels.append(self._get_heading_level(node))
                    levels.extend(collect_levels(list(node.children)))
            return levels

        all_levels = collect_levels(nodes)
        return min(all_levels) if all_levels else 1

    def _create_json_line(self, titles: List[str], content: str):
        return {
            "uuid": str(uuid.uuid4()),
            "titles": titles,
            "content": content,
            "path": self.relative_path,
            "filename": self.filename,
            "extra_info": self.extract_elements_from_markdown(content),
        }

    def extract_elements_from_markdown(
        self, markdown_text: str
    ) -> Dict[str, List[Dict]]:
        links = []
        images = []
        anchors = []

        image_pattern = re.compile(r"!\[([^\]]*?)\]\((.*?)(?<!\\)\)")
        for match in image_pattern.finditer(markdown_text):
            alt_text, url = match.groups()
            desc = alt_text if alt_text.strip() else os.path.basename(url)
            images.append({"alt": desc, "url": url.strip()})

        link_pattern = re.compile(r"(?<!!)\[([^\]]+?)\]\((.*?)(?<!\\)\)")
        for match in link_pattern.finditer(markdown_text):
            text, url = match.groups()
            links.append({"text": text.strip(), "url": url.strip()})
            if url.startswith("#"):
                anchors.append(
                    {"anchor": url.lstrip("#").strip(), "text": text.strip()}
                )

        heading_pattern = re.compile(
            r"^\s{0,3}#{1,6}\s+(.*?)(\s+#+\s*)?$", re.MULTILINE
        )
        for match in heading_pattern.finditer(markdown_text):
            heading_text = match.group(1).strip()
            anchor = self.generate_anchor_id(heading_text)
            if anchor:
                anchors.append({"anchor": anchor, "text": heading_text})

        seen = set()
        unique_anchors = []
        for item in anchors:
            if item["anchor"] not in seen:
                unique_anchors.append(item)
                seen.add(item["anchor"])

        return {
            "links": links,
            "images": images,
            "anchors": unique_anchors,
        }

    @staticmethod
    def generate_anchor_id(heading: str) -> str:
        anchor = re.sub(r"[^\w\- ]", "", heading).strip().lower()
        anchor = re.sub(r"\s+", "-", anchor)
        return anchor
