from flask import Flask, request, jsonify, render_template_string
import re
import json
import requests
from threading import BoundedSemaphore
from urllib.parse import unquote, urljoin, urlparse
from playwright.sync_api import sync_playwright, TimeoutError

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024

MAX_SHARE_TEXT_LENGTH = 4096
ALLOWED_DOUYIN_HOST = "douyin.com"
BROWSER_SEMAPHORE = BoundedSemaphore(value=1)


@app.after_request
def add_security_headers(response):
    """为页面和 API 响应添加不依赖反向代理的基础安全头。"""
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=()",
    )
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'",
    )
    return response


# 极简移动端自适应前端模板 (Tailwind CSS)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>抖音图文文案提取器</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .spinner {
            border: 3px solid rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            border-top: 3px solid #ffffff;
            width: 20px;
            height: 20px;
            animation: spin 1s linear infinite;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body class="bg-gradient-to-br from-gray-100 to-gray-200 min-h-screen text-gray-800 antialiased p-4 flex items-center justify-center">

    <div class="w-full max-w-lg bg-white rounded-2xl shadow-xl overflow-hidden">
        <div class="bg-black text-white p-5 text-center">
            <h1 class="text-2xl font-bold tracking-wider">抖音图文文案提取器</h1>
            <p class="text-sm text-gray-300 mt-1 opacity-80">视频 / 图文作品描述一键提取</p>
        </div>

        <div class="p-6 space-y-6">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">抖音分享文本或短链接</label>
                <textarea id="urlInput" rows="4" class="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-black focus:border-black outline-none transition-all resize-none" placeholder="在此粘贴... (例如: https://v.douyin.com/...)"></textarea>
            </div>

            <button id="submitBtn" onclick="extractDesc()" class="w-full bg-black hover:bg-gray-800 text-white font-semibold py-3.5 rounded-xl transition-colors flex items-center justify-center gap-2">
                <span id="btnText">立即提取文案</span>
                <div id="btnSpinner" class="spinner hidden"></div>
            </button>

            <div id="errorBox" class="hidden bg-red-50 border-l-4 border-red-500 text-red-700 p-4 rounded text-sm">
                <p id="errorMsg"></p>
            </div>

            <div id="resultBox" class="hidden space-y-3">
                <div class="flex justify-between items-center">
                    <h3 class="text-sm font-semibold text-gray-900 flex items-center gap-2">
                        <span class="w-2 h-2 rounded-full bg-green-500"></span> 提取结果
                    </h3>
                    <button id="copyBtn" type="button" onclick="copyResult()" class="text-xs text-blue-600 font-medium hover:text-blue-800 bg-blue-50 px-3 py-1 rounded-full transition">一键复制</button>
                </div>
                <div class="bg-gray-50 border border-gray-200 rounded-xl p-4 max-h-96 overflow-y-auto">
                    <p id="resultText" class="text-gray-700 text-sm whitespace-pre-wrap leading-relaxed select-all"></p>
                </div>
            </div>
        </div>
    </div>

    <script>
        async function extractDesc() {
            const input = document.getElementById('urlInput').value.trim();
            const btn = document.getElementById('submitBtn');
            const btnText = document.getElementById('btnText');
            const btnSpinner = document.getElementById('btnSpinner');
            const errorBox = document.getElementById('errorBox');
            const errorMsg = document.getElementById('errorMsg');
            const resultBox = document.getElementById('resultBox');
            const resultText = document.getElementById('resultText');

            if (!input) {
                showError('请输入抖音链接或分享文本');
                return;
            }

            // Reset UI
            errorBox.classList.add('hidden');
            resultBox.classList.add('hidden');
            btn.disabled = true;
            btn.classList.add('opacity-80', 'cursor-not-allowed');
            btnText.innerText = '正在拦截网络数据...';
            btnSpinner.classList.remove('hidden');

            try {
                const response = await fetch('/api/extract', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: input })
                });

                const data = await response.json();

                if (data.status === 'success') {
                    resultText.innerText = data.desc;
                    resultBox.classList.remove('hidden');
                } else {
                    showError(data.message || '提取失败，请重试');
                }
            } catch (err) {
                showError('网络请求错误，请确保后端服务正常运行');
            } finally {
                // Restore UI
                btn.disabled = false;
                btn.classList.remove('opacity-80', 'cursor-not-allowed');
                btnText.innerText = '立即提取文案';
                btnSpinner.classList.add('hidden');
            }
        }

        function showError(msg) {
            document.getElementById('errorMsg').innerText = msg;
            document.getElementById('errorBox').classList.remove('hidden');
        }

        function legacyCopy(text) {
            // 局域网 HTTP 页面通常无法使用 navigator.clipboard，
            // 使用临时 textarea 兼容移动端浏览器。
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.setAttribute('readonly', '');
            textarea.style.position = 'fixed';
            textarea.style.left = '-9999px';
            textarea.style.top = '0';
            textarea.style.opacity = '0';
            textarea.style.fontSize = '16px';
            document.body.appendChild(textarea);

            textarea.focus();
            textarea.select();
            textarea.setSelectionRange(0, textarea.value.length);

            let copied = false;
            try {
                copied = document.execCommand('copy');
            } catch (err) {
                copied = false;
            } finally {
                document.body.removeChild(textarea);
            }
            return copied;
        }

        function showCopyStatus(message, success) {
            const btn = document.getElementById('copyBtn');
            const originalText = '一键复制';
            btn.innerText = message;
            btn.classList.remove('text-blue-600', 'bg-blue-50', 'text-green-700', 'bg-green-50', 'text-red-700', 'bg-red-50');
            btn.classList.add(success ? 'text-green-700' : 'text-red-700');
            btn.classList.add(success ? 'bg-green-50' : 'bg-red-50');

            window.setTimeout(() => {
                btn.innerText = originalText;
                btn.classList.remove('text-green-700', 'bg-green-50', 'text-red-700', 'bg-red-50');
                btn.classList.add('text-blue-600', 'bg-blue-50');
            }, 1800);
        }

        async function copyResult() {
            const text = document.getElementById('resultText').innerText;
            if (!text.trim()) {
                showCopyStatus('没有可复制内容', false);
                return;
            }

            // Clipboard API 仅在 HTTPS 或 localhost 等安全上下文中可靠可用。
            if (window.isSecureContext && navigator.clipboard && navigator.clipboard.writeText) {
                try {
                    await navigator.clipboard.writeText(text);
                    showCopyStatus('复制成功 ✓', true);
                    return;
                } catch (err) {
                    // 权限被拒绝时继续使用兼容方案。
                }
            }

            if (legacyCopy(text)) {
                showCopyStatus('复制成功 ✓', true);
            } else {
                const result = document.getElementById('resultText');
                const selection = window.getSelection();
                const range = document.createRange();
                range.selectNodeContents(result);
                selection.removeAllRanges();
                selection.addRange(range);
                showCopyStatus('已选中，请手动复制', false);
            }
        }
    </script>
</body>
</html>
"""

def find_all_descs(data, descs):
    """递归遍历 JSON，找出所有 key 为 desc 的字符串值"""
    if isinstance(data, dict):
        for k, v in data.items():
            if k == 'desc' and isinstance(v, str) and v.strip():
                descs.append(v.strip())
            else:
                find_all_descs(v, descs)
    elif isinstance(data, list):
        for item in data:
            find_all_descs(item, descs)

GARBAGE_TEXTS = {"加载中", "读屏标签已关闭", "抖音", "点击重试", "网络错误", "抖音短视频", "记录美好生活", "原创音乐"}

def is_garbage(text):
    """检查文本是否为垃圾占位符（精确匹配或包含黑名单关键词）"""
    if not text:
        return True
    t = text.strip()
    for g in GARBAGE_TEXTS:
        if g in t:
            return True
    return False

def get_longest_desc(data):
    """返回列表中最长的 desc，自动过滤垃圾文本"""
    descs = []
    find_all_descs(data, descs)
    # 过滤掉垃圾占位符
    descs = [d for d in descs if not is_garbage(d)]
    if not descs:
        return None
    return max(descs, key=len)


def is_allowed_douyin_url(url):
    """只允许 http(s) 的 douyin.com 及其子域名，防止服务被用作 SSRF 跳板。"""
    if not isinstance(url, str) or not url:
        return False

    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower().rstrip(".")
    except ValueError:
        return False

    return (
        parsed.scheme.lower() in {"http", "https"}
        and (
            hostname == ALLOWED_DOUYIN_HOST
            or hostname.endswith(f".{ALLOWED_DOUYIN_HOST}")
        )
    )


def extract_douyin_url(share_text):
    """从分享文本中提取并规范化第一个合法抖音链接。"""
    if not isinstance(share_text, str):
        return None

    text = share_text.strip()
    if not text or len(text) > MAX_SHARE_TEXT_LENGTH:
        return None

    trailing_punctuation = ".,!?;:）》】}]'\""
    for match in re.finditer(
        r"https?://[^\s<>\"'，。！？；：、）》】}]+",
        text,
        re.IGNORECASE,
    ):
        candidate = match.group(0).rstrip(trailing_punctuation)
        if is_allowed_douyin_url(candidate):
            return candidate

    return None


def should_block_navigation(url, is_navigation_request, is_main_frame):
    """仅限制主页面跳转；图片、脚本等跨域静态资源仍可正常加载。"""
    return is_navigation_request and is_main_frame and not is_allowed_douyin_url(url)


def perform_extraction(share_text):
    """核心提取逻辑 (Playwright 网络拦截)"""
    url = extract_douyin_url(share_text)
    if not url:
        return {"status": "error", "message": "未找到有效的抖音链接。"}

    # ---------------- 预解析短链：移动端伪装 + 多重拦截 ----------------
    if (urlparse(url).hostname or "").lower() == "v.douyin.com":
        try:
            mobile_headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Cache-Control': 'no-cache',
            }
            res = requests.get(url, headers=mobile_headers, allow_redirects=False, timeout=10)

            # 优先检查 301/302/307 的 Location 响应头
            if res.status_code in (301, 302, 307, 308) and 'Location' in res.headers:
                redirect_url = urljoin(url, res.headers['Location'])
                if not is_allowed_douyin_url(redirect_url):
                    return {"status": "error", "message": "短链跳转到了不受信任的地址。"}
                url = redirect_url
            else:
                # JS 兜底解析：从 200 响应体中暴力提取隐藏的真实跳转链接
                real_url = None
                text = res.text

                # 模式1: href="https://www.douyin.com/..." 类跳转
                m = re.search(r'href="(https?://www\.douyin\.com/[^"]+)"', text)
                if m:
                    real_url = m.group(1)
                # 模式2: url 编码的跳转目标（如 /video/123 或 /note/123）
                if not real_url:
                    m = re.search(r'url[=:]\s*["\']?(https?%3A%2F%2F[^"\'&\s]+)', text, re.IGNORECASE)
                    if m:
                        real_url = unquote(m.group(1))
                # 模式3: window.location / location.href 赋值
                if not real_url:
                    m = re.search(r'(?:location\.href|window\.location)\s*=\s*["\']([^"\']+)["\']', text)
                    if m:
                        real_url = m.group(1)
                # 模式4: 常见的 open_url / jump_url 等 JSON 字段
                if not real_url:
                    m = re.search(r'(?:open_url|jump_url|redirect_url)[":\s]+["\']?(https?://www\.douyin\.com/[^"\'&\s]+)', text, re.IGNORECASE)
                    if m:
                        real_url = m.group(1)

                if real_url:
                    candidate_url = urljoin(url, real_url)
                else:
                    candidate_url = None

                if candidate_url and is_allowed_douyin_url(candidate_url):
                    url = candidate_url
                else:
                    return {"status": "error", "message": "短链解析被风控拦截，请手动在浏览器打开复制长链接后重试。"}
        except Exception:
            return {"status": "error", "message": "短链解析失败（网络异常），请手动在浏览器打开复制长链接后重试。"}
    # ----------------------------------------------------------------

    # ---------------- URL 智能重构：洗掉 modal_id 等干扰参数 ----------------
    modal_match = re.search(r'modal_id=(\d+)', url)
    if modal_match:
        url = f"https://www.douyin.com/note/{modal_match.group(1)}"
    # -----------------------------------------------------------------

    if not is_allowed_douyin_url(url):
        return {"status": "error", "message": "拒绝访问不受信任的地址。"}

    # 使用字典来保存状态，避免在多线程请求中产生全局变量污染
    ext_state = {"desc": None}

    def handle_response(response):
        try:
            if "application/json" in response.headers.get("content-type", ""):
                req_url = response.url
                if "detail" in req_url or "aweme" in req_url or "item" in req_url:
                    json_data = response.json()
                    longest_desc = get_longest_desc(json_data)

                    if longest_desc and not is_garbage(longest_desc):
                        if not ext_state["desc"] or len(longest_desc) > len(ext_state["desc"]):
                            ext_state["desc"] = longest_desc
        except Exception:
            pass

    try:
        with sync_playwright() as p:
            # -------- 关键修改：增强伪装，关闭无头模式 --------
            browser = p.chromium.launch(
                headless=False,  # 关闭无头模式，弹出真实窗口，极大降低被风控概率
                args=['--disable-blink-features=AutomationControlled']  # 隐藏自动化标志
            )
            # --------------------------------------------------

            context = browser.new_context(
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
                viewport={"width": 390, "height": 844},
                is_mobile=True,
                has_touch=True
            )
            page = context.new_page()

            def guard_main_frame_navigation(route, browser_request):
                if should_block_navigation(
                    browser_request.url,
                    browser_request.is_navigation_request(),
                    browser_request.frame == page.main_frame,
                ):
                    route.abort()
                else:
                    route.continue_()

            page.route("**/*", guard_main_frame_navigation)

            # 额外清除 webdriver 属性标志
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            page.on("response", handle_response)

            # 访问页面
            page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # 如果弹出登录/关闭遮罩，尝试自动关闭
            try:
                close_btn = page.locator("[class*='login'] [class*='close'], [class*='close']").first
                if close_btn.is_visible(timeout=1000):
                    close_btn.click(timeout=1000)
            except Exception:
                pass

            # 给出充足的时间等待所有异步接口数据返回
            page.wait_for_timeout(3000)

            # ========== SSR 源代码正则提取（核心杀招）==========
            try:
                html = page.content()

                # 路径1: <script id="RENDER_DATA" type="application/json"> (URL 编码的 JSON)
                m = re.search(r'<script[^>]*id="RENDER_DATA"[^>]*>(.*?)</script>', html, re.DOTALL)
                if m:
                    try:
                        decoded = unquote(m.group(1).strip())
                        data = json.loads(decoded)
                        ssr_desc = get_longest_desc(data)
                        if ssr_desc and not is_garbage(ssr_desc):
                            if not ext_state["desc"] or len(ssr_desc) > len(ext_state["desc"]):
                                ext_state["desc"] = ssr_desc
                    except Exception:
                        pass

                # 路径2: window._ROUTER_DATA = {...}（括号深度匹配）
                marker = 'window._ROUTER_DATA = '
                idx = html.find(marker)
                if idx != -1:
                    start = idx + len(marker)
                    if start < len(html) and html[start] == '{':
                        depth = 0
                        in_string = False
                        escape = False
                        for i in range(start, len(html)):
                            c = html[i]
                            if escape:
                                escape = False
                                continue
                            if c == '\\':
                                escape = True
                                continue
                            if c == '"' and not escape:
                                in_string = not in_string
                                continue
                            if in_string:
                                continue
                            if c == '{':
                                depth += 1
                            elif c == '}':
                                depth -= 1
                                if depth == 0:
                                    json_str = html[start:i+1]
                                    try:
                                        data = json.loads(json_str)
                                        ssr_desc = get_longest_desc(data)
                                        if ssr_desc and not is_garbage(ssr_desc):
                                            if not ext_state["desc"] or len(ssr_desc) > len(ext_state["desc"]):
                                                ext_state["desc"] = ssr_desc
                                    except Exception:
                                        pass
                                    break
            except Exception:
                pass

            # ========== DOM 视觉提取（三层递进，最高优先级）==========
            dom_desc = None
            raw = page.evaluate("""() => {
                // ---- Tier 1: 扩大选择器阵列（移动端 + PC 端「抖音精选」+ 图文）----
                const selectors = [
                    // 移动端 data-e2e 锚点
                    "[data-e2e='video-desc']",
                    "[data-e2e='note-desc']",
                    "[data-e2e='feed-desc']",
                    // 移动端 H5 常见类名
                    ".video-info",
                    ".note-desc",
                    ".detail-desc-wrap",
                    ".video-title",
                    ".note-info",
                    ".desc-wrap",
                    ".note-content",
                    ".aweme-title",
                    // PC 端「抖音精选」
                    ".video-info-detail",
                    ".account-info-desc",
                    // 通用降级
                    ".desc-text",
                    ".video-desc",
                    ".item-desc",
                    ".feed-desc",
                    ".card-desc",
                    ".detail-desc",
                    ".content-desc",
                    ".info-desc",
                    ".semi-desc",
                    "[class*='video-info'] [class*='desc']"
                ];
                for (let sel of selectors) {
                    try {
                        const el = document.querySelector(sel);
                        if (el && el.textContent.trim().length > 0) {
                            return el.textContent;
                        }
                    } catch(e) {}
                }

                // ---- Tier 2: Meta 保底 ----
                const meta = document.querySelector("meta[name='description']");
                if (meta && meta.content.trim()) {
                    return meta.content;
                }

                // ---- Tier 3: 终极暴力保底 — 遍历所有可见文本节点，返回最长的那一个 ----
                const skipTags = new Set([
                    'SCRIPT','STYLE','NOSCRIPT','SVG','META','LINK','HEAD',
                    'NAV','FOOTER','HEADER','IFRAME','INPUT','TEXTAREA',
                    'SELECT','CODE','PRE','BUTTON','A','LABEL','OPTION'
                ]);
                let best = '';
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    { acceptNode: (node) => {
                        if (!node.parentElement) return NodeFilter.FILTER_REJECT;
                        if (skipTags.has(node.parentElement.tagName)) return NodeFilter.FILTER_REJECT;
                        return NodeFilter.FILTER_ACCEPT;
                    }}
                );
                let node;
                while (node = walker.nextNode()) {
                    const t = node.textContent.trim();
                    if (t.length > best.length) best = t;
                }
                return best;
            }""")
            if raw and raw.strip():
                dom_desc = ' '.join(raw.split())

            # 谁长用谁：DOM 文本更长则覆盖抓包结果
            if dom_desc and not is_garbage(dom_desc):
                if not ext_state["desc"] or len(dom_desc) > len(ext_state["desc"]):
                    ext_state["desc"] = dom_desc

            # ========== 兜底：标题提取 ==========
            if not ext_state["desc"] or len(ext_state["desc"].strip()) == 0:
                try:
                    page.wait_for_function("document.title !== '' && document.title !== '抖音'", timeout=3000)
                except TimeoutError:
                    pass
                title = page.title()
                if title:
                    title_desc = None
                    if "- 抖音" in title:
                        title_desc = title.replace("- 抖音", "").strip()
                    elif title != "抖音":
                        title_desc = title.strip()
                    if title_desc and not is_garbage(title_desc):
                        ext_state["desc"] = title_desc

            browser.close()

        if ext_state["desc"]:
            clean_desc = ext_state["desc"].replace('\\/', '/').strip()
            return {"status": "success", "desc": clean_desc}
        else:
            return {"status": "error", "message": "未能成功提取到文案。页面可能需要登录验证或遇到了强风控。"}

    except TimeoutError:
         return {"status": "error", "message": "服务端渲染页面加载超时，请重试。"}
    except Exception as e:
        return {"status": "error", "message": f"服务端抓取失败: {str(e)}"}


# --- Flask 路由 ---

@app.route('/')
def index():
    """返回前端 HTML 页面"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/extract', methods=['POST'])
def api_extract():
    """处理前端发来的提取请求"""
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or 'url' not in data:
        return jsonify({"status": "error", "message": "请求格式错误，缺少 url 字段"}), 400

    share_text = data['url']
    if not isinstance(share_text, str):
        return jsonify({"status": "error", "message": "url 字段必须是字符串"}), 400

    if not share_text.strip():
        return jsonify({"status": "error", "message": "请输入抖音分享文本或链接"}), 400

    if len(share_text) > MAX_SHARE_TEXT_LENGTH:
        return jsonify({"status": "error", "message": "输入内容过长"}), 400

    if not extract_douyin_url(share_text):
        return jsonify({"status": "error", "message": "请输入有效的抖音链接"}), 400

    if not BROWSER_SEMAPHORE.acquire(blocking=False):
        return jsonify({
            "status": "error",
            "message": "服务正在处理其他请求，请稍后重试",
        }), 429

    try:
        result = perform_extraction(share_text)
        status_code = 200 if result.get("status") == "success" else 422
        return jsonify(result), status_code
    finally:
        BROWSER_SEMAPHORE.release()


@app.errorhandler(413)
def request_entity_too_large(_error):
    """返回 JSON，避免前端把过大的请求误判为网络故障。"""
    return jsonify({"status": "error", "message": "请求内容过大"}), 413

if __name__ == '__main__':
    print("=" * 50)
    print("  抖音文案提取 Web 服务已启动！")
    print("  请确保你的手机和电脑连接在同一个局域网 (Wi-Fi) 下。")
    print("  在手机浏览器中输入你的电脑局域网 IP 地址加端口号，例如:")
    print("  http://192.168.x.x:5000")
    print("=" * 50)
    # 监听 0.0.0.0，使局域网内其他设备可用
    app.run(host='0.0.0.0', port=5000, threaded=True)
