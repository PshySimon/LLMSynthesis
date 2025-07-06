import requests
import time
import re
import json5
import json
import asyncio
import aiohttp
from typing import Optional, List, Generator
from concurrent.futures import ThreadPoolExecutor, as_completed


class APIEndpoint:
    def __init__(self, url: str, model: str, keys: List[str]):
        self.url = url
        self.model = model
        self.keys = keys
        self.invalid_keys = set()
        self.index = 0  # round-robin

    def get_next_key(self) -> Optional[str]:
        valid_keys = [k for k in self.keys if k not in self.invalid_keys]
        if not valid_keys:
            return None
        key = valid_keys[self.index % len(valid_keys)]
        self.index += 1
        return key

    def mark_key_invalid(self, key: str):
        self.invalid_keys.add(key)

    def has_valid_key(self) -> bool:
        return len([k for k in self.keys if k not in self.invalid_keys]) > 0


class APIManager:
    def __init__(self):
        self.endpoints = self.init_endpoints()

    def init_endpoints(self):
        with open("config/env.json", "r", encoding="utf-8") as f:
            config_data = json.load(f)

        return [
            APIEndpoint(url=item["url"], model=item["model"], keys=item["keys"])
            for item in config_data
        ]

    def get_available_endpoints(self):
        for endpoint in self.endpoints:
            if endpoint.has_valid_key():
                yield endpoint


class LLMClient:
    def __init__(self):
        self.api_manager = APIManager()

    def get_completion(self, prompt: str) -> Optional[str]:
        for endpoint in self.api_manager.get_available_endpoints():
            key = endpoint.get_next_key()
            if key is None:
                continue

            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": endpoint.model,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt},
                ],
            }

            try:
                response = requests.post(
                    endpoint.url, headers=headers, json=payload, timeout=120
                )
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
            except (requests.exceptions.RequestException, KeyError, IndexError) as e:
                print(f"[ERROR] Failed with {endpoint.url} and key {key}: {e}")
                endpoint.mark_key_invalid(key)
                continue

        print("[FATAL] All API endpoints and keys failed.")
        return None

    def call_chatgpt(self, prompt: str, retries: int = 3) -> Optional[str]:
        for _ in range(retries):
            response = self.get_completion(prompt)
            if response:
                return response
            print("[Retrying] waiting before next try...")
            time.sleep(1)
        return None

    def stream_prompts(
        self,
        prompt_iter: Generator[str, None, None],
    ):
        """
        并发执行 prompts，每次只保留最大 max_workers 个活跃线程。
        每个结果立即写入 JSONL 文件。
        """
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            prompt_counter = 0

            try:
                while True:
                    # 填满任务池
                    while len(futures) < self.max_workers:
                        try:
                            prompt = next(prompt_iter)
                            future = executor.submit(self.call_chatgpt, prompt)
                            futures[future] = prompt
                            prompt_counter += 1
                        except StopIteration:
                            break

                    # 等待任何一个完成
                    if not futures:
                        break

                    done, _ = next(as_completed(futures), None), None
                    if done:
                        prompt = futures.pop(done)
                        try:
                            answer = done.result()
                            if answer:
                                self.fp.write(
                                    json.dumps(
                                        {
                                            "instruction": prompt.strip(),
                                            "input": "",
                                            "output": answer.strip(),
                                        },
                                        ensure_ascii=False,
                                    )
                                    + "\n"
                                )
                                self.fp.flush()
                                print(f"[✓] 写入成功 ({prompt_counter})")
                            else:
                                print(f"[⚠️] 无返回内容")
                        except Exception as e:
                            print(f"[❌] 执行失败: {e}")
            finally:
                self.fp.close()

    async def call_llm(self, prompt: str, retries: int = 3) -> Optional[str]:
        for attempt in range(retries):
            async with self.semaphore:
                for endpoint in self.api_manager.get_available_endpoints():
                    key = endpoint.get_next_key()
                    if not key:
                        continue

                    headers = {
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                    }

                    payload = {
                        "model": endpoint.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a helpful assistant.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                    }

                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.post(
                                endpoint.url, headers=headers, json=payload, timeout=120
                            ) as resp:
                                if resp.status != 200:
                                    raise Exception(await resp.text())

                                data = await resp.json()
                                return data["choices"][0]["message"]["content"]
                    except Exception as e:
                        print(f"[ERROR] {endpoint.url} ({key}): {e}")
                        endpoint.mark_key_invalid(key)
                        await asyncio.sleep(1)  # 短暂等待
                        continue
        return None


client = LLMClient()


def extract_json(text: str):
    # 尝试匹配最外层的 JSON 对象或数组（{}或[]）
    # 非贪婪匹配，匹配第一个完整的json块
    match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if not match:
        raise ValueError("未找到有效的 JSON 内容")
    json_str = match.group(1)
    # 可选：去除开头结尾多余空白
    json_str = json_str.strip()
    return json5.loads(json_str)


if __name__ == "__main__":
    response = client.call_chatgpt("hello?")
    print(response)
