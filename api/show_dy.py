from typing import List, Optional

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, ValidationError

from rss_class import Rss

show_dy_router = APIRouter()


class RSSResponse(BaseModel):
    message: str


def handle_rss_list(rss_list: List[Rss]) -> str:
    rss_info_list = [
        f"（已停止）{i.name}：{i.url}" if i.stop else f"{i.name}：{i.url}"
        for i in rss_list
    ]
    return "\n\n".join(rss_info_list)


async def show_rss_by_name(
    rss_name: str, group_id: Optional[int], guild_channel_id: Optional[str]
) -> str:
    rss = Rss.get_one_by_name(rss_name)
    if (
        rss is None
        or (group_id and str(group_id) not in rss.group_id)
        or (guild_channel_id and guild_channel_id not in rss.guild_channel_id)
    ):
        return f"❌ 订阅 {rss_name} 不存在或未订阅！"
    else:
        # 隐私考虑，不展示除当前群组或频道外的群组、频道和QQ
        return str(rss.hide_some_infos(group_id, guild_channel_id))


@show_dy_router.get("/", response_model=RSSResponse)
async def show_rss(
    name: Optional[str] = Query(None, description="订阅名称"),
    group_id: Optional[int] = Query(None, description="群组ID"),
    guild_channel_id: Optional[str] = Query(None, description="频道ID"),
    user_id: Optional[str] = Query(None, description="用户ID"),
):
    try:
        if name:
            rss_msg = await show_rss_by_name(name, group_id, guild_channel_id)
            return {"message": rss_msg}

        if group_id:
            rss_list = Rss.get_by_group(group_id=int(group_id))
        elif guild_channel_id:
            rss_list = Rss.get_by_guild_channel(guild_channel_id=guild_channel_id)
        else:
            rss_list = Rss.get_by_user(user=user_id)

        if rss_list:
            msg_str = handle_rss_list(rss_list)
            return {"message": msg_str}
        else:
            raise HTTPException(status_code=404, detail="当前没有任何订阅！")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
