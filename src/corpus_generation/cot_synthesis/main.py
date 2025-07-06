from src.corpus_generation.cot_synthesis.env_generator import PromptGenerator
from src.corpus_generation.cot_synthesis.cot_synthesis import run_synthesis


def read_jsonl_and_print(file_path):
    import json
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    print(f"\n[Line {line_num}]:")
                    print(data["instruction"])
                    print(data["output"])
                except json.JSONDecodeError as e:
                    print(f"[❌] 第 {line_num} 行解析失败: {e}")
    except Exception as e:
        print(f"[❌] 文件读取失败: {e}")


if __name__ == "__main__":
    prompt_generator = PromptGenerator("data/synthesis_data")
    prompt_generator.generate_env_profile("mysql", 100)
    run_synthesis("mysql")
    # import json
    # read_jsonl_and_print("/Users/caixiaomeng/Projects/Python/DataBuilder/data/synthesis/train_data.jsonl")
