"""
清理原则：
1.以版本号命名的文件夹，如：v1.0.0、24.03、24.03.RC5
2.包含如下关键词的文件夹、文件：“修订记录、病毒扫描结果、产品版本信息、版本配套文档、更新说明、
遗留问题、已解决问题、修改记录、获取文档的方法、xx版本配套文档、漏洞修补列表、修订记录、
xx公网地址、xx通信矩阵、xx账户清单、安装升级、开源软件声明、问题反馈、
漏洞更新与安全加固、技术支持、视频帮助、安全管理、参考资料、xx下载、
鲲鹏工程师进阶培训及认证服务、鲲鹏工程师培训及认证服务、鲲鹏计算移植专家服务、
鲲鹏全栈调优支持服务、鲲鹏人才培养专家进阶服务、鲲鹏物理资源服务、历史版本、
版本说明书、认证测试、认证申请、社区功能与服务常见问题、示例教程、数学库、
验收指南、用户指南、云测试服务、云手机xx、最新动态、ES3000xx、Media_2.0.0、
RAG一体化解决方案参考实践、RSA_Demo开发指南、TEE套件、TrustZone套件、
案例编写指南、成长地图、特性清单”
"""
import re
from utils.exception import FilterException
from utils.stream.stream import StreamFileFilter, StreamFileReader

# 匹配版本号（支持v开头、RC结尾、小数点、纯数字）
version_pattern = re.compile(r"(v)?\d+(?:\.\d+)*(?:\.(?:RC\d+|SPC\d+))?", re.IGNORECASE)

# 匹配关键词列表（已统一转为小写比较）
keywords = [
    "修订记录",
    "病毒扫描结果",
    "产品版本信息",
    "版本配套文档",
    "更新说明",
    "遗留问题",
    "已解决问题",
    "修改记录",
    "获取文档的方法",
    "版本配套文档",
    "漏洞修补列表",
    "公网地址",
    "通信矩阵",
    "账户清单",
    "安装升级",
    "开源软件声明",
    "问题反馈",
    "漏洞更新与安全加固",
    "技术支持",
    "视频帮助",
    "安全管理",
    "参考资料",
    "下载",
    "鲲鹏工程师进阶培训及认证服务",
    "鲲鹏工程师培训及认证服务",
    "鲲鹏计算移植专家服务",
    "鲲鹏全栈调优支持服务",
    "鲲鹏人才培养专家进阶服务",
    "鲲鹏物理资源服务",
    "历史版本",
    "版本说明书",
    "认证测试",
    "认证申请",
    "社区功能与服务常见问题",
    "示例教程",
    "数学库",
    "验收指南",
    "用户指南",
    "云测试服务",
    "云手机",
    "最新动态",
    "ES3000",
    "Media_2.0.0",
    "RAG一体化解决方案参考实践",
    "RSA_Demo开发指南",
    "TEE套件",
    "TrustZone套件",
    "案例编写指南",
    "成长地图",
    "特性清单",
    "用户信息列表",
    "口令复杂度要求",
    "下载参考",
    "离线获取",
    "在线获取",
    "下载昇腾软件",
    "支持的产品和OS清单",
    "版本说明",
    "公网URL及邮箱",
    "昇腾产品形态说明",
    "补丁说明",
    "安全声明",
    "漏洞补丁列表",
    "如何获取帮助",
    "保修",
    "快速指南（电子版）",
    "组件错误码",
    "界面化开发工具",
    "错误码参考",
    "快速开始",
    "快速体验",
    "使用导读",
    "TensorFlow",
    "用户必读",
    "下载软件包",
    "开发流程",
    "选择安装场景",
    "视图生成推理框架",
    "套件与三方卡",
    "维护参考",
    "安全加固",
    "安装",
    "升级",
    "支持的操作系统",
    "应用案例",
    "准备环境",
    "硬件开发",
    "API_参考",
    "API参考",
    "Atlas_300V_视频解析卡_用户指南（开发者场景）",
    "Index_SDK特征检索",
    "卸载",
    "Vision_SDK视觉分析",
    "学习向导",
]
keywords = [kw.lower() for kw in keywords]


def contains_keyword(name: str) -> bool:
    name_lower = name.lower()
    return any(keyword in name_lower for keyword in keywords)


def is_version_folder(name: str) -> bool:
    return bool(version_pattern.match(name))


def filter_badwords(name: str) -> bool:
    return is_version_folder(name) or contains_keyword(name)


# 文件名过滤器可以看做特殊的reader
class RuleBasedFileFilter(StreamFileFilter, StreamFileReader):
    def __init__(self, input_file_path, output_path):
        super().__init__(input_file_path, output_path)

    def process(self):
        if filter_badwords(str(self.input_file_path)):
            raise FilterException()
