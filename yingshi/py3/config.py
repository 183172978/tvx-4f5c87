def get_config():
    return {
        "spider": "file:///storage/emulated/0/json/demo_spider.py",
        "sites": [
            {
                "key": "demo",
                "name": "演示源",
                "type": 3,
                "api": "py_demo",
                "searchable": 1,
                "quickSearch": 1,
                "filterable": 0
            }
        ],
        "lives": [
            {
                "name": "直播演示",
                "type": 0,
                "url": "https://example.com/live.txt"
            }
        ],
        "wallpaper": "https://picsum.photos/1920/1080"
    }
