from utils.stream.stream import (
    BatchStreamFileProcessor,
    StreamFilePipelineBuildFactory,
    MarkdownStreamFileReader,
    HtmlStreamFileReader,
    JsonlStreamFileWriter,
    BatchProcessStreamFileProcessor,
)
import multiprocessing
from src.corpus_cleaner.content_cleaner import ParagraphContentCleaner
from src.corpus_filter.file_filter import RuleBasedFileFilter
from src.corpus_filter.content_filter import RuleBasedContentFilter
from src.text_processor.md_formatter import MarkdownFileToHtml
from src.text_processor.html_formatter import HtmlStructureExtractor


md_pipeline = (
    StreamFilePipelineBuildFactory()
    | RuleBasedFileFilter
    | MarkdownStreamFileReader
    | MarkdownFileToHtml
    | HtmlStructureExtractor
    | RuleBasedContentFilter
    | ParagraphContentCleaner
    | JsonlStreamFileWriter
)

html_pipeline = (
    StreamFilePipelineBuildFactory()
    | RuleBasedFileFilter
    | HtmlStreamFileReader
    | HtmlStructureExtractor
    | RuleBasedContentFilter
    | ParagraphContentCleaner
    | JsonlStreamFileWriter
)

html_batch_processor = BatchProcessStreamFileProcessor(
    input_folders=[
        "/Users/caixiaomeng/Projects/Python/DataBuilder/data/raw/ascend",
        "/Users/caixiaomeng/Projects/Python/DataBuilder/data/raw/kunpeng",
    ],
    output_folders=[
        "/Users/caixiaomeng/Projects/Python/DataBuilder/data/cleaned/ascend",
        "/Users/caixiaomeng/Projects/Python/DataBuilder/data/cleaned/kunpeng",
    ],
    process_pipeline=html_pipeline,
    max_workers=8,
)

md_batch_processor = BatchProcessStreamFileProcessor(
    input_folders=["/Users/caixiaomeng/Projects/Python/DataBuilder/data/raw/openeuler"],
    output_folders=[
        "/Users/caixiaomeng/Projects/Python/DataBuilder/data/cleaned/openeuler"
    ],
    process_pipeline=md_pipeline,
    max_workers=8,
)

if __name__ == "__main__":
    md_batch_processor.process_batch()
    html_batch_processor.process_batch()
