import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import update_config as config


class BusinessProviderTests(unittest.TestCase):
    group = '  - name: "Example"\n    type: select\n    proxies:\n      - "Region"\n'
    prefix = 'proxy-providers:\n  provider1:\n    type: http\nproxy-groups:\n'
    suffix = 'rules:\n  - "MATCH,Example"\n'

    def setUp(self):
        self.microsoft_group = patch.object(
            config,
            "MICROSOFT_CN_SOURCE_GROUP",
            "Example",
        )
        self.microsoft_cn_group = patch.object(
            config,
            "MICROSOFT_CN_GROUP",
            "Example CN",
        )
        self.microsoft_group.start()
        self.microsoft_cn_group.start()
        self.addCleanup(self.microsoft_group.stop)
        self.addCleanup(self.microsoft_cn_group.stop)
        self.gemini_template = patch.object(
            config,
            "GEMINI_TEMPLATE_GROUP",
            "Example",
        )
        self.gemini_template.start()
        self.addCleanup(self.gemini_template.stop)
        self.business = patch.object(config, "BUSINESS_SELECT_GROUPS", ("Example",))
        self.regions = patch.object(config, "REGION_GROUPS", ())
        self.business.start()
        self.regions.start()
        self.addCleanup(self.business.stop)
        self.addCleanup(self.regions.stop)

    def source(self, use=""):
        suffix = (
            'rules:\n'
            '  - "GEOSITE,onedrive,💾 OneDrive"\n'
            '  - "GEOSITE,bing,🤖 Copilot"\n'
            '  - "GEOSITE,category-ai-!cn,🤖 国外AI服务"\n'
            '  - "GEOSITE,microsoft,Example"\n'
            '  - "GEOSITE,google,🇬 谷歌服务"\n'
            '  - "MATCH,Example"\n'
            'rule-providers:\n'
            "  Existing:\n"
            "    type: http\n"
        )
        return self.prefix + self.group + use + suffix

    def test_missing_use_is_repaired_in_rendering_not_required_upstream(self):
        source = self.source()
        config.validate_upstream_yaml(source)
        with self.assertRaises(ValueError):
            config.validate_rendered_yaml(source)
        rendered = config.render_yaml(source, ["DOMAIN,example.org,DIRECT"], "fixture")
        block = config.group_block(rendered, "Example")
        self.assertEqual(block.replace("    use:\n      - provider1\n", ""), self.group)
        self.assertIn('rules:\n  # Personal rules', rendered)
        self.assertLess(rendered.index("DOMAIN,example.org,DIRECT"), rendered.index("MATCH,Example"))
        config.validate_rendered_yaml(rendered)
        self.assertEqual(config.ensure_business_provider_nodes(rendered), rendered)

    def test_append_preserves_other_provider_comments_and_order(self):
        use = '    use: # subscriptions\n      # keep this\n      - "other-provider" # original\n'
        source = self.source(use)
        rendered = config.ensure_business_provider_nodes(source)
        self.assertEqual(rendered, self.source(use + "      - provider1\n"))
        self.assertEqual(config.ensure_business_provider_nodes(rendered), rendered)
        config.validate_upstream_yaml(rendered)
        providers = config.business_use_list(
            config.group_block(rendered, "Example"), "Example"
        )[1]
        self.assertEqual(providers, ["other-provider", "provider1"])

    def test_existing_provider_is_unchanged_including_quotes(self):
        for item in ("provider1", '"provider1"', "'provider1'"):
            with self.subTest(item=item):
                source = self.source(f"    use:\n      - other\n      - {item} # existing\n")
                self.assertEqual(config.ensure_business_provider_nodes(source), source)
                config.validate_upstream_yaml(source)
                providers = config.business_use_list(
                    config.group_block(source, "Example"), "Example"
                )[1]
                self.assertEqual(providers, ["other", "provider1"])

    def test_ambiguous_or_unsupported_use_fails_closed(self):
        for use in (
            "    use: [other]\n",
            "    use:\n",
            "    use:\n      - provider1\n      - provider1\n",
            "    use:\n      - other\n    use:\n      - provider1\n",
            '    "use":\n      - other\n',
            "    use:\n      - {name: other}\n",
        ):
            with self.subTest(use=use), self.assertRaises(ValueError):
                config.ensure_business_provider_nodes(self.source(use))

    def test_nonselect_missing_and_duplicate_groups_are_rejected(self):
        for source in (
            self.source().replace("type: select", "type: fallback"),
            self.prefix + self.suffix,
            self.prefix + self.group * 2 + self.suffix,
        ):
            with self.subTest(source=source), self.assertRaises(ValueError):
                config.validate_upstream_yaml(source)

    def test_region_contract_is_still_strict(self):
        with patch.object(config, "REGION_GROUPS", ("Example",)):
            with self.assertRaises(ValueError):
                config.validate_upstream_yaml(self.source("    use:\n      - provider1\n"))

    def test_last_group_stops_at_next_section(self):
        suffix = self.suffix + "    use: [unrelated-rule-field]\n"
        source = self.prefix + self.group + suffix
        self.assertEqual(config.group_block(source, "Example"), self.group)
        rendered = config.ensure_business_provider_nodes(source)
        self.assertTrue(rendered.endswith(suffix))


class MicrosoftGeminiAndPersonalTests(unittest.TestCase):
    def setUp(self):
        business = patch.object(
            config,
            "BUSINESS_SELECT_GROUPS",
            ("Ⓜ️ 微软服务", "💾 OneDrive"),
        )
        regions = patch.object(config, "REGION_GROUPS", ())
        business.start()
        regions.start()
        self.addCleanup(business.stop)
        self.addCleanup(regions.stop)
        gemini_template = patch.object(
            config,
            "GEMINI_TEMPLATE_GROUP",
            "Ⓜ️ 微软服务",
        )
        gemini_template.start()
        self.addCleanup(gemini_template.stop)

    def source(self):
        candidates = (
            "🎯 全球直连",
            "🚀 手动选择",
            "♻️ 自动选择",
        )
        group_lines = lambda name: (
            f'  - name: "{name}"\n'
            "    type: select\n"
            "    proxies:\n"
            + "".join(f'      - "{candidate}"\n' for candidate in candidates)
        )
        return (
            "proxy-providers:\n"
            "  provider1:\n"
            "    type: http\n"
            "proxy-groups:\n"
            + group_lines("Ⓜ️ 微软服务")
            + group_lines("💾 OneDrive")
            + "\nrule-providers:\n"
            "  Existing:\n"
            "    type: http\n"
            "rules:\n"
            '  - "GEOSITE,onedrive,💾 OneDrive"\n'
            '  - "GEOSITE,bing,🤖 Copilot"\n'
            '  - "GEOSITE,category-ai-!cn,🤖 国外AI服务"\n'
            '  - "GEOSITE,microsoft,Ⓜ️ 微软服务"\n'
            '  - "GEOSITE,google,🇬 谷歌服务"\n'
            '  - "MATCH,🐟 漏网之鱼"\n'
        )

    def test_microsoft_cn_group_provider_and_rule_order(self):
        rendered = config.render_yaml(self.source(), [], "fixture")
        cn_block = config.group_block(rendered, "Ⓜ️ 微软服务CN")
        self.assertIn("    use:\n      - provider1\n", cn_block)
        self.assertEqual(
            config.proxy_lines(cn_block, "Ⓜ️ 微软服务CN"),
            [
                '      - "🎯 全球直连"\n',
                '      - "🚀 手动选择"\n',
                '      - "♻️ 自动选择"\n',
            ],
        )
        self.assertLess(rendered.index("GEOSITE,onedrive"), rendered.index("GEOSITE,bing"))
        self.assertLess(rendered.index("GEOSITE,bing"), rendered.index("RULE-SET,Microsoft_CN"))
        self.assertLess(
            rendered.index("RULE-SET,Microsoft_CN"),
            rendered.index("GEOSITE,microsoft,Ⓜ️ 微软服务"),
        )
        self.assertIn(config.MICROSOFT_CN_PROVIDER_URL, rendered)
        config.validate_rendered_yaml(rendered)

    def test_gemini_group_and_rule_precede_ai_and_google(self):
        rendered = config.render_yaml(self.source(), [], "fixture")
        gemini_block = config.group_block(rendered, "🤖 Gemini")
        self.assertIn("    type: select\n", gemini_block)
        self.assertIn("    use:\n      - provider1\n", gemini_block)
        self.assertLess(
            rendered.index('  - "GEOSITE,google-deepmind,🤖 Gemini"\n'),
            rendered.index('  - "GEOSITE,category-ai-!cn,🤖 国外AI服务"\n'),
        )
        self.assertLess(
            rendered.index('  - "GEOSITE,google-deepmind,🤖 Gemini"\n'),
            rendered.index('  - "GEOSITE,google,🇬 谷歌服务"\n'),
        )
        config.validate_rendered_yaml(rendered)

    def test_personal_conf_uses_personal_filename(self):
        upstream_conf = (
            "[General]\n"
            "DOWNLOAD_FILE = url=https://example.invalid/original.yaml, path=/etc/openclash/config/Custom_Clash_Full.yaml\n"
            "CONFIG_FILE = /etc/openclash/config/Custom_Clash_Full.yaml\n"
            "SUB_INFO_URL = $EN_KEY1\n"
            "[Overwrite]\n"
            "ruby_map_edit \"$CONFIG_FILE\" x y z \"$EN_KEY1\"\n"
        )
        rendered = config.render_conf(upstream_conf, "fixture", config.PERSONAL_YAML_FILENAME)
        config.validate_rendered_personal_conf(rendered)
        self.assertNotIn("Custom_Clash_Full_Apple", rendered)


if __name__ == "__main__":
    unittest.main()
