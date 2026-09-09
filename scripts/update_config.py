#!/usr/bin/env python3
"""Generate the personal OpenClash files from Aethersailor upstream sources."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_REPOSITORY = "Aethersailor/Custom_OpenClash_Rules"
UPSTREAM_REF = "main"
UPSTREAM_COMMIT_URL = (
    f"https://api.github.com/repos/{UPSTREAM_REPOSITORY}/commits/{UPSTREAM_REF}"
)
OUTPUT_YAML = ROOT / "cfg/yaml/Custom_Clash_Full.yaml"
OUTPUT_CONF = ROOT / "overwrite/yaml/Custom_Clash_Full.conf"
METADATA = ROOT / "upstream-source.json"
CUSTOM_RULES = ROOT / "custom-rules.yaml"

REGION_GROUPS = (
    "🇭🇰 香港节点",
    "🇺🇸 美国节点",
    "🇯🇵 日本节点",
    "🇸🇬 新加坡节点",
    "🇼🇸 台湾节点",
    "🇰🇷 韩国节点",
    "🇨🇦 加拿大节点",
    "🇬🇧 英国节点",
    "🇫🇷 法国节点",
    "🇩🇪 德国节点",
    "🇳🇱 荷兰节点",
    "🇹🇷 土耳其节点",
    "🇷🇺 俄罗斯节点",
    "🌐 其他地区",
    "🏠 家宽节点",
    "🐢 低倍率节点",
)

# These are the groups in which a user must be able to choose a region or an
# individual provider node.  The upstream template supplies the latter via use.
BUSINESS_SELECT_GROUPS = (
    "🚀 手动选择",
    "💬 即时通讯",
    "🌐 社交媒体",
    "📞 Talkatone",
    "🚀 GitHub",
    "🤖 ChatGPT",
    "🤖 Copilot",
    "🤖 国外AI服务",
    "🤖 国内AI服务",
    "🎶 TikTok",
    "📹 YouTube",
    "🎥 Netflix",
    "🎥 DisneyPlus",
    "🎥 HBO",
    "🎥 PrimeVideo",
    "🎥 AppleTV+",
    "🎥 Emby",
    "🎻 Spotify",
    "📺 Bahamut",
    "🌎 国外媒体",
    "🛒 国外电商",
    "🪙 加密货币",
    "📢 谷歌FCM",
    "🇬 谷歌服务",
    "🍎 苹果服务",
    "Ⓜ️ 微软服务",
    "💾 OneDrive",
    "💳 PayPal",
    "🎮 游戏平台",
    "🎮 Steam",
    "⏬ PT站点",
    "🚀 测速工具",
    "🌍 国外域名",
    "🐟 漏网之鱼",
)


def fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "sqzhang0814-Custom-OpenClash-Rules"})
    with urlopen(request, timeout=30) as response:  # nosec B310: fixed HTTPS URLs above
        return response.read().decode("utf-8")


def raw_url(commit: str, path: str) -> str:
    return f"https://raw.githubusercontent.com/{UPSTREAM_REPOSITORY}/{commit}/{path}"


def group_block(yaml_text: str, group_name: str) -> str:
    match = re.search(
        rf'^  - name: "{re.escape(group_name)}"\n(?P<body>.*?)(?=^  - name: |\Z)',
        yaml_text,
        flags=re.MULTILINE | re.DOTALL,
    )
    if not match:
        raise ValueError(f"Upstream no longer contains proxy group: {group_name}")
    return match.group(0)


def validate_upstream_yaml(yaml_text: str) -> None:
    if yaml_text.count("\nrules:\n") != 1:
        raise ValueError("Expected exactly one top-level rules section")
    if "proxy-providers:\n  provider1:" not in yaml_text:
        raise ValueError("Expected provider1 in proxy-providers")

    for name in REGION_GROUPS:
        block = group_block(yaml_text, name)
        if "    type: url-test\n" not in block or "    use:\n      - provider1\n" not in block:
            raise ValueError(f"Region group must remain url-test with provider1: {name}")

    for name in BUSINESS_SELECT_GROUPS:
        block = group_block(yaml_text, name)
        if "    type: select\n" not in block or "    use:\n      - provider1\n" not in block:
            raise ValueError(
                f"Business group must remain selectable and expose provider nodes: {name}"
            )


def read_custom_rules() -> list[str]:
    rules: list[str] = []
    for line in CUSTOM_RULES.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = re.fullmatch(r'-\s+"([^"]+)"', stripped)
        if not match:
            raise ValueError(f"Invalid personal rule syntax: {line!r}")
        rules.append(match.group(1))
    if not rules:
        raise ValueError("No personal rules found")
    return rules


def render_yaml(upstream_yaml: str, personal_rules: list[str], source_url: str) -> str:
    marker = "rules:\n"
    if "# Personal rules managed in custom-rules.yaml" in upstream_yaml:
        raise ValueError("Upstream source unexpectedly contains the local rules marker")
    rendered_rules = "".join(f'  - "{rule}"\n' for rule in personal_rules)
    insertion = (
        "rules:\n"
        "  # Personal rules managed in custom-rules.yaml. Keep these above upstream rules.\n"
        f"{rendered_rules}"
    )
    rendered = upstream_yaml.replace(marker, insertion, 1)
    return (
        "# GENERATED FILE — do not edit directly. Edit custom-rules.yaml instead.\n"
        f"# Source: {source_url}\n"
        f"{rendered}"
    )


def render_conf(upstream_conf: str, source_url: str) -> str:
    required = ("[General]", "CONFIG_FILE", "SUB_INFO_URL", "ruby_map_edit")
    if any(token not in upstream_conf for token in required):
        raise ValueError("Upstream overwrite module no longer has the expected contract")
    replacement_url = (
        "https://cdn.jsdelivr.net/gh/sqzhang0814/Custom_OpenClash_Rules@"
        "refs/heads/main/cfg/yaml/Custom_Clash_Full.yaml"
    )
    rendered, replacements = re.subn(
        r"(DOWNLOAD_FILE\s*=\s*url=)[^,]+",
        rf"\g<1>{replacement_url}",
        upstream_conf,
        count=1,
    )
    if replacements != 1:
        raise ValueError("Could not replace the YAML download URL in upstream overwrite module")
    return (
        "# GENERATED FILE — source module is synchronized by GitHub Actions.\n"
        f"# Source: {source_url}\n"
        f"{rendered}"
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    temporary.replace(path)


def main() -> None:
    commit = json.loads(fetch_text(UPSTREAM_COMMIT_URL))["sha"]
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Upstream API returned an invalid commit SHA")
    yaml_url = raw_url(commit, "cfg/yaml/Custom_Clash_Full.yaml")
    conf_url = raw_url(commit, "overwrite/yaml/Custom_Clash_Full.conf")
    upstream_yaml = fetch_text(yaml_url)
    upstream_conf = fetch_text(conf_url)
    validate_upstream_yaml(upstream_yaml)
    personal_rules = read_custom_rules()
    write_text(OUTPUT_YAML, render_yaml(upstream_yaml, personal_rules, yaml_url))
    write_text(OUTPUT_CONF, render_conf(upstream_conf, conf_url))
    metadata = {
        "upstream_repository": UPSTREAM_REPOSITORY,
        "upstream_commit": commit,
        "yaml_sha256": hashlib.sha256(upstream_yaml.encode("utf-8")).hexdigest(),
        "overwrite_conf_sha256": hashlib.sha256(upstream_conf.encode("utf-8")).hexdigest(),
    }
    write_text(METADATA, json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    print(f"Generated from upstream commit {commit}")


if __name__ == "__main__":
    main()
