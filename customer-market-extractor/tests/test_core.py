from datetime import date
import tempfile
import unittest
from pathlib import Path

from customer_market_extractor.core import card_template, discover, load_config, parse_file, safe_relative, sanitize, validate_card
from customer_market_extractor.cli import require_config


class CoreTests(unittest.TestCase):
 def setUp(self):
    self._tmp = tempfile.TemporaryDirectory()
    self.tmp_path = Path(self._tmp.name)

 def tearDown(self):
    self._tmp.cleanup()

 def test_email_preserves_headers(self):
    tmp_path = self.tmp_path
    p = tmp_path / "one.eml"
    p.write_text("From: buyer@example.com\nTo: sales@example.com\nSubject: Drawing approval\nDate: Wed, 1 Oct 2026 10:00:00 +0800\n\nApproved drawing; PO not sent.", encoding="utf-8")
    r = parse_file(p)
    assert r.status == "成功" and "Subject: Drawing approval" in r.text and "PO not sent" in r.text


 def test_many_independent_emails_are_not_deduplicated(self):
    tmp_path = self.tmp_path
    results = []
    for i in range(40):
        p = tmp_path / f"m{i}.eml"
        p.write_text(f"From: b@example.com\nSubject: Update {i}\n\nMessage {i}", encoding="utf-8")
        results.append(parse_file(p))
    assert len({r.sha256 for r in results}) == 40


 def test_image_requires_ocr_authorization(self):
    tmp_path = self.tmp_path
    p = tmp_path / "chat.png"; p.write_bytes(b"not-a-real-image")
    r = parse_file(p)
    assert r.status == "部分成功" and "OCR" in r.reason


 def test_transcript_keeps_timestamps(self):
    tmp_path = self.tmp_path
    p = tmp_path / "meeting.vtt"; p.write_text("WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nBuyer: Need test report", encoding="utf-8")
    assert "00:00:01.000" in parse_file(p).text


 def test_same_topic_different_customers_not_merged_by_parser(self):
    tmp_path = self.tmp_path
    a = tmp_path / "a.txt"; b = tmp_path / "b.txt"
    a.write_text("Customer A: delay", encoding="utf-8"); b.write_text("Customer B: delay", encoding="utf-8")
    assert parse_file(a).sha256 != parse_file(b).sha256


 def test_card_does_not_invent_missing_result(self):
    tmp_path = self.tmp_path
    text = card_template("图纸批准", "PlantationShutters", ["a.eml"], "evt-1", date(2026, 10, 29))
    assert "原始资料未提供" in text and "成交" not in text


 def test_mkt_name_yaml_and_12_sections(self):
    tmp_path = self.tmp_path
    p = tmp_path / "MKT_图纸批准_PlantationShutters_20261029.md"
    p.write_text(card_template("图纸批准", "PlantationShutters", ["a.eml"], "evt-1", date(2026, 10, 29)), encoding="utf-8")
    assert validate_card(p) == []


 def test_windows_name_sanitization(self):
    assert sanitize('A:B/C*D?') == "A_B_C_D_"


 def test_path_escape_rejected(self):
    tmp_path = self.tmp_path
    with self.assertRaises(ValueError):
        safe_relative(tmp_path, "../outside")


 def test_audio_not_transcribed_without_consent(self):
    tmp_path = self.tmp_path
    p = tmp_path / "meeting.mp3"; p.write_bytes(b"audio")
    assert parse_file(p).status == "部分成功"


 def test_csv_has_row_preserving_text(self):
    tmp_path = self.tmp_path
    p = tmp_path / "chat.csv"; p.write_text("time,speaker,msg\n10:00,A,hello", encoding="utf-8")
    assert "10:00 | A | hello" in parse_file(p).text


 def test_unknown_type_fails_safely(self):
    tmp_path = self.tmp_path
    p = tmp_path / "x.bin"; p.write_bytes(b"x")
    assert parse_file(p).status == "失败"

 def test_unconfigured_paths_are_rejected(self):
    self.assertFalse(require_config({"source_root": None, "knowledge_root": None, "work_root": None}))

 def test_discover_ignores_os_metadata(self):
    (self.tmp_path / "message.txt").write_text("business", encoding="utf-8")
    (self.tmp_path / "._message.txt").write_bytes(b"metadata")
    (self.tmp_path / ".DS_Store").write_bytes(b"metadata")
    self.assertEqual([p.name for p in discover(self.tmp_path)], ["message.txt"])

 def test_missing_config_starts_unconfigured(self):
    cfg = load_config(self.tmp_path)
    self.assertIsNone(cfg["source_root"])
    self.assertIsNone(cfg["knowledge_root"])
    self.assertIsNone(cfg["work_root"])


if __name__ == "__main__":
    unittest.main()
