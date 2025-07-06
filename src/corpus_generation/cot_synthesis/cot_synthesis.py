import os
import json

from tqdm import tqdm
from utils.llm import client
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.corpus_generation.cot_synthesis.prompt import TUNE_TEMPLATE


def build_prompt(json_data) -> str:
    cur_config = json.dumps(json_data["config"], ensure_ascii=False, indent=2)
    bottleneck_report = "\n".join(f"- {b}" for b in json_data.get("bottlenecks", []))

    system = json_data["system"]
    workload = json_data.get("workload", {})
    app_name = json_data["app_name"]

    system_info_parts = [
        f"操作系统版本：{system.get('os_version')}",
        f"CPU 信息：{system.get('cpu_info')}",
        f"内存配置：{system.get('memory_info')}",
        f"存储类型：{system.get('storage_type')}",
        f"网络环境：{system.get('network_info')}",
        f"运行环境：{system.get('runtime_environment')}",
    ]

    if "system" in workload:
        system_info_parts.append("系统运行指标：")
        for k, v in workload["system"].items():
            system_info_parts.append(f"- {k}: {v}")

    if app_name in workload:
        system_info_parts.append(f"{app_name} 运行指标：")
        for k, v in workload[app_name].items():
            system_info_parts.append(f"- {k}: {v}")

    system_info_str = "\n".join(system_info_parts)
    param_knowledge = json_data.get("param_knowledge", "")

    return (
        TUNE_TEMPLATE.replace("{$CUR_CONFIG}", cur_config)
        .replace("{$BOTTLENECK_REPORT}", bottleneck_report)
        .replace("{$SYSTEM_INFO}", system_info_str)
        .replace("{$PARAM_KNOWLEDGE}", param_knowledge)
    )


def run_synthesis(
    app_name: str,
    out_file: str = "data/synthesis/train_data.jsonl",
    max_workers: int = 8,
):
    workload_dir = f"data/synthesis_data/workload/{app_name}"
    if not os.path.exists(workload_dir):
        print(f"[❌] 目录不存在: {workload_dir}")
        return

    files = sorted(f for f in os.listdir(workload_dir) if f.endswith(".json"))
    if not files:
        print(f"[⚠️] 无数据文件: {workload_dir}")
        return

    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    print(f"[🚀] 开始并发处理 {len(files)} 条 workload 数据")

    def process_file(fname: str):
        try:
            file_path = os.path.join(workload_dir, fname)
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            prompt = build_prompt(data)
            answer = client.call_chatgpt(prompt)

            if not answer:
                raise ValueError("模型返回为空")

            item =  {
                "instruction": prompt.strip(),
                "input": "",
                "output": answer.strip(),
            }
            with open(out_file, "a", encoding="utf-8") as out_fp:
                out_fp.write(json.dumps(item, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[❌] 处理失败 ({fname}): {e}")
            return None

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_file, fname): fname for fname in files}

        for future in tqdm(
            as_completed(futures), total=len(futures), desc="并发合成数据"
        ):
            future.result()


# 示例调用
if __name__ == "__main__":
    run_synthesis("mysql")  # 修改为你要处理的 app_name
