from flask import Blueprint, request, jsonify
import re
from flasgger import swag_from

import my_trigger as tr  
from rss_class import Rss  

rss_add_bp = Blueprint('rss_add', __name__)

@rss_add_bp.route('/', methods=['POST'])
@swag_from({
    'tags': ['RSS_feed'],
    'parameters': [
    {
        'name': 'body',
        'in': 'body',
        'required': True,
        'schema': {
            'type': 'object',
            'properties': {
                'RSS_ADD': {
                    'type': 'string',
                    'description': '订阅名和订阅地址，使用空格分割，例如: example_name http://example.com/rss'
                },
                'user_id': {
                    'type': 'string',
                    'description': '用户ID'
                },
                'group_id': {
                    'type': 'string',
                    'description': '群组ID'
                },
                'guild_channel_id': {
                    'type': 'string',
                    'description': '频道ID'
                }
            }
        }
    }],
    'responses': {
        200: {
            'description': '成功添加订阅',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'}
                }
            }
        },
        400: {
            'description': '请求错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'}
                }
            }
        }
    }
})
def add_rss():
    data = request.json
    if not data:
        return jsonify({"error": "请提供订阅信息"}), 400

    name_and_url = data.get('RSS_ADD', '')
    if not re.match(r"^\S+\s\S+$", name_and_url.strip()):
        return jsonify({"error": "请输入正确的订阅名和订阅地址，使用空格分割"}), 400

    try:
        name, url = name_and_url.strip().split(" ")
    except ValueError:
        return jsonify({"error": "请输入正确的订阅名和订阅地址，使用空格分割"}), 400

    if not name or not url:
        return jsonify({"error": "订阅名和订阅地址不能为空"}), 400

    if Rss.get_one_by_name(name):
        return jsonify({"error": f"已存在订阅名为 {name} 的订阅"}), 400

    response = add_feed(name, url, data.get('user_id'), data.get('group_id'), data.get('guild_channel_id'))
    return jsonify(response)


async def add_feed(name: str, url: str, user: str = None, group: str = None, guild_channel: str = None) -> dict:
    rss = Rss(name=name, url=url)
    rss.add_user_or_group_or_channel(user, group, guild_channel)

    try:
        await tr.add_job(rss)
    except Exception as e:
        return {"error": f"添加订阅失败: {str(e)}"}

    return {"message": f"已成功添加订阅 {name} ！"}
