from typing import List, Optional, Tuple

from fastapi import APIRouter,HTTPException, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import my_trigger as tr
from rss_class import Rss

rss_del_router = APIRouter()

class RSSDeleteRequest(BaseModel):
    rss_names: str = ""
    group_id: Optional[str] = None
    user_id: Optional[str] = None

@rss_del_router.post("/")
async def handle_rss_delete(data: RSSDeleteRequest = Body(...)):
    try:
        rss_names = data.rss_names.strip().split(",")
        group_id = data.group_id
        user_id = data.user_id

        if not rss_names:
            raise HTTPException(status_code=400, detail="要删除的订阅名不能为空，请重新输入")

        delete_successes, delete_failures = await process_rss_deletion(
            rss_names, group_id, user_id
        )

        result = []
        if delete_successes:
            if user_id:
                result.append(f'👏 当前用户成功取消订阅： {"、".join(delete_successes)} ！')
            elif group_id:
                result.append(f'👏 当前群组成功取消订阅： {"、".join(delete_successes)} ！')
            else:
                result.append(f'👏 成功删除订阅： {"、".join(delete_successes)} ！')
        if delete_failures:
            if user_id:
                result.append(f'❌ 当前用户没有订阅： {"、".join(delete_failures)} ！')
            elif group_id:
                result.append(f'❌ 当前群组没有订阅： {"、".join(delete_failures)} ！')
            else:
                result.append(f'❌ 未找到订阅： {"、".join(delete_failures)} ！')

        return JSONResponse(content={"message": "\n".join(result)}, status_code=200)

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


async def process_rss_deletion(
    rss_name_list: List[str], group_id: Optional[str], user_id: Optional[str]
) -> Tuple[List[str], List[str]]:
    delete_successes = []
    delete_failures = []

    for rss_name in rss_name_list:
        rss = Rss.get_one_by_name(name=rss_name)
        if rss is None:
            delete_failures.append(rss_name)
        elif user_id:
            if rss.delete_user(user_id):
                if not any([rss.group_id, rss.user_id]):
                    rss.delete_rss()
                    tr.delete_job(rss)
                else:
                    await tr.add_job(rss)
                delete_successes.append(rss_name)
            else:
                delete_failures.append(rss_name)
        elif group_id:
            if rss.delete_group(group=str(group_id)):
                if not any([rss.group_id, rss.user_id, rss.user_id]):
                    rss.delete_rss()
                    tr.delete_job(rss)
                else:
                    await tr.add_job(rss)
                delete_successes.append(rss_name)
            else:
                delete_failures.append(rss_name)
        else:
            rss.delete_rss()
            tr.delete_job(rss)
            delete_successes.append(rss_name)

    return delete_successes, delete_failures
