import os
import json
import warnings
from pathlib import Path
from typing import List, Type, Union
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod
from utils.common import longest_common_suffix, split_path
from tqdm import tqdm
import multiprocessing
from utils.exception import FilterException
from pprint import pprint
from concurrent.futures import ThreadPoolExecutor, as_completed

class StreamFileProcessor(ABC):
    def __init__(self, input_file_path: str, output_path: str):
        # 输入文件的绝对路径，包括文件名
        self.input_file_path = input_file_path
        # 输出文件的绝对路径，不包括文件名
        self.output_path = output_path
        splitted_path = split_path(self.input_file_path)
        # 源文件的绝对路径
        self.src_path = splitted_path[0]
        # 源文件名
        self.filename = splitted_path[1]
        # 源文件的扩展名
        self.src_extension = splitted_path[2]
        # 待保存的相对路径
        self.relative_path = longest_common_suffix(self.src_path, output_path)

    @abstractmethod
    def process(self, content):
        pass


class StreamFileFilter(StreamFileProcessor):
    def __init__(self, input_file_path, output_path):
        super().__init__(input_file_path, output_path)

    @abstractmethod
    def process(self):
        pass


class NoStreamFileFilter(StreamFileFilter):
    def process(self, content):
        return content


class StreamFileReader(StreamFileProcessor):
    def __init__(self, input_file_path, output_path):
        super().__init__(input_file_path, output_path)

    def process(self):
        pass


class StreamFileWriter(StreamFileProcessor):
    def __init__(self, input_file_path, output_path):
        super().__init__(input_file_path, output_path)

    @abstractmethod
    def process(self, content):
        pass


class HtmlStreamFileReader(StreamFileReader):
    file_extension = "html"

    def __init__(self, input_file_path, output_path):
        super().__init__(input_file_path, output_path)
        self.file_extension = "html"

    def process(self):
        super().process()
        with open(self.input_file_path, "r", encoding="utf-8") as f:
            content = BeautifulSoup(f.read(), "html.parser")
            return content


class TextStreamFileReader(StreamFileReader):
    file_extension = "txt"

    def __init__(self, input_file_path, output_path):
        super().__init__(input_file_path, output_path)
        self.file_extension = "txt"

    def process(self):
        super().process()
        with open(self.input_file_path, "r", encoding="utf-8") as f:
            text = f.read()
            return text


class MarkdownStreamFileReader(TextStreamFileReader):
    file_extension = "md"

    def __init__(self, input_file_path, output_path):
        super().__init__(input_file_path, output_path)

    def process(self):
        return super().process()


class JsonStreamFileWriter(StreamFileWriter):
    def __init__(self, input_file_path, output_path):
        super().__init__(input_file_path, output_path)
        self.target_path = f"{self.output_path}/{self.filename}.json"

    def process(self, content):
        self.target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.target_path, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=2)


class JsonlStreamFileWriter(StreamFileWriter):
    def __init__(self, input_file_path, output_path):
        super().__init__(input_file_path, output_path)
        self.target_path = Path(
            os.path.join(f"{self.output_path}", f"{self.filename}.jsonl")
        )

    def process(self, content):
        self.target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.target_path, "w", encoding="utf-8") as f:
            for item in content:
                json_line = json.dumps(item, ensure_ascii=False)
                f.write(json_line + "\n")


class StreamFilePipeline:
    def __init__(self, readers: StreamFileReader, steps: List["StreamFileProcessor"]):
        self.readers = readers
        self.steps = steps

    def __call__(self, input_file_path, output_path, debug_mode=False):
        try:
            for reader in self.readers:
                if issubclass(reader, StreamFileFilter):
                    filter_ = reader(input_file_path, output_path)
                    filter_.process()
                else:
                    reader_instance = reader(input_file_path, output_path)
                    data = reader_instance.process()
                    if data is None:
                        warnings.warn(
                            f"Reader [{reader.__name__}] returned None for file: {input_file_path}"
                        )
                    if debug_mode:
                        pprint("-" * 100)
                        pprint(f"node name: {reader.__name__}")
                        pprint(data)
                        pprint("-" * 100)
        except FilterException as e:
            return
        except Exception as e:
            raise RuntimeError(
                f"Error in reader [{self.steps[0].__name__}]: {e}"
            ) from e

        # Processor 节点
        for step_class in self.steps[:-1]:
            try:
                processor = step_class(input_file_path, output_path)
                data = processor.process(data)
                if data is None:
                    warnings.warn(
                        f"Processor [{step_class.__name__}] returned None for file: {input_file_path}"
                    )
                if debug_mode:
                    pprint("-" * 100)
                    pprint(f"node name: {step_class.__name__}")
                    pprint(data)
                    pprint("-" * 100)
            except Exception as e:
                raise RuntimeError(
                    f"Error in processor [{step_class.__name__}]: {e}"
                ) from e

        # Writer 处理
        try:
            writer = self.steps[-1](input_file_path, output_path)
            result = writer.process(data)
            if debug_mode:
                pprint("-" * 100)
                pprint(f"node name: {self.steps[-1].__name__}")
                pprint(result)
                pprint("-" * 100)
            return result
        except Exception as e:
            raise RuntimeError(
                f"Error in writer [{self.steps[-1].__class__.__name__}]: {e}"
            ) from e


class StreamFilePipelineBuildFactory:

    def __init__(self):
        self.head_classes: List[Type["StreamFileReader"]] = []
        self.step_classes: List[Type["StreamFileProcessor"]] = []

    def __or__(self, cls: Type["StreamFileProcessor"]):
        if issubclass(cls, StreamFileReader):
            self.head_classes.append(cls)
        else:
            self.step_classes.append(cls)
        return self

    def build(self) -> StreamFilePipeline:
        if not self.step_classes:
            raise ValueError("No processing steps defined.")

        if not self.head_classes or not issubclass(self.head_classes[-1], StreamFileReader):
            raise ValueError("Pipeline must start with a StreamFileReader.")
        if issubclass(self.step_classes[-1], StreamFileReader):
            raise ValueError("Pipeline cannot end with a StreamFileReader.")

        for cls in self.step_classes[:-1]:
            if issubclass(cls, (StreamFileReader, StreamFileWriter)):
                raise ValueError(
                    f"Middle step must be a processor, got: {cls.__name__}"
                )

        return StreamFilePipeline(self.head_classes, self.step_classes)


class BatchStreamFileProcessor:
    def __init__(
        self,
        input_folders: Union[str, List[str]],
        output_folders: Union[str, List[str]],
        process_pipeline: Union["StreamFilePipeline", "StreamFilePipelineBuildFactory"],
        max_workers: int = 4,
    ):
        if isinstance(input_folders, str):
            input_folders = [input_folders]
        if isinstance(output_folders, str):
            output_folders = [output_folders]

        assert len(input_folders) == len(output_folders), "输入和输出文件夹数量必须一致"
        self.input_folders = [Path(folder) for folder in input_folders]
        self.output_folders = [Path(folder) for folder in output_folders]
        self.max_workers = max_workers

        if isinstance(process_pipeline, StreamFilePipelineBuildFactory):
            self.process_pipeline = process_pipeline.build()
        elif isinstance(process_pipeline, StreamFilePipeline):
            self.process_pipeline = process_pipeline
        else:
            raise ValueError(
                "processor pipeline must be StreamFilePipeline or StreamFilePipelineBuildFactory"
            )
        self.file_extension = self.process_pipeline.reader.file_extension

    def process_batch(self, debug_mode: bool = False):
        for i, (input_folder, output_folder) in enumerate(
            zip(self.input_folders, self.output_folders)
        ):
            print(
                f"\n🚀 任务 {i+1}/{len(self.input_folders)}: {input_folder} → {output_folder}"
            )

            all_files = list(input_folder.rglob(f"*.{self.file_extension}"))
            total_files = len(all_files)

            if total_files == 0:
                print(
                    f"⚠️  没有找到 {self.file_extension} 文件，跳过文件夹 {input_folder}"
                )
                continue

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor, tqdm(
                total=total_files, desc=f"处理中（{input_folder.name}）", unit="file"
            ) as pbar:
                futures = {}

                # 提交前 N 个任务
                for j, input_file_path in enumerate(all_files[: self.max_workers]):
                    future = executor.submit(
                        self._process_file,
                        input_file_path,
                        input_folder,
                        output_folder,
                        True if debug_mode and i == 0 and j == 0 else False,
                    )
                    futures[future] = input_file_path

                submitted = self.max_workers

                while futures:
                    done = next(as_completed(futures))
                    if done:
                        pbar.update(1)
                        futures.pop(done, None)

                        if submitted < total_files:
                            next_input = all_files[submitted]
                            next_future = executor.submit(
                                self._process_file,
                                next_input,
                                input_folder,
                                output_folder,
                            )
                            futures[next_future] = next_input
                            submitted += 1

    def _process_file(
        self,
        input_file_path: Path,
        input_folder: Path,
        output_folder: Path,
        debug_mode: bool = False,
    ):
        try:
            relative_path = input_file_path.relative_to(input_folder)
            output_path = output_folder / os.path.dirname(relative_path)
            output_path.mkdir(parents=True, exist_ok=True)
            self.process_pipeline(input_file_path, output_path, debug_mode=debug_mode)
        except Exception as e:
            print(f"❌ 文件处理失败: {input_file_path}，错误: {e}")


class BatchProcessStreamFileProcessor:
    def __init__(
        self,
        input_folders: Union[str, List[str]],
        output_folders: Union[str, List[str]],
        process_pipeline: Union["StreamFilePipeline", "StreamFilePipelineBuildFactory"],
        max_workers: int = 4,
    ):
        if isinstance(input_folders, str):
            input_folders = [input_folders]
        if isinstance(output_folders, str):
            output_folders = [output_folders]

        assert len(input_folders) == len(output_folders), "输入和输出文件夹数量必须一致"
        self.input_folders = [Path(folder) for folder in input_folders]
        self.output_folders = [Path(folder) for folder in output_folders]
        self.max_workers = max_workers

        if isinstance(process_pipeline, StreamFilePipelineBuildFactory):
            self.process_pipeline = process_pipeline.build()
        elif isinstance(process_pipeline, StreamFilePipeline):
            self.process_pipeline = process_pipeline
        else:
            raise ValueError(
                "processor pipeline must be StreamFilePipeline or StreamFilePipelineBuildFactory"
            )
        self.file_extension = self.process_pipeline.readers[-1].file_extension

    def process_batch(self, debug_mode: bool = False):
        for i, (input_folder, output_folder) in enumerate(
            zip(self.input_folders, self.output_folders)
        ):
            print(
                f"\n🚀 任务 {i+1}/{len(self.input_folders)}: {input_folder} → {output_folder}"
            )

            all_files = list(input_folder.rglob(f"*.{self.file_extension}"))
            total_files = len(all_files)

            if total_files == 0:
                print(
                    f"⚠️  没有找到 {self.file_extension} 文件，跳过文件夹 {input_folder}"
                )
                continue

            # 使用多进程池
            with multiprocessing.Pool(processes=self.max_workers) as pool, tqdm(
                total=total_files, desc=f"处理中（{input_folder.name}）", unit="file"
            ) as pbar:
                # 为每个文件提交一个进程任务
                for j, input_file_path in enumerate(all_files):
                    # 仅第一个任务（i==0, j==0）开启 debug
                    is_debug = True if (debug_mode and i == 0 and j == 0) else False
                    pool.apply_async(
                        self._process_file,
                        args=(input_file_path, input_folder, output_folder, is_debug),
                        callback=lambda _: pbar.update(1),
                    )

                # 关闭池并等待所有任务完成
                pool.close()
                pool.join()

    def _process_file(
        self,
        input_file_path: Path,
        input_folder: Path,
        output_folder: Path,
        debug_mode: bool = False,
    ):
        try:
            relative_path = input_file_path.relative_to(input_folder)
            output_path = output_folder / os.path.dirname(relative_path)
            output_path.mkdir(parents=True, exist_ok=True)
            self.process_pipeline(input_file_path, output_path, debug_mode=debug_mode)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"❌ 文件处理失败: {input_file_path}，错误: {e}")
