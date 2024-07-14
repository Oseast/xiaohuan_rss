from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel
from typing import Dict

from rss_class import Rss
import my_trigger as tr


cookies_router = APIRouter()

class CookieRequest(BaseModel):
    name: str
    cookies: str

@cookies_router.post("/", response_model=Dict[str, str])
async def add_cookies(request: CookieRequest):
    # 获取请求数据
    name = request.name
    cookies = request.cookies

    # 判断是否有该名称订阅
    rss = Rss.get_one_by_name(name=name)
    if rss is None:
        raise HTTPException(status_code=404, detail=f"❌ 不存在该订阅: {name}")

    # 设置Cookies并添加任务
    rss.set_cookies(cookies)
    tr.add_job(rss)  # Assuming tr.add_job(rss) is a synchronous function

    return {"message": f"👏 {rss.name}的Cookies添加成功！"}


