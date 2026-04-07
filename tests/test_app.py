import io
import sys
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.modules.setdefault("boto3", SimpleNamespace(client=Mock()))
sys.modules.setdefault("requests", SimpleNamespace(get=Mock()))
sys.modules.setdefault("botocore.exceptions", SimpleNamespace(ClientError=Exception))

import app


class LoadConfigTests(unittest.TestCase):
    def test_load_config_parses_multi_record_configuration(self):
        config = app.load_config(
            {
                "HOSTED_ZONE_ID": "Z1234567890ABC",
                "RECORD_NAMES": "home.example.com, vpn.example.com ",
                "UPDATE_IPV4": "true",
                "UPDATE_IPV6": "true",
                "AWS_REGION": "us-east-1",
                "CHECK_INTERVAL": "600",
                "TTL": "120",
            }
        )

        self.assertIsNotNone(config)
        self.assertEqual(config.hosted_zone_id, "Z1234567890ABC")
        self.assertEqual(config.record_names, ["home.example.com", "vpn.example.com"])
        self.assertTrue(config.update_ipv4)
        self.assertTrue(config.update_ipv6)
        self.assertEqual(config.check_interval, 600)
        self.assertEqual(config.ttl, 120)

    def test_load_config_supports_legacy_record_name(self):
        config = app.load_config(
            {
                "HOSTED_ZONE_ID": "Z1234567890ABC",
                "RECORD_NAME": "home.example.com",
            }
        )

        self.assertIsNotNone(config)
        self.assertEqual(config.record_names, ["home.example.com"])

    def test_load_config_rejects_missing_records(self):
        output = io.StringIO()
        with redirect_stdout(output):
            config = app.load_config({"HOSTED_ZONE_ID": "Z1234567890ABC"})

        self.assertIsNone(config)
        self.assertIn("RECORD_NAMES (or RECORD_NAME) must be set", output.getvalue())

    def test_load_config_clamps_interval_and_ttl(self):
        output = io.StringIO()
        with redirect_stdout(output):
            config = app.load_config(
                {
                    "HOSTED_ZONE_ID": "Z1234567890ABC",
                    "RECORD_NAMES": "home.example.com",
                    "CHECK_INTERVAL": "10",
                    "TTL": "999999",
                }
            )

        self.assertIsNotNone(config)
        self.assertEqual(config.check_interval, 60)
        self.assertEqual(config.ttl, 86400)
        text = output.getvalue()
        self.assertIn("CHECK_INTERVAL too low", text)
        self.assertIn("TTL too high", text)


class PublicIpTests(unittest.TestCase):
    @patch("app.requests.get")
    def test_get_public_ip_returns_validated_ipv4(self, mock_get):
        mock_get.side_effect = [
            Mock(text="203.0.113.10\n", raise_for_status=Mock()),
            Mock(text="203.0.113.10\n", raise_for_status=Mock()),
        ]

        result = app.get_public_ip("ipv4")

        self.assertEqual(result, "203.0.113.10")

    @patch("app.requests.get")
    def test_get_public_ip_rejects_mismatched_sources(self, mock_get):
        mock_get.side_effect = [
            Mock(text="203.0.113.10\n", raise_for_status=Mock()),
            Mock(text="203.0.113.11\n", raise_for_status=Mock()),
        ]

        output = io.StringIO()
        with redirect_stdout(output):
            result = app.get_public_ip("ipv4")

        self.assertIsNone(result)
        self.assertIn("mismatch detected", output.getvalue())

    @patch("app.requests.get")
    def test_get_public_ip_requires_two_sources(self, mock_get):
        mock_get.side_effect = [
            Mock(text="203.0.113.10\n", raise_for_status=Mock()),
            RuntimeError("network issue"),
        ]

        output = io.StringIO()
        with redirect_stdout(output):
            result = app.get_public_ip("ipv4")

        self.assertIsNone(result)
        self.assertIn("enough sources", output.getvalue())


if __name__ == "__main__":
    unittest.main()
