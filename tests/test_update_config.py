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
        self.business = patch.object(config, "BUSINESS_SELECT_GROUPS", ("Example",))
        self.regions = patch.object(config, "REGION_GROUPS", ())
        self.business.start()
        self.regions.start()
        self.addCleanup(self.business.stop)
        self.addCleanup(self.regions.stop)

    def source(self, use=""):
        return self.prefix + self.group + use + self.suffix

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
        config.validate_rendered_yaml(rendered)

    def test_existing_provider_is_unchanged_including_quotes(self):
        for item in ("provider1", '"provider1"', "'provider1'"):
            with self.subTest(item=item):
                source = self.source(f"    use:\n      - other\n      - {item} # existing\n")
                self.assertEqual(config.ensure_business_provider_nodes(source), source)
                config.validate_rendered_yaml(source)

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
        source = self.source() + "    use: [unrelated-rule-field]\n"
        self.assertEqual(config.group_block(source, "Example"), self.group)
        rendered = config.ensure_business_provider_nodes(source)
        self.assertTrue(rendered.endswith(self.suffix + "    use: [unrelated-rule-field]\n"))


if __name__ == "__main__":
    unittest.main()
