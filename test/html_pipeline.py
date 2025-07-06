from utils.stream.stream import (
    BatchStreamFileProcessor,
    StreamFilePipelineBuildFactory,
    HtmlStreamFileReader,
    NoStreamFileFilter,
    JsonlStreamFileWriter,
)
from src.text_processor.html_formatter import HtmlStructureExtractor

md_pipeline = (
    StreamFilePipelineBuildFactory()
    | HtmlStreamFileReader
    | NoStreamFileFilter
    | HtmlStructureExtractor
    | JsonlStreamFileWriter
)

md_batch_processor = BatchStreamFileProcessor(
    input_folders=["/Users/caixiaomeng/Projects/Python/DataBuilder/data/raw/kunpeng"],
    output_folders=[
        "/Users/caixiaomeng/Projects/Python/DataBuilder/data/cleaned/kunpeng"
    ],
    process_pipeline=md_pipeline,
    max_workers=8,
)

import cProfile

cProfile.run("md_batch_processor.process_batch()", sort="cumulative")
