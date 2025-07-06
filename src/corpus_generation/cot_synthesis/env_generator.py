import json
import os
import re
import itertools
import random
from tqdm import tqdm

from utils.llm import client, extract_json
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.corpus_generation.cot_synthesis.prompt import PARAM_KNOWLEDGE_PROMPT


class PromptGenerator:
    def __init__(self, env_dir="env"):
        self.env_dir = env_dir
        self.applications = [
            "mysql",
            "redis",
            "pgsql",
            "spark",
            "flink",
            "kafka",
            "nginx",
            "ceph",
        ]

        self.set_system = False
        self.app_version_dir = os.path.join(env_dir, "app/version")
        self.app_bottleneck_dir = os.path.join(env_dir, "app/bottleneck")
        self.system_dir = os.path.join(env_dir, "system")
        self.workload_dir = os.path.join(env_dir, "workload")

        for path in [
            self.system_dir,
        ]:
            os.makedirs(path, exist_ok=True)

        for path in [
            self.app_version_dir,
            self.app_bottleneck_dir,
            self.workload_dir,
        ]:
            for app in self.applications:
                os.makedirs(os.path.join(path, app), exist_ok=True)

    def _call_llm(self, prompt: str) -> str:
        return client.call_chatgpt(prompt)

    def generate_app_info(self, app_name: str):
        prompt = f"""
你是一个性能调优专家，请列出 {app_name} 常见的版本列表和性能瓶颈，要求如下：

1. 输出格式为 JSON；
2. 字段说明：
   - application_versions：请返回一个包含 3~5 个版本号的字符串数组，例如 ["1.0", "2.0", "3.0"]；
   - performance_bottlenecks：请尽可能多的返回性能瓶颈描述的字符串数组，每条描述简洁明了，避免重复。

请严格按照JSON格式返回示例：

{{
  "application_versions": ["版本1", "版本2", "版本3"],
  "performance_bottlenecks": [
    "瓶颈描述1",
    "瓶颈描述2",
    "瓶颈描述3"
  ]
}}
        """

        try:
            result = self._call_llm(prompt)
            parsed = extract_json(result)
        except Exception as e:
            print(f"[❌] 应用信息解析失败: {e}, result: {result}")

        # 保存版本列表（单文件）
        versions = parsed.get("application_versions", [])
        versions_path = os.path.join(self.app_version_dir, app_name, f"versions.json")
        with open(versions_path, "w", encoding="utf-8") as f:
            json.dump(versions, f, ensure_ascii=False, indent=2)

        # 保存性能瓶颈，每条一个文件
        bottlenecks = parsed.get("performance_bottlenecks", [])
        for i, bottleneck in enumerate(bottlenecks):
            bottleneck_path = os.path.join(
                self.app_bottleneck_dir, app_name, f"bottleneck_{i:03d}.json"
            )
            with open(bottleneck_path, "w", encoding="utf-8") as f:
                json.dump({"bottleneck": bottleneck}, f, ensure_ascii=False, indent=2)

    def generate_system_info(self):
        # 预定义的典型取值列表
        os_versions = [
            "openEuler 24.03 LTS",
        ]

        cpu_infos = [
            "8 核 @ 2.4GHz",
            "16 核 @ 2.6GHz",
            "32 核 @ 3.0GHz",
            "64 核 @ 2.8GHz",
            "4 核 @ 3.5GHz",
        ]

        memory_infos = [
            "16GB DDR4",
            "32GB DDR4",
            "64GB DDR4",
        ]

        storage_types = [
            "NVMe SSD",
            "SATA SSD",
            "本地 HDD RAID 10",
        ]

        network_infos = [
            "万兆以太网",
            "1Gbps 以太网",
            "千兆以太网",
        ]

        runtime_environments = [
            "物理机",
            "Docker 容器",
            "虚拟机（KVM）",
        ]

        all_combinations = itertools.product(
            os_versions,
            cpu_infos,
            memory_infos,
            storage_types,
            network_infos,
            runtime_environments,
        )
        for combo in all_combinations:
            sys_info = {
                "os_version": combo[0],
                "cpu_info": combo[1],
                "memory_info": combo[2],
                "storage_type": combo[3],
                "network_info": combo[4],
                "runtime_environment": combo[5],
            }

            idx = len(os.listdir(self.system_dir))
            out_path = os.path.join(self.system_dir, f"system_{idx:03d}.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(sys_info, f, ensure_ascii=False, indent=2)

    def sample_bottleneck_combinations(self, bottlenecks):
        """
        根据加权概率从 bottlenecks 中采样组合，组合数量为 1~3 个瓶颈
        """
        weights = {
            1: 0.65,  # 一般一个瓶颈
            2: 0.30,  # 少数有两个
            3: 0.05,  # 极少数情况
        }

        # 保证不超过现有瓶颈个数
        possible_counts = [i for i in weights if i <= len(bottlenecks)]
        probs = [weights[i] for i in possible_counts]

        chosen_len = random.choices(possible_counts, weights=probs, k=1)[0]

        combos = list(itertools.combinations(bottlenecks, chosen_len))
        random.shuffle(combos)

        return combos

    def environment_combinations(self, app_name: str):
        # 读版本列表（单文件）
        versions_path = os.path.join(self.app_version_dir, app_name, "versions.json")
        with open(versions_path, "r", encoding="utf-8") as f:
            app_versions = json.load(f)

        # 读所有瓶颈文件，提取字符串
        bottleneck_files = sorted(
            f for f in os.listdir(os.path.join(self.app_bottleneck_dir, app_name))
        )
        bottlenecks = []
        for fname in bottleneck_files:
            with open(
                os.path.join(self.app_bottleneck_dir, app_name, fname),
                "r",
                encoding="utf-8",
            ) as f:
                data = json.load(f)
                bottlenecks.append(data.get("bottleneck", ""))

        # 读系统配置
        system_files = sorted(os.listdir(self.system_dir))
        system_infos = []
        for fname in system_files:
            with open(os.path.join(self.system_dir, fname), "r", encoding="utf-8") as f:
                system_infos.append(json.load(f))

        bottleneck_combinations = self.sample_bottleneck_combinations(bottlenecks)

        for system_info, app_version, bottleneck_pair in itertools.product(
            system_infos, app_versions, bottleneck_combinations
        ):
            yield system_info, app_version, bottleneck_pair

    def generate_workload(
        self, app_name: str, system_info, app_version, bottlenecks_desc
    ):
        prompt = f"""
你是一个系统建模专家，基于以下环境组合为 `{app_name}` 构造一段典型工作负载特征描述。

【系统配置】：
{json.dumps(system_info, ensure_ascii=False, indent=2)}

【应用版本】：{app_version}
【性能瓶颈】：
- {bottlenecks_desc}

请生成该环境下模拟采集可能的工作负载 profile，系统和应用的关键工作负载指标都需要有（4-10条），用于观察当前应用运行的状态
输出结果请使用json返回，格式如下:
{{
    "system": {{
        "metric1": "value1",
        "metric2": "value2"
    }},
    "{app_name}": {{
        "metric3": "value3",
        "metric4": "value4"
    }}
}}
"""
        try:
            result = self._call_llm(prompt)
            return extract_json(result)
        except Exception as e:
            print(f"[❌] 应用信息解析失败: {e}, result: {result}")
        return None

    def generate_param_knowledge(
        self, app_name: str, bottlenecks_desc
    ):
        prompt = PARAM_KNOWLEDGE_PROMPT.format(app_name, bottlenecks_desc)
        try:
            result = self._call_llm(prompt)
            return result
        except Exception as e:
            print(f"[❌] 应用信息解析失败: {e}, result: {result}")
        return None

    def generate_cur_config(
        self, app_name: str, system_info, app_version, bottlenecks_desc
    ):
        prompt = f"""
你是一个系统建模专家，基于以下环境组合为 `{app_name}` 推理出当前可能的配置信息。

【系统配置】：
{json.dumps(system_info, ensure_ascii=False, indent=2)}

【应用版本】：{app_version}
【性能瓶颈】：
- {bottlenecks_desc}

请根据上述环境信息给出当前应用可能的关键配置（4-10条）,不要输出超过10条配置，输出结果请使用json返回，格式如下:
{{
    "metric1": "value1",
    "metric2": "value2"
}}
"""
        try:
            result = self._call_llm(prompt)
            return extract_json(result)
        except Exception as e:
            print(f"[❌] 应用信息解析失败: {e}, result: {result}")
        return None


    def generate_env_profile(self, app_name: str, max_profiles: int = 5, max_workers: int = 8):
        self.generate_app_info(app_name)
        if not self.set_system:
            self.generate_system_info()
            self.set_system = True

        combo_gen = self.environment_combinations(app_name)

        os.makedirs(os.path.join(self.workload_dir, app_name), exist_ok=True)

        def generate_one(system_info, app_version, bottlenecks, index):
            try:
                bottlenecks_desc = "\n".join(bottlenecks)
                workload_info = self.generate_workload(
                    app_name, system_info, app_version, bottlenecks_desc
                )
                if not workload_info:
                    return None

                cur_config = self.generate_cur_config(
                    app_name, system_info, app_version, bottlenecks_desc
                )
                if not cur_config:
                    return None

                param_knowledge = self.generate_param_knowledge(app_name, bottlenecks_desc)
                if not param_knowledge:
                    return None

                return {
                    "index": index,
                    "data": {
                        "app_name": app_name,
                        "app_version": app_version,
                        "bottlenecks": list(bottlenecks),
                        "system": system_info,
                        "workload": workload_info,
                        "config": cur_config,
                        "param_knowledge": param_knowledge,
                    },
                }
            except Exception as e:
                print(f"[❌] 任务异常: {e}")
                return None

        used_count = 0
        futures = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for i, (system_info, app_version, bottlenecks) in enumerate(combo_gen):
                if used_count >= max_profiles:
                    break
                futures.append(
                    executor.submit(generate_one, system_info, app_version, bottlenecks, i)
                )
                used_count += 1

            pbar = tqdm(total=len(futures), desc="合成workload数据中")
            for future in as_completed(futures):
                result = future.result()
                if result:
                    index = result["index"]
                    data = result["data"]
                    out_path = os.path.join(
                        self.workload_dir, app_name, f"workload_{index:03d}.json"
                    )
                    with open(out_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                pbar.update(1)
            pbar.close()

        print("[完成] 工作负载数据合成任务已结束")


if __name__ == "__main__":

    gen = PromptGenerator("data/synthesis_data")
    gen.generate_env_profile("mysql", 100)
