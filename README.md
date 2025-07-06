目录结构介绍
.
├── README.md                           项目说明文件
├── config.json                         环境配置文件
├── src
│   ├── analyze-corpus                  数据集分析模块
│   ├── corpus-cleaner                  语料清洗模块
│   ├── corpus-deduplication            语料去重模块
│   ├── corpus-generation               语料增强、蒸馏、合成模块
│   ├── data-crawler                    数据爬虫模块
│   │   └── kunpeng_crawler.py              鲲鹏官网文档爬虫模块
│   ├── quality-assesment               数据质量评估模块
│   └── text-converter                  数据转换模块，将其他格式的数据转换成txt格式
│       ├── md_processor.py
│       └── pdf_processor.py
├── test.py
└── utils
    └── llm.py# LLMSynthesis
