"""爬虫管道：串联 fetch → clean → convert → dedup → write。

用法：
    python -m tools.crawler.pipeline --urls tools/crawler/urls/network.json
    python -m tools.crawler.pipeline --urls tools/crawler/urls/network.json --dry-run
    # default output: platform/.cache/crawler-candidates/{course}
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_PLATFORM = _ROOT / "platform"
if str(_PLATFORM) not in sys.path:
    sys.path.insert(0, str(_PLATFORM))

from tools.crawler.cleaner import clean_html, extract_title
from tools.crawler.converter import ArticleMeta, slug_from_title, to_knowledge_markdown
from tools.crawler.dedup import DedupIndex
from tools.crawler.fetcher import fetch_batch

logger = logging.getLogger(__name__)

def _display_path(path: Path) -> str:
    """Repo-relative POSIX path, or basename if outside the repo (no absolute leak)."""
    try:
        return path.resolve().relative_to(_ROOT).as_posix()
    except ValueError:
        return path.name


def run_pipeline(
    url_file: Path,
    output_dir: Path,
    *,
    dry_run: bool = False,
    delay: float = 2.0,
    allow_knowledge_write: bool = False,
) -> dict:
    """执行完整的爬虫管道。

    Args:
        url_file: URL 列表 JSON 文件路径
        output_dir: 输出目录（默认 platform/.cache/crawler-candidates/{course}）
        dry_run: 试运行（不写文件）
        delay: 每次请求间隔（秒）

    Returns:
        统计信息 dict
    """
    from app.source_policy import assert_crawler_output_allowed

    assert_crawler_output_allowed(
        output_dir, allow_knowledge_write=allow_knowledge_write
    )

    # 1. 加载 URL 列表
    with open(url_file, encoding="utf-8") as f:
        entries = json.load(f)

    logger.info("loaded %d URLs from %s", len(entries), _display_path(url_file))

    # 2. 批量抓取
    urls = [e["url"] for e in entries]
    fetch_results = fetch_batch(urls, delay=delay)

    # 3. 清洗 + 转换 + 去重
    dedup = DedupIndex()
    articles: list[tuple[str, str]] = []  # (filename, markdown_content)

    stats = {
        "total": len(entries),
        "fetched": 0,
        "cleaned": 0,
        "dedup_skipped": 0,
        "converted": 0,
        "written": 0,
        "output_dir": _display_path(output_dir),
    }

    for entry, result in zip(entries, fetch_results):
        if not result.success:
            logger.warning("SKIP fetch failed: %s — %s", entry["url"], result.error)
            continue
        stats["fetched"] += 1

        # 清洗
        text = clean_html(result.html, url=result.url)
        if len(text) < 100:
            logger.warning("SKIP too short (%d chars): %s", len(text), entry["url"])
            continue
        stats["cleaned"] += 1

        # 标题
        title = entry.get("topic", "") or extract_title(result.html)
        if not title:
            title = "未命名条目"

        # 去重
        is_dup, reason = dedup.check_and_add(entry["url"], title, text)
        if is_dup:
            logger.info("SKIP dedup [%s]: %s", reason, title)
            stats["dedup_skipped"] += 1
            continue

        # 转换
        meta = ArticleMeta(
            title=title,
            course=entry.get("course", "unknown"),
            tags=entry.get("tags", []),
            difficulty=entry.get("difficulty", "中等"),
            source_url=entry["url"],
        )
        md = to_knowledge_markdown(text, meta)
        stats["converted"] += 1

        # 文件名
        slug = slug_from_title(title)
        filename = f"{slug}.md"
        articles.append((filename, md))
        logger.info("converted: %s → %s", title, filename)

    # 4. 写入文件
    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        for filename, content in articles:
            out_path = output_dir / filename
            if out_path.exists():
                logger.info("SKIP existing file: %s", _display_path(out_path))
                continue
            out_path.write_text(content, encoding="utf-8")
            stats["written"] += 1
            logger.info("written: %s", _display_path(out_path))
    else:
        stats["written"] = len(articles)
        logger.info("[DRY RUN] would write %d files to %s", len(articles), _display_path(output_dir))

    logger.info("pipeline complete: %s", json.dumps(stats, indent=2))
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="知识库爬虫管道")
    parser.add_argument("--urls", required=True, help="URL 列表 JSON 文件路径")
    parser.add_argument("--output", default=None, help="输出目录（默认 platform/.cache/crawler-candidates/{course}）")
    parser.add_argument("--dry-run", action="store_true", help="试运行，不写文件")
    parser.add_argument("--delay", type=float, default=2.0, help="请求间隔（秒）")
    parser.add_argument(
        "--allow-knowledge-write",
        action="store_true",
        help="显式允许写入 knowledge/（仍不会自动进入检索，除非 frontmatter 已审核）",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    url_file = Path(args.urls)
    if not url_file.exists():
        logger.error("URL file not found: %s", url_file)
        sys.exit(1)

    # 推断输出目录
    if args.output:
        output_dir = Path(args.output)
    else:
        with open(url_file, encoding="utf-8") as f:
            entries = json.load(f)
        course = entries[0].get("course", "unknown") if entries else "unknown"
        from app.source_policy import default_crawler_output_dir

        output_dir = default_crawler_output_dir(course)

    from app.source_policy import SourceIngestDenied

    try:
        stats = run_pipeline(
            url_file,
            output_dir,
            dry_run=args.dry_run,
            delay=args.delay,
            allow_knowledge_write=args.allow_knowledge_write,
        )
    except SourceIngestDenied as exc:
        logger.error("%s", exc)
        sys.exit(2)
    print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
