import os
import sys
import time
import logging
import re
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
import pypinyin
import requests
from pathlib import Path
import concurrent.futures
from croniter import croniter

# 从环境变量获取配置
PLEX_HOST = os.getenv("PLEX_HOST", "http://localhost:32400")
PLEX_TOKEN = os.getenv("PLEX_TOKEN", "")
CRON_SCHEDULE = os.getenv("CRON_SCHEDULE", "")  # 定时任务表达式
LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "7"))  # 日志保留天数

# 标签映射
TAGS = {
    "Anime": "动画",
    "Action": "动作",
    "Mystery": "悬疑",
    "Tv Movie": "电视电影",
    "Animation": "动画",
    "Crime": "犯罪",
    "Family": "家庭",
    "Fantasy": "奇幻",
    "Disaster": "灾难",
    "Adventure": "冒险",
    "Short": "短片",
    "Horror": "恐怖",
    "History": "历史",
    "Suspense": "悬疑",
    "Biography": "传记",
    "Sport": "运动",
    "Comedy": "喜剧",
    "Romance": "爱情",
    "Thriller": "惊悚",
    "Documentary": "纪录",
    "Indie": "独立",
    "Music": "音乐",
    "Sci-Fi": "科幻",
    "Western": "西部",
    "Children": "儿童",
    "Martial Arts": "武侠",
    "Drama": "剧情",
    "War": "战争",
    "Musical": "歌舞",
    "Film-noir": "黑色",
    "Science Fiction": "科幻",
    "Film-Noir": "黑色",
    "Food": "饮食",
    "War & Politics": "战争与政治",
    "Sci-Fi & Fantasy": "科幻",
    "Mini-Series": "迷你剧",
    "Reality": "真人秀",
    "Home and Garden": "家居与园艺",
    "Game Show": "游戏",
    "Awards Show": "颁奖典礼",
    "News": "新闻",
    "Talk": "访谈",
    "Talk Show": "脱口秀",
    "Travel": "旅行",
    "Soap": "肥皂剧",
}

TYPE = {"movie": 1, "show": 2, "artist": 8, "album": 9, "track": 10, "photo": 99}

# 初始化日志
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True, parents=True)
log_file = log_dir / "plexzh.log"  # 固定日志文件名

# 配置日志轮转 (最大10MB，保留3个备份)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=3  # 保留3个备份
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("PlexZH")

def has_chinese(string):
    for char in string:
        if '\u4e00' <= char <= '\u9fff':
            return True
    return False

def is_english(s):
    # 移除 "・" 字符
    s = s.replace('・', '')
    # 检查是否包含中文
    if not has_chinese(s):
        return True
    # 检查是否为日文
    for char in s:
        if '\u3040' <= char <= '\u30ff':
            return True
    return False

def convert_to_pinyin(text):
    str_a = pypinyin.pinyin(text, style=pypinyin.FIRST_LETTER)
    str_b = [str(str_a[i][0]).upper() for i in range(len(str_a))]
    return ''.join(str_b).replace("：", "").replace("（", "").replace("）", "").replace("，", "").replace("！", "").replace("？", "").replace("。", "").replace("；", "").replace("·", "").replace("-", "").replace("／", "").replace(",", "").replace("…", "").replace("!", "").replace("?", "").replace(".", "").replace(":", "").replace(";", "").replace("～", "").replace("~", "").replace("・", "")

def clean_old_logs(retention_days):
    """删除超过指定天数的旧日志文件"""
    logger.info(f"开始清理超过 {retention_days} 天的旧日志...")
    now = datetime.now()
    log_files = list(log_dir.glob("plexzh.log*"))  # 匹配所有轮转日志
    
    deleted_count = 0
    for file_path in log_files:
        # 跳过当前活动日志
        if file_path.name == "plexzh.log":
            continue
            
        try:
            # 获取文件修改时间
            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            
            # 检查文件是否过期
            if (now - file_mtime) > timedelta(days=retention_days):
                file_path.unlink()
                logger.info(f"删除旧日志文件: {file_path.name}")
                deleted_count += 1
        except Exception as e:
            logger.error(f"删除日志文件失败 {file_path.name}: {str(e)}")
    
    logger.info(f"日志清理完成，删除了 {deleted_count} 个旧日志文件")

def is_valid_cron(expression):
    """验证 cron 表达式是否有效"""
    try:
        croniter(expression)
        return True
    except:
        return False

def get_next_run_time(cron_expr):
    """计算下次运行时间"""
    base_time = datetime.now()
    cron = croniter(cron_expr, base_time)
    return cron.get_next(datetime)

class PlexServer:

    def __init__(self):
        self.s = requests.session()
        
        # 直接从环境变量获取配置
        self.host = PLEX_HOST
        self.token = PLEX_TOKEN
        
        if not self.host or not self.token:
            logger.error("PLEX_HOST 或 PLEX_TOKEN 环境变量未设置!")
            sys.exit(1)
        
        if self.host[-1] == "/":
            self.host = self.host[:-1]
        
        logger.info(f"已成功连接到服务器: {self.login()}")

    def login(self):
        try:
            self.s.headers = {'X-Plex-Token': self.token, 'Accept': 'application/json'}
            friendly_name = self.s.get(url=self.host).json()['MediaContainer']['friendlyName']
            return friendly_name
        except Exception as e:
            logger.error(f"服务器连接失败: {str(e)}")
            logger.error("请检查PLEX_HOST和PLEX_TOKEN配置是否正确")
            time.sleep(10)
            sys.exit(1)

    def select_library(self):
        data = self.s.get(
            url=f"{self.host}/library/sections/"
        ).json().get("MediaContainer", {}).get("Directory", [])

        library = [
            "{}> {}".format(i, data[i]["title"])
            for i in range(len(data))
        ]
        index = int(input("\n".join(library) + "\n请选择库: "))
        action_key = data[index]['key']
        action_type = int(input("\n1> 电影\n2> 节目\n8> 艺术家\n9> 专辑\n10> 单曲\n请选择要操作的类型: "))
        return action_key, action_type

    def list_library(self):
        data = self.s.get(
            url=f"{self.host}/library/sections/"
        ).json().get("MediaContainer", {}).get("Directory", [])
    
        libraries = [[int(x['key']), TYPE[x['type']], x['title']] for x in data]
        return libraries

    def list_media_keys(self, select):
        response = self.s.get(url=f'{self.host}/library/sections/{select[0]}/all?type={select[1]}').json()
        datas = response.get("MediaContainer", {}).get("Metadata", [])
    
        if not datas:
            if select[1] == 8:  # 如果是艺术家（歌手）
                logger.info("歌手数: 0")
            elif select[1] == 9:  # 如果是专辑
                logger.info("专辑数: 0")
            elif select[1] == 10:  # 如果是音轨
                logger.info("音轨数: 0")
            else:
                logger.info("媒体数: 0")
            return []
    
        media_keys = [data["ratingKey"] for data in datas]
    
        if select[1] == 8:  # 如果是艺术家（歌手）
            logger.info(f"歌手数: {len(media_keys)}")
        elif select[1] == 9:  # 如果是专辑
            logger.info(f"专辑数: {len(media_keys)}")
        elif select[1] == 10:  # 如果是音轨
            logger.info(f"音轨数: {len(media_keys)}")
        else:
            logger.info(f"媒体数: {len(media_keys)}")
    
        return media_keys

    def get_metadata(self, rating_key):
        metadata = self.s.get(url=f'{self.host}/library/metadata/{rating_key}').json()["MediaContainer"]["Metadata"][0]
        return metadata

    def put_title_sort(self, select, rating_key, sort_title, lock):
        self.s.put(
            url=f"{self.host}/library/metadata/{rating_key}",
            params={
                "type": select[1],
                "id": rating_key,
                "includeExternalMedia": 1,
                "titleSort.value": sort_title,
                "titleSort.locked": lock
            }
        )

    def put_genres(self, select, rating_key, tag, addtag):
        """变更流派标签。"""
        if TAGS.get(tag):  
            # 获取当前的所有标签
            current_tags = [genre.get("tag") for genre in self.get_metadata(rating_key).get('Genre', {})]
            # 移除原有的英文标签
            current_tags = [current_tag for current_tag in current_tags if current_tag != tag]
            # 创建一个新的参数列表
            params = {
                "type": select[1],
                "id": rating_key,
                "genre.locked": 1,
            }
            # 添加新的标签
            params.update({f"genre[{i}].tag.tag": current_tag for i, current_tag in enumerate(current_tags)})
            params[f"genre[{len(current_tags)}].tag.tag"] = addtag
            res = self.s.put(url=f"{self.host}/library/metadata/{rating_key}", params=params).text
            return res

    def put_styles(self, select, rating_key, tag, addtag):
        """变更风格标签。"""
        if TAGS.get(tag):  
            # 获取当前的所有标签
            current_tags = [style.get("tag") for style in self.get_metadata(rating_key).get('Style', {})]
            # 移除原有的英文标签
            current_tags = [current_tag for current_tag in current_tags if current_tag != tag]
            # 创建一个新的参数列表
            params = {
                "type": select[1],
                "id": rating_key,
                "style.locked": 1,
            }
            # 添加新的标签
            params.update({f"style[{i}].tag.tag": current_tag for i, current_tag in enumerate(current_tags)})
            params[f"style[{len(current_tags)}].tag.tag"] = addtag
            res = self.s.put(url=f"{self.host}/library/metadata/{rating_key}", params=params).text
            return res

    def put_mood(self, select, rating_key, tag, addtag):
        """变更情绪标签。"""
        if TAGS.get(tag):  
            # 获取当前的所有标签
            current_tags = [mood.get("tag") for mood in self.get_metadata(rating_key).get('Mood', {})]
            # 移除原有的英文标签
            current_tags = [current_tag for current_tag in current_tags if current_tag != tag]
            # 创建一个新的参数列表
            params = {
                "type": select[1],
                "id": rating_key,
                "mood.locked": 1,
            }
            # 添加新的标签
            params.update({f"mood[{i}].tag.tag": current_tag for i, current_tag in enumerate(current_tags)})
            params[f"mood[{len(current_tags)}].tag.tag"] = addtag
            res = self.s.put(url=f"{self.host}/library/metadata/{rating_key}", params=params).text
            return res

    def process_media(self, args):
        select, rating_key = args
        metadata = self.get_metadata(rating_key)
        title = metadata["title"]
        title_sort = metadata.get("titleSort", "")
        genres = [genre.get("tag") for genre in metadata.get('Genre', {})]
        styles = [style.get("tag") for style in metadata.get('Style', {})]
        moods = [mood.get("tag") for mood in metadata.get('Mood', {})]

        if not is_english(title) and (has_chinese(title_sort) or title_sort == ""):
            title_sort = convert_to_pinyin(title)
            self.put_title_sort(select, rating_key, title_sort, 1)
            logger.info(f"{title} → {title_sort}")

        if select[1] != 10:
            for genre in genres:
                if new_genre := TAGS.get(genre):
                    self.put_genres(select, rating_key, genre, new_genre)
                    logger.info(f"{title}: {genre} → {new_genre}")

            for style in styles:
                if new_style := TAGS.get(style):
                    self.put_styles(select, rating_key, style, new_style)
                    logger.info(f"{title}: {style} → {new_style}")

            for mood in moods:
                if new_mood := TAGS.get(mood):
                    self.put_styles(select, rating_key, mood, new_mood)
                    logger.info(f"{title}: {mood} → {new_mood}")

    def process_artist(self, args):
        select, rating_key = args
        metadata = self.get_metadata(rating_key)
        title = metadata["title"]
        title_sort = metadata.get("titleSort", "")
        genres = [genre.get("tag") for genre in metadata.get('Genre', {})]
        styles = [style.get("tag") for style in metadata.get('Style', {})]
        moods = [mood.get("tag") for mood in metadata.get('Mood', {})]
    
        if not is_english(title) and (has_chinese(title_sort) or title_sort == ""):
            title_sort = convert_to_pinyin(title)
            self.put_title_sort(select, rating_key, title_sort, 1)
            logger.info(f"{title} → {title_sort}")
    
        for genre in genres:
            if new_genre := TAGS.get(genre):
                self.put_genres(select, rating_key, genre, new_genre)
                logger.info(f"{title}: {genre} → {new_genre}")
    
        for style in styles:
            if new_style := TAGS.get(style):
                self.put_styles(select, rating_key, style, new_style)
                logger.info(f"{title}: {style} → {new_style}")
    
        for mood in moods:
            if new_mood := TAGS.get(mood):
                self.put_mood(select, rating_key, mood, new_mood)
                logger.info(f"{title}: {mood} → {new_mood}")
    
    def process_album(self, args):
        select, rating_key = args
        metadata = self.get_metadata(rating_key)
        title = metadata["title"]
        title_sort = metadata.get("titleSort", "")
        genres = [genre.get("tag") for genre in metadata.get('Genre', {})]
        styles = [style.get("tag") for style in metadata.get('Style', {})]
        moods = [mood.get("tag") for mood in metadata.get('Mood', {})]
    
        if not is_english(title) and (has_chinese(title_sort) or title_sort == ""):
            title_sort = convert_to_pinyin(title)
            self.put_title_sort(select, rating_key, title_sort, 1)
            logger.info(f"{title} → {title_sort}")
    
        for genre in genres:
            if new_genre := TAGS.get(genre):
                self.put_genres(select, rating_key, genre, new_genre)
                logger.info(f"{title}: {genre} → {new_genre}")
    
        for style in styles:
            if new_style := TAGS.get(style):
                self.put_styles(select, rating_key, style, new_style)
                logger.info(f"{title}: {style} → {new_style}")
    
        for mood in moods:
            if new_mood := TAGS.get(mood):
                self.put_mood(select, rating_key, mood, new_mood)
                logger.info(f"{title}: {mood} → {new_mood}")
    
    def process_track(self, args):
        select, rating_key = args
        metadata = self.get_metadata(rating_key)
        title = metadata["title"]
        title_sort = metadata.get("titleSort", "")
        moods = [mood.get("tag") for mood in metadata.get('Mood', {})]
    
        if not is_english(title) and (has_chinese(title_sort) or title_sort == ""):
            title_sort = convert_to_pinyin(title)
            self.put_title_sort(select, rating_key, title_sort, 1)
            logger.info(f"{title} → {title_sort}")
    
        for mood in moods:
            if new_mood := TAGS.get(mood):
                self.put_mood(select, rating_key, mood, new_mood)
                logger.info(f"{title}: {mood} → {new_mood}")

    def loop_all(self):
        library_list = self.list_library()
    
        for ll in library_list:
            if ll[1] != 99:
                select = ll[:2]
                logger.info(f"处理库: {ll[2]}")
                if ll[1] == 8:  # 如果是音乐库
    
                    # 处理艺术家（歌手）
                    artist_keys = self.list_media_keys([select[0], 8])
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        executor.map(self.process_artist, [(select, key) for key in artist_keys])
    
                    # 处理专辑
                    album_keys = self.list_media_keys([select[0], 9])
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        executor.map(self.process_album, [(select, key) for key in album_keys])
    
                    # 处理音轨
                    track_keys = self.list_media_keys([select[0], 10])
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        executor.map(self.process_track, [(select, key) for key in track_keys])
    
                else:
                    media_keys = self.list_media_keys(select)
    
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        executor.map(self.process_media, [(select, key) for key in media_keys])
    
                logger.info("")

    def put_collection_title_sort(self, select, rating_key, sort_title, lock):
        self.s.put(
            url=f"{self.host}/library/metadata/{rating_key}",
            params={
                "type": select[1],
                "id": rating_key,
                "includeExternalMedia": 1,
                "titleSort.value": sort_title,
                "titleSort.locked": lock
            }
        )

    def loop_all_collections(self):
        library_list = self.list_library()
        for ll in library_list:
            if ll[1] != 99:
                select = ll[:2]
                logger.info(f"处理库: {ll[2]}")
                response = self.s.get(url=f'{self.host}/library/sections/{select[0]}/collections').json()
                if "Metadata" not in response["MediaContainer"]:
                    logger.info(f"合集数: 0")
                    logger.info("")
                    continue
                collections = response["MediaContainer"]["Metadata"]
                logger.info(f"合集数: {len(collections)}")
                for collection in collections:
                    rating_key = collection['ratingKey']
                    title = collection['title']
                    title_sort = collection.get('titleSort', '')
                    if not is_english(title) and (has_chinese(title_sort) or title_sort == ""):
                        title_sort = convert_to_pinyin(title)
                        self.put_collection_title_sort(select, rating_key, title_sort, 1)
                        logger.info(f"{title} → {title_sort}")
                logger.info("")

def main_execution():
    # 清理旧日志
    clean_old_logs(LOG_RETENTION_DAYS)
    
    logger.info("===== 开始执行本地化任务 =====")
    plex_server = PlexServer()
    plex_server.loop_all()
    plex_server.loop_all_collections()
    logger.info("===== 任务执行完成 =====")

if __name__ == '__main__':
    if CRON_SCHEDULE:
        # 验证 cron 表达式
        if not is_valid_cron(CRON_SCHEDULE):
            logger.error(f"无效的 CRON 表达式: {CRON_SCHEDULE}")
            logger.error("请使用标准的 cron 表达式格式")
            sys.exit(1)
        
        logger.info(f"PlexZH - 已启用定时任务模式")
        logger.info(f"计划表达式: {CRON_SCHEDULE}")
        logger.info(f"日志保留天数: {LOG_RETENTION_DAYS} 天")
        
        while True:
            try:
                # 计算下次运行时间
                next_run = get_next_run_time(CRON_SCHEDULE)
                logger.info(f"下次执行时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # 计算等待时间（秒）
                wait_seconds = (next_run - datetime.now()).total_seconds()
                if wait_seconds > 0:
                    logger.info(f"等待 {wait_seconds:.0f} 秒后执行...")
                    time.sleep(wait_seconds)
                
                # 执行任务
                main_execution()
            except Exception as e:
                logger.error(f"任务执行失败: {str(e)}")
                # 防止频繁出错导致循环过载
                time.sleep(60)
    else:
        logger.info("PlexZH - 立即执行模式")
        logger.info(f"日志保留天数: {LOG_RETENTION_DAYS} 天")
        main_execution()
