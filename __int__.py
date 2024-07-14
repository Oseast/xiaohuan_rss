from fastapi import FastAPI
from api import routers  # 确保 api 模块中的 routers 列表是可导入的
import tracemalloc
from rss_class import Rss
import my_trigger as tr
import asyncio

tracemalloc.start()
app = FastAPI()

# 遍历 routers 列表，包含所有路由
for router, prefix, tags in routers:
    app.include_router(router, prefix=prefix, tags=tags)

async def process_rss():
    print("任务启动")
    rss_list = Rss.read_rss()
    for rss in rss_list:
        await tr.add_job(rss)

if __name__ == "__main__":
    import uvicorn

    # 创建一个新的事件循环
    loop = asyncio.get_event_loop()
    # 在事件循环中运行 process_rss 协程
    loop.run_until_complete(process_rss())
    # 运行 uvicorn 服务器
    uvicorn.run(app, host="0.0.0.0", port=5000)