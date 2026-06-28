"""Tests for muckaway-ai-mcp's new hire_skip() agent-callable tool.

The MCP-decorated function exposes the tool to MCP clients. Tests call
it directly (in-process) — same as the other 6 human tools.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from server import hire_skip  # the MCP-decorated function


def test_hire_skip_success():
    """Valid call returns ready_to_confirm with all expected fields."""
    r = hire_skip("SW1A 1AA", "soil", 4.0, "2026-07-15")
    assert r["status"] == "ready_to_confirm"
    assert "estimate" in r
    assert "pricing" in r
    assert "disposal_facility" in r
    assert "wtn" in r
    assert r["estimate"]["skip_size"] in ("mini", "midi", "builders", "large", "roll")
    assert r["pricing"]["currency"] == "GBP"
    assert r["wtn"]["wtn_id"].startswith("WTN-")


def test_hire_skip_rejects_invalid_postcode():
    r = hire_skip("NOTREAL", "soil", 4.0, "2026-07-15")
    assert r["status"] == "rejected"
    assert r["reason"] == "invalid_postcode"


def test_hire_skip_rejects_zero_volume():
    r = hire_skip("SW1A 1AA", "soil", 0, "2026-07-15")
    assert r["status"] == "rejected"
    assert r["reason"] == "invalid_volume"


def test_hire_skip_rejects_bad_date():
    r = hire_skip("SW1A 1AA", "soil", 4.0, "07/15/2026")
    assert r["status"] == "rejected"
    assert r["reason"] == "invalid_date"


def test_hire_skip_picks_correct_size():
    """Volume → skip size mapping."""
    r1 = hire_skip("M1 1AA", "soil", 1.0, "2026-07-15")
    r2 = hire_skip("M1 1AA", "soil", 3.0, "2026-07-15")
    r3 = hire_skip("M1 1AA", "soil", 5.0, "2026-07-15")
    r4 = hire_skip("M1 1AA", "soil", 7.0, "2026-07-15")
    r5 = hire_skip("M1 1AA", "soil", 15.0, "2026-07-15")
    assert r1["estimate"]["skip_size"] == "mini"
    assert r2["estimate"]["skip_size"] == "midi"
    assert r3["estimate"]["skip_size"] == "builders"
    assert r4["estimate"]["skip_size"] == "large"
    assert r5["estimate"]["skip_size"] == "roll"


def test_hire_skip_london_postcode_triggers_permit():
    """SW/WC/EC postcodes should add a permit fee."""
    r = hire_skip("SW1A 1AA", "soil", 4.0, "2026-07-15")
    assert r["pricing"]["permit_gbp"] == 50
    r2 = hire_skip("M1 1AA", "soil", 4.0, "2026-07-15")
    assert r2["pricing"]["permit_gbp"] == 0


def test_hire_skip_agent_metadata_x402():
    """Each call returns x402_price_usd for pay-per-call monetization."""
    r = hire_skip("M1 1AA", "soil", 4.0, "2026-07-15")
    assert r["agent_metadata"]["x402_price_usd"] == 0.05
    assert r["agent_metadata"]["for_agent"] == "other_llm_can_call"


def test_hire_skip_vat_calc():
    """VAT = 20% of subtotal. Midi skip: 220 haulage + 110 disposal = 330; + 20% = 396 total."""
    r = hire_skip("M1 1AA", "soil", 4.0, "2026-07-15")  # no permit
    assert r["pricing"]["subtotal_gbp"] == 330
    assert r["pricing"]["vat_gbp"] == 66.0
    assert r["pricing"]["total_gbp"] == 396.0


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))