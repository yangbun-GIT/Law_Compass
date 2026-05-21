import argparse
import asyncio
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from tqdm import tqdm


BASE_URL = "https://accident.knia.or.kr"
START_URLS = [f"{BASE_URL}/myaccident{i}" for i in range(1, 6)]

ASSET_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg",
    ".ico", ".css", ".js", ".woff", ".woff2", ".ttf",
    ".mp4", ".avi", ".mov", ".zip"
)

BLACKLIST_TEXTS = {
    "홈으로",
    "메뉴열기",
    "카카오톡",
    "개인정보처리방침",
    "검색",
}

GLOBAL_MENU_TEXTS = {
    "과실비율의 이해",
    "과실비율 인정기준",
    "과실비율 분쟁심의위원회",
    "자료실",
    "과실비율 법률상담",
    "심의위원장 인사말",
    "심의위원회 소개",
    "심의제도 소개",
    "홍보자료",
    "기준정보",
    "연구자료",
    "설명자료",
    "인터넷 상담",
}


def clean_text(value: str) -> str:
    if not value:
        return ""
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()


def normalize_url(base_url: str, href: str) -> str | None:
    if not href:
        return None

    href = href.strip()

    if href.startswith("javascript:"):
        return None
    if href.startswith("mailto:"):
        return None
    if href.startswith("tel:"):
        return None

    absolute = urljoin(base_url, href)
    absolute, _fragment = urldefrag(absolute)
    return absolute


def is_same_site(url: str) -> bool:
    try:
        return urlparse(url).netloc == urlparse(BASE_URL).netloc
    except Exception:
        return False


def is_asset_url(url: str) -> bool:
    path = urlparse(url).path.lower()
    return path.endswith(ASSET_EXTENSIONS)


def extract_content_from_html(html: str, page_url: str) -> dict:
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    title = clean_text(soup.title.get_text(" ")) if soup.title else ""

    headings = []
    for tag in soup.find_all(["h1", "h2", "h3", "h4"]):
        text = clean_text(tag.get_text(" "))
        if text:
            headings.append(text)

    links = []
    for a in soup.find_all("a"):
        text = clean_text(a.get_text(" "))
        href = normalize_url(page_url, a.get("href", ""))
        if not text and not href:
            continue

        links.append({
            "text": text,
            "href": href,
            "is_same_site": is_same_site(href) if href else False,
            "is_asset": is_asset_url(href) if href else False,
        })

    images = []
    for img in soup.find_all("img"):
        src = normalize_url(page_url, img.get("src", ""))
        alt = clean_text(img.get("alt", ""))
        if src:
            images.append({
                "alt": alt,
                "src": src,
            })

    body_text = clean_text(soup.get_text("\n"))
    lines = [clean_text(line) for line in body_text.splitlines()]
    lines = [line for line in lines if line]

    return {
        "title": title,
        "headings": headings,
        "text": "\n".join(lines),
        "links": links,
        "images": images,
    }


async def body_text_hash(page) -> str:
    text = await page.evaluate("""
        () => document.body ? document.body.innerText : ""
    """)
    return sha256(clean_text(text))


async def extract_visible_items(page) -> list[dict]:
    """
    현재 화면에 보이는 메뉴/행/링크를 수집한다.
    depth는 왼쪽 들여쓰기 기준의 추정값이다.
    """
    return await page.evaluate("""
        () => {
            const scope =
                document.querySelector("main") ||
                document.querySelector("#container") ||
                document.querySelector(".container") ||
                document.querySelector(".content") ||
                document.body;

            const nodes = Array.from(
                scope.querySelectorAll("li, dt, dd, tr, a, button, summary, [role='button'], [onclick]")
            );

            const visible = nodes
                .filter(el => {
                    const rect = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    const text = (el.innerText || el.textContent || "").replace(/\\s+/g, " ").trim();

                    return (
                        text &&
                        rect.width > 0 &&
                        rect.height > 0 &&
                        style.visibility !== "hidden" &&
                        style.display !== "none"
                    );
                })
                .map(el => {
                    const rect = el.getBoundingClientRect();
                    const text = (el.innerText || el.textContent || "").replace(/\\s+/g, " ").trim();

                    return {
                        text,
                        tag: el.tagName.toLowerCase(),
                        class_name: el.className ? String(el.className) : "",
                        left: Math.round(rect.left),
                        top: Math.round(rect.top),
                        href: el.href || el.getAttribute("href") || null
                    };
                });

            const minLeft = Math.min(...visible.map(v => v.left));
            const unique = [];
            const seen = new Set();

            for (const item of visible) {
                const key = item.text + "|" + item.tag + "|" + item.left + "|" + item.top;
                if (seen.has(key)) continue;
                seen.add(key);

                unique.push({
                    ...item,
                    depth: Math.max(0, Math.round((item.left - minLeft) / 18))
                });
            }

            return unique;
        }
    """)


async def build_snapshot(page, label: str, trigger: dict | None = None) -> dict:
    html = await page.content()
    current_url = page.url
    extracted = extract_content_from_html(html, current_url)
    visible_items = await extract_visible_items(page)

    text = extracted["text"]

    return {
        "label": label,
        "url": current_url,
        "captured_at": datetime.now().isoformat(timespec="seconds"),
        "trigger": trigger,
        "content_hash": sha256(current_url + "\n" + text),
        "title": extracted["title"],
        "headings": extracted["headings"],
        "text": text,
        "visible_items": visible_items,
        "links": extracted["links"],
        "images": extracted["images"],
    }


async def get_click_candidates(page) -> list[dict]:
    """
    현재 페이지에서 클릭 가능한 후보를 찾는다.
    전역 메뉴/홈/카카오톡/이미지 링크 등은 Python 쪽에서 한 번 더 필터링한다.
    """
    return await page.evaluate("""
        () => {
            function cssPath(el) {
                if (el.id) {
                    return "#" + CSS.escape(el.id);
                }

                const path = [];

                while (el && el.nodeType === Node.ELEMENT_NODE && path.length < 8) {
                    let selector = el.nodeName.toLowerCase();

                    if (el.className && typeof el.className === "string") {
                        const classes = el.className
                            .split(/\\s+/)
                            .filter(Boolean)
                            .slice(0, 2)
                            .map(c => "." + CSS.escape(c))
                            .join("");
                        selector += classes;
                    }

                    let sibling = el;
                    let nth = 1;

                    while ((sibling = sibling.previousElementSibling)) {
                        if (sibling.nodeName.toLowerCase() === el.nodeName.toLowerCase()) {
                            nth++;
                        }
                    }

                    selector += `:nth-of-type(${nth})`;
                    path.unshift(selector);
                    el = el.parentElement;
                }

                return path.join(" > ");
            }

            const scope =
                document.querySelector("main") ||
                document.querySelector("#container") ||
                document.querySelector(".container") ||
                document.querySelector(".content") ||
                document.body;

            const rawNodes = Array.from(
                scope.querySelectorAll("a, button, summary, [role='button'], [onclick], li, dt, dd")
            );

            const candidates = [];

            for (const el of rawNodes) {
                if (el.closest("header, footer, nav")) continue;

                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                const text = (el.innerText || el.textContent || "").replace(/\\s+/g, " ").trim();
                const href = el.href || el.getAttribute("href") || null;
                const onclick = el.getAttribute("onclick") || "";

                const clickable =
                    ["A", "BUTTON", "SUMMARY"].includes(el.tagName) ||
                    el.getAttribute("role") === "button" ||
                    onclick ||
                    style.cursor === "pointer";

                if (!clickable) continue;
                if (!text && !href && !onclick) continue;
                if (rect.width <= 0 || rect.height <= 0) continue;
                if (style.visibility === "hidden" || style.display === "none") continue;

                candidates.push({
                    selector: cssPath(el),
                    text,
                    href,
                    onclick,
                    tag: el.tagName.toLowerCase(),
                    class_name: el.className ? String(el.className) : "",
                    top: Math.round(rect.top),
                    left: Math.round(rect.left)
                });
            }

            return candidates;
        }
    """)


def should_skip_candidate(candidate: dict, current_url: str) -> bool:
    text = clean_text(candidate.get("text", ""))
    href = candidate.get("href")

    if text in BLACKLIST_TEXTS:
        return True

    if text in GLOBAL_MENU_TEXTS:
        return True

    if len(text) > 120:
        return True

    if href:
        absolute = normalize_url(current_url, href)
        if not absolute:
            return False

        if not is_same_site(absolute):
            return True

        if is_asset_url(absolute):
            return True

        path = urlparse(absolute).path

        # myaccident 영역 중심으로 수집.
        # 필요하면 이 조건을 완화해서 사이트 전체를 수집할 수 있다.
        if not (
            path.startswith("/myaccident") or
            path == urlparse(current_url).path
        ):
            return True

    return False


async def close_dialogs_if_any(page):
    selectors = [
        "button:has-text('닫기')",
        "a:has-text('닫기')",
        ".close",
        ".btn_close",
        ".popup_close",
        "[aria-label*='닫']",
    ]

    for selector in selectors:
        try:
            locator = page.locator(selector)
            count = await locator.count()
            if count > 0:
                await locator.first.click(timeout=800, force=True)
                await page.wait_for_timeout(300)
                return
        except Exception:
            pass


async def collect_network_payload(response, storage: list, max_chars: int):
    try:
        url = response.url

        if not url.startswith(BASE_URL):
            return

        resource_type = response.request.resource_type
        if resource_type not in {"xhr", "fetch", "document"}:
            return

        status = response.status
        content_type = response.headers.get("content-type", "")

        item = {
            "url": url,
            "status": status,
            "resource_type": resource_type,
            "content_type": content_type,
            "captured_at": datetime.now().isoformat(timespec="seconds"),
        }

        if "application/json" in content_type:
            try:
                item["json"] = await response.json()
            except Exception:
                text = await response.text()
                item["text"] = text[:max_chars]
        else:
            text = await response.text()
            item["text"] = text[:max_chars]

        item["payload_hash"] = sha256(json.dumps(item, ensure_ascii=False, sort_keys=True))
        storage.append(item)

    except Exception:
        return


async def scrape_start_page(context, start_url: str, args) -> dict:
    page = await context.new_page()

    network_payloads = []
    network_tasks = []

    def on_response(response):
        task = asyncio.create_task(
            collect_network_payload(
                response=response,
                storage=network_payloads,
                max_chars=args.max_network_chars,
            )
        )
        network_tasks.append(task)

    page.on("response", on_response)

    result = {
        "start_url": start_url,
        "initial_snapshot": None,
        "snapshots": [],
        "clicked_pages": [],
        "network_payloads": network_payloads,
    }

    await page.goto(start_url, wait_until="networkidle", timeout=args.timeout_ms)
    await page.wait_for_timeout(args.after_load_delay_ms)

    result["initial_snapshot"] = await build_snapshot(
        page=page,
        label="initial",
        trigger=None,
    )

    clicked_keys = set()
    seen_snapshot_hashes = {result["initial_snapshot"]["content_hash"]}

    total_clicks = 0

    for _round in range(args.max_rounds):
        candidates = await get_click_candidates(page)

        filtered = []
        for candidate in candidates:
            if should_skip_candidate(candidate, page.url):
                continue

            key = "|".join([
                page.url,
                candidate.get("selector", ""),
                candidate.get("text", ""),
                candidate.get("href") or "",
                candidate.get("onclick") or "",
            ])

            if key in clicked_keys:
                continue

            candidate["_key"] = key
            filtered.append(candidate)

        if not filtered:
            break

        clicked_in_this_round = 0

        for candidate in filtered:
            if total_clicks >= args.max_clicks_per_page:
                break

            clicked_keys.add(candidate["_key"])
            before_url = page.url
            before_hash = await body_text_hash(page)

            try:
                locator = page.locator(candidate["selector"]).first()
                await locator.scroll_into_view_if_needed(timeout=1200)
                await locator.click(timeout=args.click_timeout_ms, force=True)
                total_clicks += 1
                clicked_in_this_round += 1

                await page.wait_for_timeout(args.after_click_delay_ms)

                try:
                    await page.wait_for_load_state("networkidle", timeout=args.network_idle_timeout_ms)
                except PlaywrightTimeoutError:
                    pass

                after_url = page.url
                after_hash = await body_text_hash(page)

                if after_url != before_url:
                    linked_snapshot = await build_snapshot(
                        page=page,
                        label="clicked_link_page",
                        trigger={
                            "text": candidate.get("text"),
                            "href": candidate.get("href"),
                            "selector": candidate.get("selector"),
                        },
                    )

                    result["clicked_pages"].append(linked_snapshot)

                    try:
                        await page.go_back(wait_until="networkidle", timeout=args.timeout_ms)
                        await page.wait_for_timeout(args.after_load_delay_ms)
                    except Exception:
                        await page.goto(start_url, wait_until="networkidle", timeout=args.timeout_ms)
                        await page.wait_for_timeout(args.after_load_delay_ms)

                    continue

                if after_hash != before_hash:
                    snapshot = await build_snapshot(
                        page=page,
                        label="after_click_dom_changed",
                        trigger={
                            "text": candidate.get("text"),
                            "href": candidate.get("href"),
                            "selector": candidate.get("selector"),
                        },
                    )

                    if snapshot["content_hash"] not in seen_snapshot_hashes:
                        seen_snapshot_hashes.add(snapshot["content_hash"])
                        result["snapshots"].append(snapshot)

                await close_dialogs_if_any(page)

            except Exception as e:
                result["snapshots"].append({
                    "label": "click_error",
                    "url": page.url,
                    "captured_at": datetime.now().isoformat(timespec="seconds"),
                    "trigger": {
                        "text": candidate.get("text"),
                        "href": candidate.get("href"),
                        "selector": candidate.get("selector"),
                    },
                    "error": str(e),
                })

        if clicked_in_this_round == 0:
            break

        if total_clicks >= args.max_clicks_per_page:
            break

    if network_tasks:
        await asyncio.gather(*network_tasks, return_exceptions=True)

    await page.close()

    result["network_payloads"] = dedupe_by_hash(
        network_payloads,
        hash_key="payload_hash",
    )

    return result


def dedupe_by_hash(items: list[dict], hash_key: str) -> list[dict]:
    seen = set()
    output = []

    for item in items:
        key = item.get(hash_key)
        if not key:
            key = sha256(json.dumps(item, ensure_ascii=False, sort_keys=True))

        if key in seen:
            continue

        seen.add(key)
        output.append(item)

    return output


def build_rag_documents(result: dict) -> list[dict]:
    """
    AI/RAG/검색용으로 바로 쓰기 좋게 평탄화한다.
    """
    documents = []

    for page_data in result["pages"]:
        candidates = []

        if page_data.get("initial_snapshot"):
            candidates.append(page_data["initial_snapshot"])

        candidates.extend(page_data.get("snapshots", []))
        candidates.extend(page_data.get("clicked_pages", []))

        for item in candidates:
            text = clean_text(item.get("text", ""))

            if not text:
                continue

            doc_id = sha256(item.get("url", "") + "|" + item.get("label", "") + "|" + text)

            documents.append({
                "doc_id": doc_id,
                "source": "KNIA 자동차사고 과실비율 정보포털",
                "source_url": item.get("url"),
                "label": item.get("label"),
                "title": item.get("title"),
                "headings": item.get("headings", []),
                "text": text,
                "metadata": {
                    "captured_at": item.get("captured_at"),
                    "trigger": item.get("trigger"),
                    "links": item.get("links", []),
                    "images": item.get("images", []),
                }
            })

    return dedupe_by_hash(documents, hash_key="doc_id")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="knia_fault_ratio.json")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--max-rounds", type=int, default=8)
    parser.add_argument("--max-clicks-per-page", type=int, default=250)
    parser.add_argument("--timeout-ms", type=int, default=30000)
    parser.add_argument("--click-timeout-ms", type=int, default=2500)
    parser.add_argument("--network-idle-timeout-ms", type=int, default=5000)
    parser.add_argument("--after-load-delay-ms", type=int, default=1000)
    parser.add_argument("--after-click-delay-ms", type=int, default=700)
    parser.add_argument("--max-network-chars", type=int, default=200000)
    args = parser.parse_args()

    final_result = {
        "metadata": {
            "site": "자동차사고 과실비율 분쟁심의위원회 / 과실비율 정보포털",
            "base_url": BASE_URL,
            "start_urls": START_URLS,
            "collected_at": datetime.now().isoformat(timespec="seconds"),
            "description": (
                "myaccident1~5 페이지의 기본 HTML, 아코디언 클릭 후 DOM 변화, "
                "클릭으로 연결되는 상세 페이지, Ajax/Fetch 응답을 수집한 JSON 데이터"
            ),
        },
        "pages": [],
        "rag_documents": [],
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=args.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )

        context = await browser.new_context(
            viewport={"width": 1366, "height": 1600},
            locale="ko-KR",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )

        for url in tqdm(START_URLS, desc="KNIA pages"):
            page_result = await scrape_start_page(context, url, args)
            final_result["pages"].append(page_result)

        await browser.close()

    final_result["rag_documents"] = build_rag_documents(final_result)

    output_path = Path(args.out)
    output_path.write_text(
        json.dumps(final_result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[완료] 저장 위치: {output_path.resolve()}")
    print(f"[완료] RAG 문서 수: {len(final_result['rag_documents'])}")


if __name__ == "__main__":
    asyncio.run(main())