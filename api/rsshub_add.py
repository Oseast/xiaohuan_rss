from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from yarl import URL

from config import config
from rss_class import Rss
from .add_dy import add_feed
import my_trigger as tr  

class RSSHubAddRequest(BaseModel):
    name: Optional[str] = None
    route: Optional[str] = None
    user_id: Optional[str] = None
    group_id: Optional[str] = None

rsshub_add_router = APIRouter()

@rsshub_add_router.post("/")
async def handle_rsshub_add(data: RSSHubAddRequest):
    try:
        name = data.name.strip() if data.name else None
        route = data.route.strip() if data.route else None
        user_id = data.user_id.strip() if data.user_id else None
        group_id = data.group_id.strip() if data.group_id else None

        if not name:
            raise HTTPException(status_code=400, detail="订阅名不能为空，请重新输入")
        rss=Rss.get_one_by_name(name=name)
        
        if rss:
            if user_id in rss.user_id or group_id in rss.group_id:
                raise HTTPException(status_code=400, detail=f"当前用户或群组已存在名为 {name} 的订阅，请重新输入")
            rss.add_user_or_group_or_channel(user=user_id, group=group_id)
            try:
                print('进入try语句中')
                await tr.add_job(rss)
            except Exception as e:
                return {"error": f"添加订阅失败: {str(e)}"}

            return {"message": f"已成功添加订阅 {name} ！"}
        if not route:
            raise HTTPException(status_code=400, detail="路由名不能为空，请重新输入")

        rsshub_url = URL(str(config.rsshub))
        feed_url = f"{rsshub_url}{route}"
        await add_feed(name, feed_url, user_id, group_id)

        return {"message": "订阅添加成功"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
