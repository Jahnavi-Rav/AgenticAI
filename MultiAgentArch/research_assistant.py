import re
import requests
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Optional
from urllib.parse import quote


MAX_SOURCES = 5
OUTDATED_DAYS_NORMAL = 365
OUTDATED_DAYS_TIME_SENSITIVE = 90
MIN_CITATION_OVERLAP = 0.25


USER_AGENT = "AgenticAIResearchAssistant/1.0 (https://github.com/Jahnavi-Rav/AgenticAI; learning project)"

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
})


TIME_SENSITIVE_WORDS = [
    "latest",
    "current",
    "today",
    "recent",
    "news",
    "price",
    "ceo",
    "president",
    "law",
    "regulation",
    "2025",
    "2026",
]


BAD_QUERIES = {
    "hi",
    "hello",
    "hey",
    "test",
    "ok",
    "yes",
    "no",
}


@dataclass
class Source:
    id: int
    title: str
    url: str
    summary: str
    last_updated: Optional[str]
    quality_score: float
    warnings: List[str] = field(default_factory=list)


def is_bad_query(query: str) -> bool:
    cleaned = query.strip().lower()

    if not cleaned:
        return True

    if cleaned in BAD_QUERIES:
        return True

    if len(cleaned) < 8:
        return True

    return False


def is_time_sensitive_query(query: str) -> bool:
    q = query.lower()
    return any(word in q for word in TIME_SENSITIVE_WORDS)


def days_since(timestamp: Optional[str]) -> Optional[int]:
    if not timestamp:
        return None

    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return (now - dt).days
    except Exception:
        return None


def citation_overlap(claim: str, source_text: str) -> float:
    claim_words = set(re.findall(r"\w+", claim.lower()))
    source_words = set(re.findall(r"\w+", source_text.lower()))

    if not claim_words:
        return 0.0

    overlap = claim_words & source_words
    return len(overlap) / len(claim_words)


def search_wikipedia(query: str, limit: int = MAX_SOURCES) -> List[Dict]:
    url = "https://en.wikipedia.org/w/api.php"

    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": limit,
        "format": "json",
    }

    try:
        response = SESSION.get(url, params=params, timeout=20)
        response.raise_for_status()

        data = response.json()
        return data.get("query", {}).get("search", [])

    except requests.exceptions.HTTPError as e:
        print("Wikipedia API HTTP error:", e)
        return []

    except requests.exceptions.Timeout:
        print("Wikipedia API timed out.")
        return []

    except requests.exceptions.RequestException as e:
        print("Wikipedia API request failed:", e)
        return []

    except ValueError:
        print("Wikipedia API returned invalid JSON.")
        return []


def get_page_summary(title: str) -> Optional[Dict]:
    encoded_title = quote(title)
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_title}"

    try:
        response = SESSION.get(url, timeout=20)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.HTTPError as e:
        print(f"Summary HTTP error for '{title}':", e)
        return None

    except requests.exceptions.Timeout:
        print(f"Summary request timed out for '{title}'.")
        return None

    except requests.exceptions.RequestException as e:
        print(f"Summary request failed for '{title}':", e)
        return None

    except ValueError:
        print(f"Summary returned invalid JSON for '{title}'.")
        return None


def get_last_revision(page_id: int) -> Optional[str]:
    url = "https://en.wikipedia.org/w/api.php"

    params = {
        "action": "query",
        "prop": "revisions",
        "rvprop": "timestamp",
        "pageids": page_id,
        "format": "json",
    }

    try:
        response = SESSION.get(url, params=params, timeout=20)
        response.raise_for_status()

        data = response.json()
        pages = data.get("query", {}).get("pages", {})
        page = pages.get(str(page_id), {})
        revisions = page.get("revisions", [])

        if not revisions:
            return None

        return revisions[0].get("timestamp")

    except requests.exceptions.HTTPError as e:
        print(f"Revision HTTP error for page {page_id}:", e)
        return None

    except requests.exceptions.Timeout:
        print(f"Revision request timed out for page {page_id}.")
        return None

    except requests.exceptions.RequestException as e:
        print(f"Revision request failed for page {page_id}:", e)
        return None

    except ValueError:
        print(f"Revision returned invalid JSON for page {page_id}.")
        return None


def source_quality_score(source: Source) -> float:
    score = 0.7

    if source.last_updated:
        score += 0.1

    if len(source.summary.split()) < 30:
        score -= 0.2

    if not source.url:
        score -= 0.1

    return max(0.0, min(score, 1.0))


def collect_sources(query: str) -> List[Source]:
    search_results = search_wikipedia(query)

    sources: List[Source] = []

    for item in search_results:
        page_id = item.get("pageid")
        title = item.get("title")

        if not page_id or not title:
            continue

        summary_data = get_page_summary(title)

        if not summary_data:
            continue

        summary = summary_data.get("extract", "")

        if not summary:
            continue

        page_url = (
            summary_data
            .get("content_urls", {})
            .get("desktop", {})
            .get("page", "")
        )

        last_updated = get_last_revision(page_id)

        source = Source(
            id=len(sources) + 1,
            title=title,
            url=page_url,
            summary=summary,
            last_updated=last_updated,
            quality_score=0.0,
        )

        source.quality_score = source_quality_score(source)
        sources.append(source)

    return sources


def check_outdated_sources(query: str, sources: List[Source]) -> None:
    time_sensitive = is_time_sensitive_query(query)

    if time_sensitive:
        freshness_limit = OUTDATED_DAYS_TIME_SENSITIVE
    else:
        freshness_limit = OUTDATED_DAYS_NORMAL

    for source in sources:
        age = days_since(source.last_updated)

        if age is None:
            source.warnings.append("Could not verify source freshness.")
            continue

        if age > freshness_limit:
            source.warnings.append(
                f"Possible outdated source: last updated {age} days ago."
            )


def check_weak_sources(sources: List[Source]) -> None:
    for source in sources:
        if source.quality_score < 0.6:
            source.warnings.append("Weak source: low quality score.")


def summarize_sources(sources: List[Source]) -> List[str]:
    bullets = []

    for source in sources:
        sentences = source.summary.split(".")
        first_sentence = sentences[0].strip()

        if first_sentence:
            bullets.append(f"{first_sentence}. [{source.id}]")

    return bullets


def compare_sources(sources: List[Source]) -> List[Dict]:
    comparison = []

    for source in sources:
        comparison.append({
            "id": source.id,
            "title": source.title,
            "quality_score": source.quality_score,
            "last_updated": source.last_updated,
            "warnings": source.warnings,
        })

    return comparison


def check_citation_mismatch(bullets: List[str], sources: List[Source]) -> List[str]:
    warnings = []
    source_map = {source.id: source for source in sources}

    for bullet in bullets:
        match = re.search(r"\[(\d+)\]", bullet)

        if not match:
            warnings.append(f"Missing citation: {bullet}")
            continue

        source_id = int(match.group(1))
        source = source_map.get(source_id)

        if not source:
            warnings.append(f"Invalid citation ID in: {bullet}")
            continue

        score = citation_overlap(bullet, source.summary)

        if score < MIN_CITATION_OVERLAP:
            warnings.append(
                f"Citation mismatch risk: claim may not be supported by source [{source_id}]."
            )

    return warnings


def research_pipeline(query: str) -> Dict:
    if is_bad_query(query):
        return {
            "answer": "Please enter a more specific research question.",
            "sources": [],
            "comparison": [],
            "warnings": ["Empty, vague, or greeting-style query."],
        }

    sources = collect_sources(query)

    if not sources:
        return {
            "answer": "I could not find usable sources.",
            "sources": [],
            "comparison": [],
            "warnings": ["Missing evidence or search API unavailable."],
        }

    check_outdated_sources(query, sources)
    check_weak_sources(sources)

    bullets = summarize_sources(sources)
    comparison = compare_sources(sources)
    citation_warnings = check_citation_mismatch(bullets, sources)

    answer = "\n".join(bullets)

    all_warnings = citation_warnings[:]

    for source in sources:
        for warning in source.warnings:
            all_warnings.append(f"Source [{source.id}] {warning}")

    return {
        "answer": answer,
        "sources": sources,
        "comparison": comparison,
        "warnings": all_warnings,
    }


def print_result(result: Dict) -> None:
    print("\nSummary:")
    print(result["answer"])

    print("\nSources:")
    if not result["sources"]:
        print("No sources.")
    else:
        for source in result["sources"]:
            print(f"[{source.id}] {source.title}")
            print(f"URL: {source.url}")
            print(f"Last updated: {source.last_updated}")
            print(f"Quality score: {source.quality_score}")
            print()

    print("Comparison:")
    if not result.get("comparison"):
        print("No comparison available.")
    else:
        for item in result["comparison"]:
            print(item)

    if result["warnings"]:
        print("\nWarnings:")
        for warning in result["warnings"]:
            print("-", warning)

    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    print("Autonomous Research Assistant")
    print("Type 'exit' to quit.\n")

    while True:
        query = input("Research question: ").strip()

        if query.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break

        result = research_pipeline(query)
        print_result(result)