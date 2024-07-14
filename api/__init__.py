from .rsshub_add import rsshub_add_router
from .del_dy import rss_del_router
from .add_cookies import cookies_router
from .show_all import show_all_router
from .show_dy import show_dy_router
from .change_dy import rss_change_router



routers = [
    (rsshub_add_router, "/rsshub_add", ["RSS_feed"]),
    (rss_del_router, "/rss_del", ["RSS_feed"]),
    (show_dy_router, "/show_rss", ["RSS_feed"]),
    (cookies_router, "/add_cookies", ["RSS_feed"]),
    (rss_change_router, "/change_rss", ["RSS_feed"]),
    (show_all_router, "/show_all", ["RSS_feed"]),
    # (rss_add_router, "/rss_add", ["RSS_feed"]),
]
