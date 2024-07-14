import re
from contextlib import suppress
from copy import deepcopy
from typing import Any, List, Optional,Match

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from my_trigger import add_job, delete_job
from config import DATA_PATH
from rss_class import Rss
from utils import regex_validate
import my_trigger as tr  

rss_change_router = APIRouter()

class ChangeRequest(BaseModel):
    name_list: List[str]
    changes: str
    group_id: Optional[int] = None
    guild_channel_id: Optional[str] = None

attribute_dict = {
    "name": "name",
    "url": "url",
    "user": "user_id",
    "qun": "group_id",
    "channel": "guild_channel_id",
    "time": "time",
    "proxy": "img_proxy",
    "tl": "translation",
    "ot": "only_title",
    "op": "only_pic",
    "ohp": "only_has_pic",
    "downpic": "download_pic",
    "upgroup": "is_open_upload_group",
    "downopen": "down_torrent",
    "downkey": "down_torrent_keyword",
    "wkey": "down_torrent_keyword",
    "blackkey": "black_keyword",
    "bkey": "black_keyword",
    "mode": "duplicate_filter_mode",
    "img_num": "max_image_number",
    "stop": "stop",
    "pikpak": "pikpak_offline",
    "ppk": "pikpak_path_key",
    "forward": "send_forward_msg",
}

@rss_change_router.post("/")
async def change_rss(request: ChangeRequest):
    name_list = request.name_list
    change_info = request.changes
    group_id = request.group_id
    guild_channel_id = request.guild_channel_id

    rss_list = []
    for name in name_list:
        if rss_tmp := Rss.get_one_by_name(name=name):
            rss_list.append(rss_tmp)

    rss_list = await filter_rss_by_permissions(rss_list, change_info, group_id, guild_channel_id)

    if len(rss_list) > 1 and " name=" in change_info:
        raise HTTPException(status_code=400, detail="禁止将多个订阅批量改名，会因为名称相同起冲突。")

    rm_list_exist = re.search("rm_list='.+'", change_info)
    change_list = handle_rm_list(rss_list, change_info, rm_list_exist)
    changed_rss_list = await batch_change_rss(change_list, group_id, guild_channel_id, rss_list, rm_list_exist)

    rss_msg_list = [str(rss.hide_some_infos(group_id, guild_channel_id)) for rss in changed_rss_list]
    result_msg = f"修改了 {len(rss_msg_list)} 条订阅"
    if rss_msg_list:
        separator = "\n----------------------\n"
        result_msg += separator + separator.join(rss_msg_list)

    return {"message": result_msg}

async def filter_rss_by_permissions(rss_list: List[Rss], change_info: str, group_id: Optional[int], guild_channel_id: Optional[str]) -> List[Rss]:
    if group_id:
        if re.search(" (user|qun|channel)=", change_info):
            raise HTTPException(status_code=400, detail="禁止在群组中修改订阅账号！如要取消订阅请使用 deldy 命令！")
        rss_list = [rss for rss in rss_list if rss.group_id == [str(group_id)] and not rss.user_id and not rss.guild_channel_id]

    if guild_channel_id:
        if re.search(" (user|qun|channel)=", change_info):
            raise HTTPException(status_code=400, detail="禁止在子频道中修改订阅账号！如要取消订阅请使用 deldy 命令！")
        rss_list = [rss for rss in rss_list if rss.guild_channel_id == [str(guild_channel_id)] and not rss.user_id and not rss.group_id]

    if not rss_list:
        raise HTTPException(status_code=400, detail="请检查是否存在以下问题：\n1.要修改的订阅名不存在对应的记录\n2.当前群组或频道无权操作")

    return rss_list

async def validate_rss_change(key_to_change: str, value_to_change: str) -> None:
    mode_property_set = {"", "-1", "link", "title", "image", "or"}
    if key_to_change == "mode" and (set(value_to_change.split(",")) - mode_property_set or value_to_change == "or"):
        raise HTTPException(status_code=400, detail=f"去重模式参数错误！\n{key_to_change}={value_to_change}")
    elif key_to_change in {"downkey", "wkey", "blackkey", "bkey"} and not regex_validate(value_to_change.lstrip("+-")):
        raise HTTPException(status_code=400, detail=f"正则表达式错误！\n{key_to_change}={value_to_change}")
    elif key_to_change == "ppk" and not regex_validate(value_to_change):
        raise HTTPException(status_code=400, detail=f"正则表达式错误！\n{key_to_change}={value_to_change}")

async def batch_change_rss(change_list: List[str], group_id: Optional[int], guild_channel_id: Optional[str], rss_list: List[Rss], rm_list_exist: Optional[Match[str]] = None) -> List[Rss]:
    changed_rss_list = []

    for rss in rss_list:
        new_rss = deepcopy(rss)
        rss_name = rss.name

        for change_dict in change_list:
            key_to_change, value_to_change = change_dict.split("=", 1)

            if key_to_change in attribute_dict.keys():
                await validate_rss_change(key_to_change, value_to_change)
                handle_change_list(new_rss, key_to_change, value_to_change, group_id, guild_channel_id)
            else:
                raise HTTPException(status_code=400, detail=f"参数错误！\n{change_dict}")

        if new_rss.__dict__ == rss.__dict__ and not rm_list_exist:
            continue
        changed_rss_list.append(new_rss)
        new_rss.upsert(rss_name)

        if not new_rss.stop:
            await add_job(new_rss)
        elif not rss.stop:
            delete_job(new_rss)
    
    return changed_rss_list

def handle_property(value: str, property_list: List[Any]) -> List[Any]:
    if value == "-1":
        return []
    value_list = value.split(",")
    if value_list[0] == "":
        value_list.pop(0)
        return property_list + [i for i in value_list if i not in property_list]
    return list(dict.fromkeys(value_list))

def handle_regex_property(value: str, old_value: str) -> Optional[str]:
    result = None
    if not value:
        result = None
    elif value.startswith("+"):
        result = f"{old_value}|{value.lstrip('+')}" if old_value else value.lstrip("+")
    elif value.startswith("-"):
        if regex_list := old_value.split("|"):
            with suppress(ValueError):
                regex_list.remove(value.lstrip("-"))
            result = "|".join(regex_list) if regex_list else None
    else:
        result = value
    if isinstance(result, str) and not regex_validate(result):
        result = None
    return result

def handle_change_list(rss: Rss, key_to_change: str, value_to_change: str, group_id: Optional[int], guild_channel_id: Optional[str]) -> None:
    if key_to_change == "name":
        tr.delete_job(rss)
        rss.rename_file(str(DATA_PATH / f"{Rss.handle_name(value_to_change)}.json"))
    elif key_to_change in {"user", "qun", "channel"} and not group_id and not guild_channel_id or key_to_change == "mode":
        value_to_change = handle_property(value_to_change, getattr(rss, attribute_dict[key_to_change]))
    elif key_to_change == "time":
        value_to_change = handle_time_change(value_to_change)
    elif key_to_change in {"proxy", "tl", "ot", "op", "ohp", "downpic", "upgroup", "downopen", "stop", "pikpak", "forward"}:
        value_to_change = bool(int(value_to_change))
        if key_to_change == "stop" and not value_to_change and rss.error_count > 0:
            rss.error_count = 0
    elif key_to_change in {"downkey", "wkey", "blackkey", "bkey"}:
        value_to_change = handle_regex_property(value_to_change, getattr(rss, attribute_dict[key_to_change]))
    elif key_to_change == "ppk" and not value_to_change:
        value_to_change = None
    elif key_to_change == "img_num":
        value_to_change = int(value_to_change)
    setattr(rss, attribute_dict.get(key_to_change), value_to_change)

def handle_time_change(value_to_change: str) -> str:
    if not re.search(r"[_*/,-]", value_to_change):
        if int(float(value_to_change)) < 1:
            return "1"
        else:
            return str(int(float(value_to_change)))
    return value_to_change

def handle_rm_list(rss_list: List[Rss], change_info: str, rm_list_exist: Optional[Match[str]] = None) -> List[str]:
    rm_list = None

    if rm_list_exist:
        rm_list_str = rm_list_exist[0].lstrip().replace("rm_list=", "")
        rm_list = [i.strip("'") for i in rm_list_str.split("','")]
        change_info = change_info.replace(rm_list_exist[0], "").strip()

    if rm_list:
        for rss in rss_list:
            if len(rm_list) == 1 and rm_list[0] == "-1":
                setattr(rss, "content_to_remove", None)
            elif valid_rm_list := [i for i in rm_list if regex_validate(i)]:
                setattr(rss, "content_to_remove", valid_rm_list)

    change_list = [i.strip() for i in change_info.split(" ")]
    change_list.pop(0)

    return change_list

