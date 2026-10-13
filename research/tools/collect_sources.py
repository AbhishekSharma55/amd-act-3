"""Save public research sources with retrieval metadata; no authenticated requests."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "sources"
OUT.mkdir(parents=True, exist_ok=True)


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.parts = []
        self.links = []
        self.anchor = None

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        if tag == "a":
            self.anchor = [dict(attrs).get("href"), []]

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = max(0, self.skip - 1)
        if tag == "a" and self.anchor:
            self.links.append({"url": self.anchor[0], "text": " ".join(self.anchor[1])})
            self.anchor = None

    def handle_data(self, text):
        if not self.skip and text.strip():
            self.parts.append(text.strip())
        if self.anchor and text.strip():
            self.anchor[1].append(text.strip())


SOURCES = {
    "amd-cloud-launch": "https://www.amd.com/en/blogs/2025/introducing-the-amd-developer-cloud.html",
    "amd-rocm-production": "https://www.amd.com/en/blogs/2026/amd-rocm-10-a-simpler-path-to-production-ai-on-amd.html",
    "amd-community-inference": "https://www.amd.com/en/developer/resources/technical-articles/2026/kimi-code-in-mxfp4-on-amd-gpus.html",
    "amd-playbooks": "https://www.amd.com/en/developer/resources/technical-articles/2026/launching-amd-ai-playbooks.html",
    "amd-gemma-support": "https://www.amd.com/en/developer/resources/technical-articles/2026/day-0-support-for-gemma-4-on-amd-processors-and-gpus.html",
    "amd-annual-report": "https://ir.amd.com/financial-information/sec-filings/content/0000002488-26-000018/amd-20251227.htm",
    "lablab-sponsor": "https://lablab.ai/sponsor",
    "lablab-win-guide": "https://lablab.ai/guide/how-to-win-an-ai-hackathon",
    "lablab-submission-guide": "https://lablab.ai/delivering-your-hackathon-solution",
    "lablab-guidelines": "https://lablab.ai/ai-articles/hackathon-guidelines",
    "evolus-developers": "https://evolus.ai/en/developers",
    "luma-milan": "https://luma.com/AMDHackathon-Milan",
    "luma-rome": "https://luma.com/AMDHackathon-Rome",
    "luma-imperia": "https://luma.com/AMDHackathon-Imperia",
    "winner-cctv": "https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-ii/roc-dragon/intelligence-for-existing-cctv-systems",
    "winner-cacheforge": "https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-ii/roc-m-roll/cacheforge-topology-aware-kv",
    "winner-ageband": "https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-ii/kiano/ageband",
    "winner-leagent": "https://lablab.ai/submissions/seswtk4cs6nz2gy2se0dtuf8",
    "winner-padayon": "https://lablab.ai/submissions/p7pvs9jxr2fr7g1kes8jrh18",
    "winner-announcement": "https://www.linkedin.com/posts/lablab-ai_three-tracks-real-amd-hardware-20000-activity-7500512595343405056-jZgl",
    "current-docuswarm": "https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii/yanero-rockstar/docuswarm-parallel-due-diligence-on-amd-gpus",
    "current-fiscalrag": "https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii/vyson-fiscalrag/vyson-fiscalrag-cited-tax-answers-on-amd-instinct",
    "current-compressor": "https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii/gheware/compressor-maintenance-copilot",
    "current-gas": "https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii/aisupersecuresystv2-3chaliveret/super-secure-syst-v23-6-gas-ai-guardian",
    "current-industrial": "https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii/industrial-fault-copilot/industrial-fault-copilot",
    "current-patient": "https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii/figueira-ai/patientkeeper-retorno",
    "current-forgesight": "https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii/amders/forgesight-ai",
    "current-returns": "https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii/khlab/why-they-return",
    "winner-cctv-readme": "https://raw.githubusercontent.com/CU-DrAgon/rocm-cctv-analysis/main/README.md",
    "winner-cacheforge-readme": "https://raw.githubusercontent.com/lucheeseng827/amd-hackathon/main/README.md",
    "act-i-live": "https://lablab.ai/ai-hackathons/amd-developer/live",
    "act-iii": "https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii",
    "act-iii-live": "https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii/live",
    "act-ii": "https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-ii",
    "act-ii-live": "https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-ii/live",
    "rulebook": "https://lablab.ai/hackathon-rules",
    "terms": "https://lablab.ai/terms-of-use",
    "tokenfactory": "https://notebooks.amd.com/tokenfactory",
    "evolus-track": "https://evolus.ai/en/hackathon",
    "evolus-conditions": "https://evolus.ai/en/hackathon-conditions",
    "evolus-event-blog": "https://evolus.ai/en/blog/evolus-amd-developer-hackathon-lablab",
    "winner-chaos": "https://lablab.ai/ai-hackathons/amd-developer/techmavericks/chaos-economy-multi-agent-rl-market-simulator",
    "act-i-announcement": "https://www.linkedin.com/posts/lablab-ai_10770-builders-walked-in-these-teams-activity-7472361155663978496-knnz",
}


def fetch(item):
    key, url = item
    meta = {"id": key, "url": url, "retrieved_at_utc": datetime.now(timezone.utc).isoformat()}
    try:
        response = requests.get(url, timeout=45)
        meta.update(status=response.status_code, final_url=response.url)
        raw = response.text
        (OUT / f"{key}.html").write_text(raw)
        if "text/html" in response.headers.get("Content-Type", ""):
            parser = TextParser()
            parser.feed(raw)
            text = "\n".join(parser.parts)
            (OUT / f"{key}-links.json").write_text(json.dumps(parser.links, indent=2))
            match = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', raw, re.S)
            if match:
                data = json.loads(match[1])
                (OUT / f"{key}-data.json").write_text(json.dumps(data, indent=2))
                compiled = data.get("props", {}).get("pageProps", {}).get("source", {}).get("compiledSource", "")
                if compiled:
                    strings = [json.loads(m[1]) for m in re.finditer(r'children:\s*("(?:\\.|[^"\\])*")', compiled)]
                    (OUT / f"{key}-extracted.txt").write_text("\n".join(strings))
        else:
            text = raw
        (OUT / f"{key}.txt").write_text(text)
        meta.update(bytes=len(response.content), snapshot=f"sources/{key}.txt")
    except Exception as error:
        meta["error"] = str(error)
    return meta


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(fetch, SOURCES.items()))
    (ROOT / "source-index.json").write_text(json.dumps(results, indent=2))
    for item in results:
        print(item["id"], item.get("status", "ERROR"), item.get("bytes", 0), item.get("error", ""))
