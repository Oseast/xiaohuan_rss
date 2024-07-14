import re
import asyncio
from apscheduler.executors.pool import ProcessPoolExecutor, ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from async_timeout import timeout
from aiohttp import ClientSession

import rss_parsing
from rss_class import Rss
from logger_config import LoggerConfig

# 创建LoggerConfig实例并获取logger
logger_config = LoggerConfig(log_file='rss.log')
logger = logger_config.get_logger()

# 初始化Scheduler
scheduler = BackgroundScheduler(
    executors={
        'default': ThreadPoolExecutor(64),
        'processpool': ProcessPoolExecutor(8)
    }
)
scheduler.start()

# 检测某个RSS更新
async def check_update(rss: Rss) -> None:
    logger.info(f"{rss.name} 检查更新")
    try:
        wait_for = 5 * 60 if re.search(r"[_*/,-]", rss.time) else int(rss.time) * 60
        async with timeout(wait_for):
            await rss_parsing.start(rss)
    except asyncio.TimeoutError:
        logger.error(f"{rss.name} 检查更新超时，结束此次任务!")
    except Exception as e:
        logger.error(f"{rss.name} 检查更新时发生错误: {e}")

# Sync wrapper for the async function
def check_update_sync(rss: Rss) -> None:
    asyncio.run(check_update(rss))

def delete_job(rss: Rss) -> None:
    if scheduler.get_job(rss.name):
        scheduler.remove_job(rss.name)
        logger.info(f"删除任务{rss.name}")

# 加入订阅任务队列并立即执行一次
async def add_job(rss: Rss) -> None:
    print('进入add_job函数')
    delete_job(rss)
    # 加入前判断是否存在子频道或群组或用户，三者不能同时为空
    if any([rss.user_id, rss.group_id, rss.guild_channel_id]):
        rss_trigger(rss)
        await check_update(rss)

def rss_trigger(rss: Rss) -> None:
    if re.search(r"[_*/,-]", rss.time):
        my_trigger_cron(rss)
        return
    # 制作一个“time分钟/次”触发器
    trigger = IntervalTrigger(minutes=int(rss.time), jitter=10)
    # 添加任务
    scheduler.add_job(
        func=check_update_sync,  # Use the sync wrapper here
        trigger=trigger,  # 触发器
        args=(rss,),  # 函数的参数列表，注意：只有一个值时，不能省略末尾的逗号
        id=rss.name,
        misfire_grace_time=30,  # 允许的误差时间，建议不要省略
        max_instances=1,  # 最大并发
        coalesce=True,  # 积攒的任务是否只跑一次，是否合并所有错过的Job
    )
    logger.info(f"定时任务 {rss.name} 添加成功")

def my_trigger_cron(rss: Rss) -> None:
    # 解析参数
    tmp_list = rss.time.split("_")
    times_list = ["*/5", "*", "*", "*", "*"]
    for index, value in enumerate(tmp_list):
        if value:
            times_list[index] = value
    try:
        # 制作一个触发器
        trigger = CronTrigger(
            minute=times_list[0],
            hour=times_list[1],
            day=times_list[2],
            month=times_list[3],
            day_of_week=times_list[4],
        )
    except Exception:
        logger.exception(f"创建定时器错误！cron:{times_list}")
        return

    # 添加任务
    scheduler.add_job(
        func=check_update_sync,  # Use the sync wrapper here
        trigger=trigger,  # 触发器
        args=(rss,),  # 函数的参数列表，注意：只有一个值时，不能省略末尾的逗号
        id=rss.name,
        misfire_grace_time=30,  # 允许的误差时间，建议不要省略
        max_instances=1,  # 最大并发
        coalesce=True,  # 积攒的任务是否只跑一次，是否合并所有错过的Job
    )
    logger.info(f"定时任务 {rss.name} 添加成功")
