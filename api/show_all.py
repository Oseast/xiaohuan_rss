import re
from typing import List, Optional

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, ValidationError

from rss_class import Rss

show_all_router = APIRouter()


class RSSResponse(BaseModel):
    name: str
    url: str
    user_id: Optional[List[str]]
    group_id: Optional[List[str]]
    guild_channel_id: Optional[List[str]]


def filter_results_by_keyword(
    rss_list: List[Rss],
    search_keyword: str,
    group_id: Optional[int],
    guild_channel_id: Optional[str],
) -> List[Rss]:
    return [
        i
        for i in rss_list
        if (
            re.search(search_keyword, i.name, flags=re.I)
            or re.search(search_keyword, i.url, flags=re.I)
            or (
                search_keyword.isdigit()
                and not group_id
                and not guild_channel_id
                and (
                    (i.user_id and search_keyword in i.user_id)
                    or (i.group_id and search_keyword in i.group_id)
                    or (i.guild_channel_id and search_keyword in i.guild_channel_id)
                )
            )
        )
    ]


def get_rss_list(group_id: Optional[int], guild_channel_id: Optional[str]) -> List[Rss]:
    if group_id:
        return Rss.get_by_group(group_id=group_id)
    elif guild_channel_id:
        return Rss.get_by_guild_channel(guild_channel_id=guild_channel_id)
    else:
        return Rss.read_rss()


@show_all_router.get("/", response_model=List[RSSResponse])
async def handle_rss_show_all(
    keyword: Optional[str] = Query(None, description="用于过滤结果的关键词"),
    group_id: Optional[int] = Query(None, description="群组ID，用于过滤结果"),
    guild_channel_id: Optional[str] = Query(None, description="频道ID，用于过滤结果"),
):
    try:
        rss_list = get_rss_list(group_id, guild_channel_id)

        if not rss_list:
            raise HTTPException(status_code=404, detail="当前没有任何订阅！")

        result = (
            filter_results_by_keyword(rss_list, keyword, group_id, guild_channel_id)
            if keyword
            else rss_list
        )

        if result:
            return result
        else:
            raise HTTPException(status_code=404, detail="当前没有任何订阅！")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
