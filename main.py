from flask import Flask, render_template_string, request, jsonify, redirect, url_for
import re
import requests
import sqlite3
from datetime import datetime

app = Flask(__name__)

# 初始化数据库
def init_db():
    conn = sqlite3.connect('history.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def url_get(url):
    html_content = requests.get(url=url).text
    m3u8_pattern = r'"url":"(.*?)"'
    m3u8_links = re.findall(m3u8_pattern, html_content)
    m3u8_links_list = []
    for link in m3u8_links:
        cleaned_link = link.replace('\\/', '/').replace('&amp;', '&')
        m3u8_links_list.append(cleaned_link)
    return m3u8_links_list

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>智能视频播放器</title>
    <link href="https://vjs.zencdn.net/7.20.1/video-js.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            padding: 20px;
            background-color: #f0f0f0;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .input-group {
            margin-bottom: 20px;
        }
        #myPlayer {
            width: 100%;
            height: auto;
            margin-top: 20px;
        }
        .playlist, .history {
            border-left: 2px solid #ddd;
            padding-left: 20px;
            max-height: 400px;
            overflow-y: auto;
        }
        .playlist-item, .history-item {
            cursor: pointer;
            padding: 10px;
            margin: 5px 0;
            background: #f8f9fa;
            border-radius: 4px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .playlist-item:hover, .history-item:hover {
            background: #e2e6ea;
        }
        .url-text {
            flex: 1;
            margin-right: 10px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .remove-btn {
            color: red;
            cursor: pointer;
            padding: 2px 8px;
            margin-left: 10px;
            border-radius: 3px;
        }
        .remove-btn:hover {
            background: #ffe6e6;
        }
        @media (max-width: 768px) {
            .playlist, .history {
                margin-top: 20px;
                border-left: none;
                border-top: 2px solid #ddd;
                padding-top: 20px;
            }
            .url-text {
                font-size: 14px;
            }
            .remove-btn {
                font-size: 18px;
                padding: 0 8px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="text-center my-4">智能视频播放器</h1>
        
        <div class="row">
            <!-- 左侧控制区 -->
            <div class="col-md-8">
                <div class="card shadow mb-4">
                    <div class="card-body">
                        <h5 class="card-title">直接播放</h5>
                        <div class="input-group mb-3">
                            <input type="text" id="directUrl" class="form-control" 
                                   placeholder="直接输入m3u8地址">
                            <button class="btn btn-success" onclick="playDirect()">立即播放</button>
                        </div>
                    </div>
                </div>

                <div class="card shadow">
                    <div class="card-body">
                        <h5 class="card-title">网页解析</h5>
                        <div class="input-group mb-3">
                            <input type="text" id="webUrl" class="form-control" 
                                   placeholder="输入包含视频的网页地址">
                            <button class="btn btn-primary" onclick="parseWeb()">解析网页</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 右侧区域 -->
            <div class="col-md-4">
                <!-- 播放列表 -->
                <div class="card shadow mb-4">
                    <div class="card-body">
                        <h5 class="card-title">解析结果</h5>
                        <div id="playlist" class="playlist"></div>
                    </div>
                </div>

                <!-- 历史记录 -->
                <div class="card shadow">
                    <div class="card-body">
                        <h5 class="card-title">历史记录 
                            <button class="btn btn-danger btn-sm float-end" onclick="clearHistory()">清空记录</button>
                        </h5>
                        <div id="historyList" class="history"></div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 播放器 -->
        <div class="card shadow mt-4">
            <div class="card-body">
                <video id="myPlayer" class="video-js vjs-default-skin vjs-fluid" 
                       controls preload="auto">
                    <source id="videoSource" src="" type="application/x-mpegURL">
                </video>
            </div>
        </div>
    </div>

    <script src="https://vjs.zencdn.net/7.20.1/video.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        const player = videojs('myPlayer', {
            html5: {
                hls: {
                    overrideNative: true
                }
            },
            responsive: true
        });

        // 初始化历史记录
        function loadHistory() {
            fetch('/history')
                .then(response => response.json())
                .then(data => {
                    const historyList = document.getElementById('historyList');
                    historyList.innerHTML = '';
                    data.forEach(item => {
                        const div = document.createElement('div');
                        div.className = 'history-item';
                        
                        // URL显示部分
                        const urlSpan = document.createElement('span');
                        urlSpan.className = 'url-text';
                        urlSpan.textContent = item.url;
                        urlSpan.title = item.url;
                        
                        // 删除按钮
                        const btn = document.createElement('span');
                        btn.className = 'remove-btn';
                        btn.innerHTML = '×';
                        btn.onclick = (e) => {
                            e.stopPropagation();
                            removeHistory(item.url); // 改为传递URL
                        };
                        
                        div.appendChild(urlSpan);
                        div.appendChild(btn);
                        
                        // 点击URL播放视频
                        div.onclick = () => {
                            player.src({ src: item.url, type: 'application/x-mpegURL' });
                            player.play();
                        };
                        
                        historyList.appendChild(div);
                    });
                });
        }

        // 播放后保存记录
        function saveHistory(url) {
            fetch('/history', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ url: url })
            });
        }

        // 删除单条记录（改为使用URL）
        function removeHistory(url) {
            fetch('/history?url=' + encodeURIComponent(url), {
                method: 'DELETE'
            }).then(() => loadHistory());
        }

        // 清空所有记录
        function clearHistory() {
            if (confirm('确定要清空所有历史记录吗？')) {
                fetch('/history', {
                    method: 'DELETE'
                }).then(() => loadHistory());
            }
        }

        // 直接播放功能
        function playDirect() {
            const url = document.getElementById('directUrl').value;
            if (url) {
                player.src({ src: url, type: 'application/x-mpegURL' });
                player.play();
                saveHistory(url);
            }
        }

        // 网页解析功能
        async function parseWeb() {
            const webUrl = document.getElementById('webUrl').value;
            if (!webUrl) return;

            try {
                const response = await fetch('/parse', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ url: webUrl })
                });

                const data = await response.json();
                const playlist = document.getElementById('playlist');
                playlist.innerHTML = '';

                data.urls.forEach(url => {
                    const div = document.createElement('div');
                    div.className = 'playlist-item';
                    div.textContent = url.slice(0, 60) + (url.length > 60 ? '...' : '');
                    div.title = url;
                    div.onclick = () => {
                        player.src({ src: url, type: 'application/x-mpegURL' });
                        player.play();
                        saveHistory(url);
                    };
                    playlist.appendChild(div);
                });

            } catch (error) {
                alert('解析失败，请检查链接有效性');
            }
        }

        // 页面加载时初始化历史记录
        document.addEventListener('DOMContentLoaded', loadHistory);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/parse', methods=['POST'])
def parse():
    data = request.get_json()
    url = data.get('url')
    try:
        urls = url_get(url)
        return jsonify({ "urls": urls })
    except Exception as e:
        return jsonify({ "error": str(e) }), 400

@app.route('/history', methods=['GET', 'POST', 'DELETE'])
def handle_history():
    conn = sqlite3.connect('history.db')
    c = conn.cursor()

    if request.method == 'GET':
        c.execute('SELECT * FROM history ORDER BY created_at DESC')
        rows = c.fetchall()
        history = [{"id": row[0], "url": row[1]} for row in rows]
        return jsonify(history)

    elif request.method == 'POST':
        url = request.json.get('url')
        if not url:
            return jsonify({"error": "URL is required"}), 400
        try:
            c.execute('INSERT OR IGNORE INTO history (url) VALUES (?)', (url,))
            conn.commit()
            return jsonify({"status": "success"})
        except sqlite3.IntegrityError:
            return jsonify({"status": "exists"})

    elif request.method == 'DELETE':
        # 获取URL参数
        url = request.args.get('url')
        if url:
            c.execute('DELETE FROM history WHERE url = ?', (url,))
        else:
            c.execute('DELETE FROM history')
        conn.commit()
        return jsonify({"status": "success"})

    conn.close()

if __name__ == '__main__':
    app.run(debug=True)