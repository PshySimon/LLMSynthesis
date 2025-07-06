import json
from tqdm import tqdm
from utils.llm import get_chat_response
from utils.thread_pool import ThreadPool
from utils.prompts import DATA_SYNTHESIS_PROMPT

file_path = "/Users/caixiaomeng/Projects/Python/DataBuilder/data/cleaned_all.jsonl"
queries = []

with open(file_path, "r", encoding="utf-8") as f:
    for line in tqdm(f):
        line = line.strip()
        try:
            if line:
                data = json.loads(line)
                uuid = data["uuid"]
                title = "-".join(data["titles"])
                path = "/".join([data["path"], data["filename"]])
                content = data["content"]
                if len(content) < 10:
                    continue
                queries.append(
                    (uuid,
                    DATA_SYNTHESIS_PROMPT.substitute(
                        title=title, path=path, content=content
                    ))
                )
        except Exception as e:
            import traceback
            traceback.print_exc()
            break
        
def data_synthesis(uuid, query):
    return {
        "uuid": uuid,
        "response": get_chat_response(query)
    }

all_tasks = [(data_synthesis, (uuid, query,), {}) for uuid, query in queries]

thread_pool = ThreadPool(max_workers=16)
thread_pool.submit_all_and_wait(all_tasks)
