from typing import Any, Dict, Optional, Tuple

import aiohttp
import feedparser
from tinydb import TinyDB
from yarl import URL

import my_trigger as tr
from config import DATA_PATH, config
from parsing import get_proxy
from parsing.cache_manage import cache_filter
from parsing.check_update import dict_hash
from parsing.parsing_rss import ParsingRss
from rss_class import Rss
from utils import get_http_caching_headers
from logger_config import LoggerConfig

# 创建LoggerConfig实例并获取logger
logger_config = LoggerConfig(log_file='rss.log')
logger = logger_config.get_logger()

HEADERS = {
    "Accept": "application/xhtml+xml,application/xml,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "max-age=0",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/111.0.0.0 Safari/537.36"
    ),
    "Connection": "keep-alive",
    "Content-Type": "application/xml; charset=utf-8",
}



async def save_first_time_fetch(rss: Rss, new_rss: Dict[str, Any]) -> None:
    _file = DATA_PATH / f"{Rss.handle_name(rss.name)}.json"
    result = [cache_filter(entry) for entry in new_rss["entries"]]
    for r in result:
        r["hash"] = dict_hash(r)

    with TinyDB(
        _file,
        encoding="utf-8",
        sort_keys=True,
        indent=4,
        ensure_ascii=False,
    ) as db:
        db.insert_multiple(result)

    logger.info(f"{rss.name} 第一次抓取成功！")
    pr = ParsingRss(rss=rss)
    await pr.start(rss_name=rss.name, new_rss=new_rss)



# 抓取 feed，读取缓存，检查更新，对更新进行处理
async def start(rss: Rss) -> None:
    # 先检查订阅者是否合法
    if not any([rss.user_id, rss.group_id, rss.guild_channel_id]):
        await auto_stop(rss)
        return

    new_rss, cached = await fetch_rss(rss)
    # 检查是否存在rss记录
    _file = DATA_PATH / f"{Rss.handle_name(rss.name)}.json"
    first_time_fetch = not _file.exists()

    if cached:
        logger.info(f"{rss.name} 没有新信息")
        return

    if not new_rss or not new_rss.get("feed"):
        rss.error_count += 1
        logger.warning(f"{rss.name} 抓取失败！")

        if first_time_fetch:
            if config.rss_proxy and not rss.img_proxy:
                rss.img_proxy = True
                logger.info(f"{rss.name} 第一次抓取失败，自动使用代理抓取")
                await start(rss)
            else:
                await auto_stop(rss)

        if rss.error_count >= 100:
            await auto_stop(rss)
        return

    if new_rss.get("feed") and rss.error_count > 0:
        rss.error_count = 0

    if first_time_fetch:
        await save_first_time_fetch(rss, new_rss)
        return

    pr = ParsingRss(rss=rss)
    await pr.start(rss_name=rss.name, new_rss=new_rss)


async def auto_stop(rss: Rss) -> None:
    rss.stop = True
    rss.upsert()
    tr.delete_job(rss)
    cookies_str = "及 cookies " if rss.cookies else ""
    if not any([rss.user_id, rss.group_id, rss.guild_channel_id]):
        msg = f"{rss.name}[{rss.get_url()}]无人订阅！已自动停止更新！"
    elif rss.error_count >= 100:
        msg = f"{rss.name}[{rss.get_url()}]已经连续抓取失败超过 100 次！已自动停止更新！请检查订阅地址{cookies_str}！"
    else:
        msg = f"{rss.name}[{rss.get_url()}]第一次抓取失败！已自动停止更新！请检查订阅地址{cookies_str}！"
    await logger.warn(f"{msg}")


async def fetch_rss_backup(
    rss: Rss, session: aiohttp.ClientSession, proxy: Optional[str]
) -> Dict[str, Any]:
    d = {}
    for rsshub_url in config.rsshub_backup:
        rss_url = rss.get_url(rsshub=str(rsshub_url))
        try:
            resp = await session.get(rss_url, proxy=proxy)
            d = feedparser.parse(await resp.text())
            if d.get("feed"):
                logger.info(f"[{rss_url}]抓取成功！")
                break
        except Exception:
            logger.debug(f"[{rss_url}]访问失败！将使用备用 RSSHub 地址！")
            continue
    return d


# 获取 RSS 并解析为 json
async def fetch_rss(rss: Rss) -> Tuple[Dict[str, Any], bool]:
    rss_url = rss.get_url()
    local_host = ["localhost", "127.0.0.1"]
    proxy = get_proxy(rss.img_proxy) if URL(rss_url).host not in local_host else None
    cookies = rss.cookies or None
    headers = {
        "Accept": "application/xhtml+xml,application/xml,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "max-age=0",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/111.0.0.0 Safari/537.36"
        ),
        "Connection": "keep-alive",
        "Content-Type": "application/xml; charset=utf-8",
    }
    d = {}
    cached = False

    try:
        async with aiohttp.ClientSession(cookies=cookies, headers=headers, raise_for_status=True, timeout=aiohttp.ClientTimeout(10)) as session:
            resp = await session.get(rss_url, proxy=proxy)

            if not config.rsshub_backup:
                http_caching_headers = get_http_caching_headers(resp.headers)
                rss.etag = http_caching_headers.get("ETag")
                rss.last_modified = http_caching_headers.get("Last-Modified")
                rss.upsert()

            if resp.status == 200 and int(resp.headers.get("Content-Length", "1")) == 0 or resp.status == 304:
                cached = True

            d = feedparser.parse(await resp.text())

    except aiohttp.ClientError as e:
        if not URL(rss.url).scheme and config.rsshub_backup:
            logger.debug(f"[{rss_url}] 访问失败！将使用备用 RSSHub 地址！")
            d = await fetch_rss_backup(rss, session, proxy)
        else:
            logger.error(f"[{rss_url}] 访问失败！发生异常：{e}")

    except Exception as e:
        logger.error(f"发生未知异常：{e}")

    return d, cached

