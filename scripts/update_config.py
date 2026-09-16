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
APPLE_OUTPUT_YAML = ROOT / "cfg/yaml/Custom_Clash_Full_Apple.yaml"
APPLE_OUTPUT_CONF = ROOT / "overwrite/yaml/Custom_Clash_Full_Apple.conf"
METADATA = ROOT / "upstream-source.json"
CUSTOM_RULES = ROOT / "custom-rules.yaml"
APPLE_YAML_FILENAME = "Custom_Clash_Full_Apple.yaml"

APPLE_PROVIDER_URLS = (
    (
        "Apple_Update",
        "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/apple-update.mrs",
    ),
    (
        "Apple_PKI",
        "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/apple-pki.mrs",
    ),
    (
        "Apple_iCloud_CN",
        "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/icloud%40cn.mrs",
    ),
    (
        "Apple_Dev_CN",
        "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/apple-dev%40cn.mrs",
    ),
)

APPLE_RULES = (
    ("Apple_Update", "🍎 苹果系统服务"),
    ("Apple_PKI", "🍎 苹果系统服务"),
    ("Apple_iCloud_CN", "🍎 苹果服务CN"),
    ("Apple_Dev_CN", "🍎 苹果服务CN"),
)

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
    header = rf'^  - name: "{re.escape(group_name)}"\n'
    matches = list(re.finditer(header, yaml_text, flags=re.MULTILINE))
    if len(matches) != 1:
        if not matches:
            raise ValueError(f"Upstream no longer contains proxy group: {group_name}")
        raise ValueError(f"Upstream contains duplicate proxy group: {group_name}")
    start = matches[0].start()
    following = re.search(
        r'^  - name: ', yaml_text[matches[0].end() :], flags=re.MULTILINE
    )
    end = matches[0].end() + following.start() if following else len(yaml_text)
    if end <= start:
        raise ValueError(f"Upstream no longer contains proxy group: {group_name}")
    return yaml_text[start:end]


def check_url(url: str) -> None:
    """Verify a remote rule-provider endpoint responds with content."""
    request = Request(url, headers={"User-Agent": "sqzhang0814-Custom-OpenClash-Rules"})
    with urlopen(request, timeout=30) as response:  # nosec B310: fixed HTTPS URLs above
        status = getattr(response, "status", response.getcode())
        if not 200 <= status < 400:
            raise ValueError(f"Apple provider URL returned HTTP {status}: {url}")
        if not response.read(1):
            raise ValueError(f"Apple provider URL returned an empty response: {url}")


def validate_apple_provider_urls() -> None:
    for _, url in APPLE_PROVIDER_URLS:
        check_url(url)


def validate_upstream_yaml(yaml_text: str) -> None:
    if len(re.findall(r"^rules:\s*$", yaml_text, flags=re.MULTILINE)) != 1:
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


def proxy_lines(group_text: str, group_name: str) -> list[str]:
    match = re.search(
        r"^    proxies:\n(?P<items>(?:      - [^\n]*\n)+)",
        group_text,
        flags=re.MULTILINE,
    )
    if not match:
        raise ValueError(f"Proxy group has no contiguous proxies list: {group_name}")
    return match.group("items").splitlines(keepends=True)


def inject_apple_groups(yaml_text: str) -> str:
    if len(re.findall(r'^  - name: "🍎 苹果服务CN"\s*$', yaml_text, flags=re.MULTILINE)):
        raise ValueError("Apple group already exists: 🍎 苹果服务CN")
    if len(re.findall(r'^  - name: "🍎 苹果系统服务"\s*$', yaml_text, flags=re.MULTILINE)):
        raise ValueError("Apple group already exists: 🍎 苹果系统服务")

    source_block = group_block(yaml_text, "🍎 苹果服务")
    direct_line = '      - "🎯 全球直连"\n'
    source_lines = proxy_lines(source_block, "🍎 苹果服务")
    source_without_direct = [line for line in source_lines if line != direct_line]
    required_candidates = ("🚀 手动选择", "♻️ 自动选择", *REGION_GROUPS)
    for candidate in required_candidates:
        expected_line = f'      - "{candidate}"\n'
        if source_without_direct.count(expected_line) != 1:
            raise ValueError(
                f"Upstream Apple service group must expose exactly one candidate: {candidate}"
            )

    source_header = '  - name: "🍎 苹果服务"\n'
    system_header = '  - name: "🍎 苹果系统服务"\n'
    if source_block.count(source_header) != 1:
        raise ValueError("Apple service group anchor is not unique")
    system_block = source_block.replace(source_header, system_header, 1)
    proxy_match = re.search(
        r"^    proxies:\n(?P<items>(?:      - [^\n]*\n)+)",
        system_block,
        flags=re.MULTILINE,
    )
    if not proxy_match:
        raise ValueError("Could not rebuild 🍎 苹果系统服务 proxies")
    rebuilt_lines = [direct_line, *source_without_direct]
    system_block = (
        system_block[: proxy_match.start("items")]
        + "".join(rebuilt_lines)
        + system_block[proxy_match.end("items") :]
    )

    apple_cn_block = (
        '  - name: "🍎 苹果服务CN"\n'
        "    type: select\n"
        "    proxies:\n"
        '      - "DIRECT"\n'
    )
    inserted = apple_cn_block + system_block + source_block
    if yaml_text.count(source_block) != 1:
        raise ValueError("Apple service group insertion anchor is not unique")
    return yaml_text.replace(source_block, inserted, 1)


def inject_apple_rule_providers(yaml_text: str) -> str:
    section_matches = list(
        re.finditer(r"^rule-providers:\s*$", yaml_text, flags=re.MULTILINE)
    )
    if len(section_matches) != 1:
        raise ValueError("Expected exactly one rule-providers section")
    for name, _ in APPLE_PROVIDER_URLS:
        if re.search(rf"^  {re.escape(name)}:\s*$", yaml_text, flags=re.MULTILINE):
            raise ValueError(f"Apple rule provider already exists: {name}")
        if f"RULE-SET,{name}," in yaml_text:
            raise ValueError(f"Apple rule provider rule reference already exists: {name}")

    provider_text = "".join(
        (
            f"  {name}:\n"
            "    type: http\n"
            "    behavior: domain\n"
            "    format: mrs\n"
            "    interval: 28800\n"
            f'    url: "{url}"\n'
        )
        for name, url in APPLE_PROVIDER_URLS
    )
    anchor = "rule-providers:\n"
    if yaml_text.count(anchor) != 1:
        raise ValueError("rule-providers insertion anchor is not unique")
    return yaml_text.replace(anchor, anchor + provider_text, 1)


def inject_apple_rules(yaml_text: str) -> str:
    tvplus_rule = '  - "GEOSITE,apple-tvplus,🎥 AppleTV+"\n'
    generic_rule = '  - "GEOSITE,apple,🍎 苹果服务"\n'
    if yaml_text.count(tvplus_rule) != 1:
        raise ValueError("Expected exactly one GEOSITE apple-tvplus rule")
    if yaml_text.count(generic_rule) != 1:
        raise ValueError("Expected exactly one generic GEOSITE apple rule")
    if yaml_text.index(generic_rule) <= yaml_text.index(tvplus_rule):
        raise ValueError("Generic GEOSITE apple rule must follow apple-tvplus")

    rule_text = "".join(
        f'  - "RULE-SET,{provider},{group}"\n' for provider, group in APPLE_RULES
    )
    for provider, _ in APPLE_RULES:
        line = f'  - "RULE-SET,{provider},'
        if line in yaml_text:
            raise ValueError(f"Apple rule insertion anchor already exists: {provider}")
    return yaml_text.replace(tvplus_rule, rule_text + tvplus_rule, 1)


def provider_block(yaml_text: str, provider_name: str) -> str:
    header = rf"^  {re.escape(provider_name)}:\n"
    matches = list(re.finditer(header, yaml_text, flags=re.MULTILINE))
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one rendered Apple provider: {provider_name}")
    following = re.search(
        r"^  \S[^\n]*:\s*$",
        yaml_text[matches[0].end() :],
        flags=re.MULTILINE,
    )
    end = matches[0].end() + following.start() if following else len(yaml_text)
    return yaml_text[matches[0].start() : end]


def validate_rendered_apple_yaml(yaml_text: str, personal_rules: list[str]) -> None:
    marker = "# Personal rules managed in custom-rules.yaml. Keep these above upstream rules.\n"
    if yaml_text.count(marker) != 1:
        raise ValueError("Personal rules marker must occur exactly once in Apple YAML")
    position = yaml_text.index(marker) + len(marker)
    for rule in personal_rules:
        line = f'  - "{rule}"\n'
        if yaml_text.count(line) != 1 or not yaml_text.startswith(line, position):
            raise ValueError(f"Personal rule is not unique and at the top: {rule}")
        position += len(line)

    for name, url in APPLE_PROVIDER_URLS:
        block = provider_block(yaml_text, name)
        expected_fields = (
            "    type: http\n",
            "    behavior: domain\n",
            "    format: mrs\n",
            "    interval: 28800\n",
            f'    url: "{url}"\n',
        )
        if any(field not in block for field in expected_fields):
            raise ValueError(f"Apple provider definition is incomplete: {name}")

    cn_block = group_block(yaml_text, "🍎 苹果服务CN")
    if "    type: select\n" not in cn_block or "    use:\n" in cn_block:
        raise ValueError("🍎 苹果服务CN must be a standalone select group")
    if proxy_lines(cn_block, "🍎 苹果服务CN") != ['      - "DIRECT"\n']:
        raise ValueError("🍎 苹果服务CN must contain only DIRECT")

    system_block = group_block(yaml_text, "🍎 苹果系统服务")
    if "    type: select\n" not in system_block:
        raise ValueError("🍎 苹果系统服务 must be a select group")
    if "    use:\n      - provider1\n" not in system_block:
        raise ValueError("🍎 苹果系统服务 must expose provider1 nodes")
    system_lines = proxy_lines(system_block, "🍎 苹果系统服务")
    if not system_lines or system_lines[0] != '      - "🎯 全球直连"\n':
        raise ValueError("🍎 苹果系统服务 must start with 🎯 全球直连")
    required_candidates = ("🚀 手动选择", "♻️ 自动选择", *REGION_GROUPS)
    for candidate in required_candidates:
        expected_line = f'      - "{candidate}"\n'
        if system_lines.count(expected_line) != 1:
            raise ValueError(f"🍎 苹果系统服务 is missing candidate: {candidate}")

    ordered_rules = [
        f'  - "RULE-SET,{provider},{group}"\n' for provider, group in APPLE_RULES
    ] + [
        '  - "GEOSITE,apple-tvplus,🎥 AppleTV+"\n',
        '  - "GEOSITE,apple,🍎 苹果服务"\n',
    ]
    positions = []
    for line in ordered_rules:
        if yaml_text.count(line) != 1:
            raise ValueError(f"Apple rule must occur exactly once: {line.strip()}")
        positions.append(yaml_text.index(line))
    if positions != sorted(positions):
        raise ValueError("Apple rules are not ordered before the generic Apple rule")


def render_apple_yaml(
    upstream_yaml: str, personal_rules: list[str], source_url: str
) -> str:
    rendered = render_yaml(upstream_yaml, personal_rules, source_url)
    rendered = inject_apple_groups(rendered)
    rendered = inject_apple_rule_providers(rendered)
    rendered = inject_apple_rules(rendered)
    validate_rendered_apple_yaml(rendered, personal_rules)
    return rendered


def render_conf(
    upstream_conf: str,
    source_url: str,
    yaml_filename: str = "Custom_Clash_Full.yaml",
) -> str:
    required = ("[General]", "CONFIG_FILE", "SUB_INFO_URL", "ruby_map_edit")
    if any(token not in upstream_conf for token in required):
        raise ValueError("Upstream overwrite module no longer has the expected contract")
    if "/" in yaml_filename or "\\" in yaml_filename:
        raise ValueError(f"Invalid generated YAML filename: {yaml_filename}")
    replacement_url = (
        "https://cdn.jsdelivr.net/gh/sqzhang0814/Custom_OpenClash_Rules@"
        f"refs/heads/main/cfg/yaml/{yaml_filename}"
    )
    rendered, replacements = re.subn(
        r"(DOWNLOAD_FILE\s*=\s*url=)[^,]+",
        rf"\g<1>{replacement_url}",
        upstream_conf,
        count=1,
    )
    if replacements != 1:
        raise ValueError("Could not replace the YAML download URL in upstream overwrite module")
    if yaml_filename != "Custom_Clash_Full.yaml":
        rendered = rendered.replace("Custom_Clash_Full.yaml", yaml_filename)
    return (
        "# GENERATED FILE — source module is synchronized by GitHub Actions.\n"
        f"# Source: {source_url}\n"
        f"{rendered}"
    )


def validate_rendered_apple_conf(conf_text: str) -> None:
    expected_url = (
        "https://cdn.jsdelivr.net/gh/sqzhang0814/Custom_OpenClash_Rules@"
        f"refs/heads/main/cfg/yaml/{APPLE_YAML_FILENAME}"
    )
    expected_path = f"/etc/openclash/config/{APPLE_YAML_FILENAME}"
    if conf_text.count(expected_url) != 1:
        raise ValueError("Apple overwrite module has an unexpected DOWNLOAD_FILE URL")
    if conf_text.count(expected_path) < 2:
        raise ValueError("Apple overwrite module must use the Apple YAML path")
    if "Custom_Clash_Full.yaml" in conf_text:
        raise ValueError("Apple overwrite module still references the original YAML filename")
    if f"CONFIG_FILE = {expected_path}" not in conf_text:
        raise ValueError("Apple overwrite module has an unexpected CONFIG_FILE")


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
    validate_apple_provider_urls()
    personal_rules = read_custom_rules()
    write_text(OUTPUT_YAML, render_yaml(upstream_yaml, personal_rules, yaml_url))
    write_text(OUTPUT_CONF, render_conf(upstream_conf, conf_url))
    write_text(
        APPLE_OUTPUT_YAML,
        render_apple_yaml(upstream_yaml, personal_rules, yaml_url),
    )
    apple_conf = render_conf(upstream_conf, conf_url, APPLE_YAML_FILENAME)
    validate_rendered_apple_conf(apple_conf)
    write_text(APPLE_OUTPUT_CONF, apple_conf)
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
