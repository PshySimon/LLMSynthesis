import hashlib
import json
from typing import List, Literal
from pathlib import Path

from simhash import Simhash
from datasketch import MinHash, MinHashLSH
from tqdm import tqdm


class TextDeduplicator:
    def __init__(
        self,
        method: Literal["md5", "simhash", "minhash"] = "md5",
        simhash_threshold=3,
        minhash_threshold=0.8,
    ):
        self.method = method
        self.simhash_threshold = simhash_threshold
        self.minhash_threshold = minhash_threshold
        self.dup_path = Path("./dup.jsonl")
        self.dup_path.unlink(missing_ok=True)

    def save_duplicate(self, text1: str, text2: str):
        with open(self.dup_path, "a", encoding="utf-8") as f:
            f.write(
                json.dumps({"text1": text1, "text2": text2}, ensure_ascii=False) + "\n"
            )

    def deduplicate(self, texts: List[str]) -> List[str]:
        print(f"去重方法: {self.method}")
        if self.method == "md5":
            return self._deduplicate_md5(texts)
        elif self.method == "simhash":
            return self._deduplicate_simhash(texts)
        elif self.method == "minhash":
            return self._deduplicate_minhash(texts)
        else:
            raise ValueError(f"Unknown method: {self.method}")

    def _deduplicate_md5(self, texts: List[str]) -> List[str]:
        seen = set()
        result = []
        for text in tqdm(texts, desc="MD5去重中"):
            h = hashlib.md5(text.strip().encode("utf-8")).hexdigest()
            if h not in seen:
                seen.add(h)
                result.append(text)
            else:
                self.save_duplicate(text, text)
        return result

    def _deduplicate_simhash(self, texts: List[str]) -> List[str]:
        seen = []
        result = []
        added = set()

        def is_duplicate(sh, text):
            for other_sh, other_text in seen:
                if sh.distance(other_sh) <= self.simhash_threshold:
                    key = tuple(sorted([text, other_text]))
                    if key not in added:
                        self.save_duplicate(text, other_text)
                        added.add(key)
                    return True
            return False

        for text in tqdm(texts, desc="SimHash去重中"):
            sh = Simhash(text)
            if not is_duplicate(sh, text):
                seen.append((sh, text))
                result.append(text)
        return result

    def _deduplicate_minhash(self, texts: List[str]) -> List[str]:
        def get_minhash(text: str):
            m = MinHash(num_perm=128)
            for word in text.split():
                m.update(word.encode("utf-8"))
            return m

        lsh = MinHashLSH(threshold=self.minhash_threshold, num_perm=128)
        result = []
        minhashes = {}
        added = set()

        for i, text in enumerate(tqdm(texts, desc="MinHash去重中")):
            mh = get_minhash(text)
            duplicates = lsh.query(mh)
            if duplicates:
                for dup_id in duplicates:
                    dup_text = minhashes[dup_id]
                    key = tuple(sorted([text, dup_text]))
                    if key not in added:
                        self.save_duplicate(text, dup_text)
                        added.add(key)
            else:
                lsh.insert(i, mh)
                minhashes[i] = text
                result.append(text)

        return result


if __name__ == "__main__":
    from tqdm import tqdm
    file_path = "/Users/caixiaomeng/Projects/Python/DataBuilder/data/cleaned_all.jsonl"
    texts = []

    with open(file_path, "r", encoding="utf-8") as f:
        for line in tqdm(f):
            line = line.strip()
            if line:
                data = json.loads(line)
                content = data["content"]
                texts.append(content)
    deduplicator = TextDeduplicator(method="simhash")
    unique_texts = deduplicator.deduplicate(texts)
