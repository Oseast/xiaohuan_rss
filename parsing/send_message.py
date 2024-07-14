import asyncio
from collections import defaultdict
from contextlib import suppress
from typing import Any, Callable, Coroutine, DefaultDict, Dict, List, Tuple, Union

import arrow
import requests
from config import config
from rss_class import Rss
from .cache_manage import insert_into_cache_db, write_item
from logger_config import LoggerConfig

# 创建LoggerConfig实例并获取logger
logger_config = LoggerConfig(log_file='rss.log')
logger = logger_config.get_logger()


sending_lock: DefaultDict[Tuple[Union[int, str], str], asyncio.Lock] = defaultdict(
    asyncio.Lock
)


# 发送消息
async def send_msg(
    rss: Rss, messages: List[str], items: List[Dict[str, Any]], header_message: str
) -> bool:
    logger.info(f"发送消息: {rss.name}")
    if not messages:
        return False
    flag = False
    if rss.user_id:
        flag = any(
            await asyncio.gather(
                *[
                    send_one_message(
                        user_id=user_id,
                        messages=messages[0],
                        items=items[0],
                        header_message=header_message,
                    )
                    for user_id in rss.user_id 
                ]
            )
        )
    return flag

async def send_one_message(
    user_id:  str,
    messages: str,
    items: Dict[str, Any],
    header_message: str,
) -> bool:
    full_message = header_message + "\n" + "\n".join(messages)
    token = "sk-haidong010p"
    url = f"https://ideal-lattice.com/send_group_chat/?group_name={user_id}&message={full_message}&token={token}"
    response = requests.get(url)
    if response.status_code==200:
        logger.info(f"成功发送一条信息")
    else:
        logger.error(f"信息发送失败")
    print(response.status_code)
    return response.status_code == 200


# 发送消息并写入文件
async def handle_send_msgs(
    rss: Rss, messages: List[str], items: List[Dict[str, Any]], state: Dict[str, Any]
) -> None:
    db = state["tinydb"]
    header_message = state["header_message"]

    if await send_msg(rss, messages, items, header_message):
        if rss.duplicate_filter_mode:
            for item in items:
                insert_into_cache_db(
                    conn=state["conn"], item=item, image_hash=item["image_hash"]
                )

        for item in items:
            if item.get("to_send"):
                item.pop("to_send")

    else:
        for item in items:
            item["to_send"] = True

        state["error_count"] += len(messages)

    for item in items:
        write_item(db, item)
