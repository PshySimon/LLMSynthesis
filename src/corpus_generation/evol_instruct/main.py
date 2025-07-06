import json
import random

from utils.llm import client
from depth import (
    createConstraintsPrompt,
    createDeepenPrompt,
    createConcretizingPrompt,
    createReasoningPrompt,
)
from breadth import createBreadthPrompt


def main(seed_prompts_path, output_path):

    fr = open(seed_prompts_path, "r")

    all_objs = json.load(fr)

    evol_objs = []


    for cur_obj in all_objs:

        instruction = cur_obj["instruction"].strip() + "\r\n" + cur_obj["input"].strip()

        evol_prompts = []
        evol_prompts.append(createConstraintsPrompt(instruction))
        evol_prompts.append(createDeepenPrompt(instruction))
        evol_prompts.append(createConcretizingPrompt(instruction))
        evol_prompts.append(createReasoningPrompt(instruction))
        evol_prompts.append(createBreadthPrompt(instruction))

        selected_evol_prompt = random.choice(evol_prompts)

        evol_instruction = client.call_chatgpt(selected_evol_prompt)
        answer = client.call_chatgpt(evol_instruction)

        evol_objs.append({"instruction": evol_instruction, "output": answer})


    with open(output_path, "w") as f:
        json.dump(evol_objs, f, indent=4)


if __name__ == "__main__":
    main(
        seed_prompts_path="/Users/caixiaomeng/Projects/Python/DataBuilder/src/corpus_generation/seed_prompts/alpaca.json",
        output_path="/Users/caixiaomeng/Projects/Python/DataBuilder/data/synthesis_data/test.json",
    )
