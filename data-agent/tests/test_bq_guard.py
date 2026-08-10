"""Unit tests for BigQuery SQL guard (no live BQ required)."""

from __future__ import annotations

import pytest

from app.config import Settings
from app.tools.bq import BigQueryTools, BqGuardError


@pytest.fixture
def tools(monkeypatch: pytest.MonkeyPatch) -> BigQueryTools:
    settings = Settings(
        bq_project="oppo-gcp-prod-digfood-129869",
        bq_allowed_datasets="qpon_rpt_d,qpon_dws_d,qpon_dwd_d",
        gemini_api_key="dummy",
    )
    t = BigQueryTools.__new__(BigQueryTools)
    t.settings = settings
    t.client = None  # type: ignore[assignment]
    return t


def test_reject_dml(tools: BigQueryTools) -> None:
    with pytest.raises(BqGuardError):
        tools._assert_readonly("DELETE FROM qpon_rpt_d.t WHERE true")


def test_reject_disallowed_dataset(tools: BigQueryTools) -> None:
    sql = "SELECT 1 FROM `oppo-gcp-prod-digfood-129869.qpon_ods_d.ods_x` LIMIT 1"
    with pytest.raises(BqGuardError):
        tools._assert_datasets_allowed(sql)


def test_allow_rpt(tools: BigQueryTools) -> None:
    sql = (
        "SELECT partition_date, COUNT(1) c "
        "FROM `oppo-gcp-prod-digfood-129869.qpon_rpt_d.rpt_business_indicator_detail_d` "
        "WHERE partition_date = '2026-08-01' GROUP BY 1"
    )
    tools._assert_readonly(sql)
    tools._assert_datasets_allowed(sql)


def test_reject_backtick_two_part_ods(tools: BigQueryTools) -> None:
    with pytest.raises(BqGuardError):
        tools._assert_datasets_allowed("SELECT 1 FROM `qpon_ods_d.ods_x`")


def test_reject_cross_project(tools: BigQueryTools) -> None:
    with pytest.raises(BqGuardError):
        tools._assert_datasets_allowed("SELECT 1 FROM `evil-project.secret_ds.t`")


def test_reject_from_source_db(tools: BigQueryTools) -> None:
    with pytest.raises(BqGuardError):
        tools._assert_datasets_allowed("SELECT 1 FROM digital_food_order.some_table")


def test_parse_fqn_guard(tools: BigQueryTools) -> None:
    with pytest.raises(BqGuardError):
        tools._parse_and_guard_fqn("qpon_ods_d.some_table")
    p, d, t = tools._parse_and_guard_fqn("qpon_dwd_d.dwd_product_order_voucher_all")
    assert d == "qpon_dwd_d"
    assert t == "dwd_product_order_voucher_all"
    assert p == "oppo-gcp-prod-digfood-129869"
