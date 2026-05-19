"""
统一黑名单管理

合并模块0和模块1的黑名单域名与关键词，提供统一的过滤接口。
"""

from typing import Set
from urllib.parse import urlparse


# ========== 黑名单域名（排除搜索引擎、社交媒体、电商平台等） ==========

BLACKLIST_DOMAINS: Set[str] = {
    # 搜索引擎
    'baidu.com', 'bing.com', 'google.com', 'sogou.com', 'so.com',
    # 社交媒体
    'zhihu.com', 'weibo.com', 'douyin.com', 'bilibili.com',
    'douban.com', 'mp.weixin.qq.com',
    # 电商
    'taobao.com', 'tmall.com', 'jd.com', 'pinduoduo.com',
    '1688.com', 'alibaba.com', 'made-in-china.com',
    # 内容/资讯平台
    'csdn.net', 'jianshu.com', 'toutiao.com', '51cto.com',
    # 招聘平台
    'zhaopin.com', 'liepin.com', 'bosszhipin.com', '51job.com',
    # 分类信息
    '58.com', 'ganji.com',
    # 国际
    'youtube.com', 'facebook.com', 'twitter.com',
    # 广告
    'ad.com', 'doubleclick.net', 'googlesyndication.com',
    # 百度子站
    'map.baidu.com', 'image.baidu.com', 'wenku.baidu.com',
    'baike.baidu.com', 'zhidao.baidu.com', 'tieba.baidu.com',
    'pan.baidu.com', 'haokan.baidu.com',
    # 视频/游戏
    'video.', 'play.', 'music.', 'game.',
    # 快手
    'kuaishou.com',
}

# ========== URL路径黑名单关键词（路径中出现则过滤） ==========

BLACKLIST_KEYWORDS: Set[str] = {
    'login', 'signin', 'register', 'signup', 'password',
    'member', 'vip', 'pay', 'payment', 'cart', 'shop',
    'download', 'app', 'plugin', 'ad.', 'ads.',
    'zhaopin', 'job', 'career', 'recruit',
}


def is_blacklisted(url: str, extra_domains: Set[str] = None,
                   check_path: bool = False) -> bool:
    """检查URL是否在黑名单中

    Args:
        url: 待检查URL
        extra_domains: 额外的黑名单域名（合并检查）
        check_path: 是否检查路径中的黑名单关键词（模块1需要）

    Returns:
        True = 在黑名单中（应过滤）
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return True

        domain = parsed.netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]

        # 域名黑名单检查
        all_domains = BLACKLIST_DOMAINS
        if extra_domains:
            all_domains = all_domains | extra_domains

        for bd in all_domains:
            if bd in domain or domain in bd:
                return True

        # 路径黑名单检查（可选）
        if check_path:
            path_query = (parsed.path + parsed.query).lower()
            for bk in BLACKLIST_KEYWORDS:
                if bk in path_query:
                    return True

        return False
    except Exception:
        return True
