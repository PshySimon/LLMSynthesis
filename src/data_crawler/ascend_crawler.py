import re
import os
import asyncio
from playwright.async_api import async_playwright

KUNPENG_DOC_URL = "https://www.hiascend.com/zh/document?tab=document"
SAVE_PATH = "/Users/caixiaomeng/Projects/Python/DataBuilder/data/raw/ascend"


async def sanitize_filename(path):
    # 移除文件名中的非法字符
    path = re.sub(r'[<>:"/\\|?*]', "_", path)
    # 去掉两端的空白字符
    path = path.strip()
    # 替换空格为下划线
    path = path.replace(" ", "_")
    # 限制文件名长度（Windows 文件名最大长度为255）
    path = path[:255]
    return path


async def get_breadcrumbs(page):
    try:
        breadcrumbs = await page.query_selector_all("span.bread-item-inner")
        breadcrumb_list = []
        for breadcrumb in breadcrumbs:
            text = await breadcrumb.inner_text()
            # 使用await调用sanitize_filename
            breadcrumb_list.append(await sanitize_filename(text.strip()))
        return breadcrumb_list[:-1]
    except Exception as e:
        print(f"[错误] 获取来源失败: {e}")
        return []


async def save_article(page):
    breadcrumb_list = await get_breadcrumbs(page)

    if not breadcrumb_list:
        print("[跳过]提取文章来源失败")
        return False

    dir_name = os.path.join(*breadcrumb_list)
    full_path = os.path.join(SAVE_PATH, dir_name)

    if not os.path.exists(full_path):
        os.makedirs(full_path)
        print(f"目录 '{full_path}' 已创建。")

    try:
        await page.wait_for_timeout(1000)  # 稳定 DOM

        title_el = await page.query_selector("section.topic-section h1.topic-title")
        if not title_el:
            print("[跳过] 非文章页面（无标题）")
            return False

        title_text = await title_el.inner_text()
        safe_title = title_text.strip().replace("/", "-").replace("\\", "-")

        content_el = await page.query_selector(
            "section.article-content .the-article.document-article"
        )
        if content_el:
            content = await content_el.inner_html()  # 加上 await
            filename = os.path.join(full_path, f"{safe_title}.html")
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"[已保存] {filename}")
        else:
            print(f"[跳过] 无正文内容: {safe_title}")
        return True
    except Exception as e:
        print(f"[错误] 保存文章失败: {e}")
        return False


async def process_list_item(context, page, index):
    await page.wait_for_selector(".document-section-pc .list-wrapper .list-item")
    list_items = await page.query_selector_all(
        ".document-section-pc .list-wrapper .list-item"
    )

    if index >= len(list_items):
        return

    async with context.expect_page() as new_page_info:
        await list_items[index].click()

    new_page = await new_page_info.value
    await new_page.wait_for_load_state("networkidle")

    is_article = await save_article(new_page)
    if not is_article:
        await new_page.close()
        return

    while True:
        next_btn = await new_page.query_selector("div.next-article.is-exist")
        if next_btn:
            await next_btn.click()
            await new_page.wait_for_timeout(1000)
            success = await save_article(new_page)
            if not success:
                break
        else:
            break

    await new_page.close()


"""
爬取鲲鹏官网的全部文档，以html形式保存
"""


async def kunpeng_crawler():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # 设为True可无头运行
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(KUNPENG_DOC_URL, wait_until="networkidle")

        await page.wait_for_selector(".o-pagination-pages div")
        pages = await page.query_selector_all(".o-pagination-pages div")
        last_span = await pages[-1].query_selector("span")
        max_page = int(await last_span.inner_text())
        print(f"📄 总页数: {max_page}")

        for current_page in range(1, max_page + 1):
            print(f"\n===== 第 {current_page} 页 =====")
            await page.wait_for_selector(
                ".document-section-pc .list-wrapper .list-item"
            )
            list_items = await page.query_selector_all(
                ".document-section-pc .list-wrapper .list-item"
            )
            total_items = len(list_items)

            for idx in range(total_items):
                print(f"\n-- 处理第 {idx + 1}/{total_items} 个条目 --")
                try:
                    await process_list_item(context, page, idx)
                except Exception as e:
                    print(f"[错误]处理item失败，错误原因是：{e}")

            if current_page < max_page:
                next_page_btn = await page.query_selector("div.o-pagination-next")
                if next_page_btn:
                    await next_page_btn.click()
                    await page.wait_for_timeout(2000)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(kunpeng_crawler())
