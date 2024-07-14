from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl

DATA_PATH = Path.cwd() / "data"
JSON_PATH = DATA_PATH / "rss.json"

class ELFConfig(BaseSettings):
    class Config:
        extra = "allow"

    # 代理地址
    rss_proxy: Optional[str] = None
    rsshub: AnyHttpUrl = "https://rsshub.speednet.icu"
    # 备用 rsshub 地址
    rsshub_backup: List[AnyHttpUrl] = ["https://rsshub.app"]
    db_cache_expire: int = 30
    limit: int = 200
    max_length: int = 1024  # 正文长度限制，防止消息太长刷屏，以及消息过长发送失败的情况
    enable_boot_message: bool = True  # 是否启用启动时的提示消息推送
    debug: bool = False  # 是否开启 debug 模式，开启后会打印更多的日志信息，同时检查更新时不会使用缓存,便于调试

    zip_size: int = 2 * 1024
    gif_zip_size: int = 6 * 1024
    img_format: Optional[str] = None
    img_down_path: Optional[str] = None

    blockquote: bool = True
    black_word: Optional[List[str]] = None

    # 百度翻译的 appid 和 key
    baidu_id: Optional[str] = None
    baidu_key: Optional[str] = None
    deepl_translator_api_key: Optional[str] = None
    # 配合 deepl_translator 使用的语言检测接口，前往 https://detectlanguage.com/documentation 注册获取 api_key
    single_detection_api_key: Optional[str] = None


# 实例化配置
config = ELFConfig()
