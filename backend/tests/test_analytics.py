import pytest
from backend.app.services.sip_tracker_service import SipTrackerService

def test_sip_calculator():
    res = SipTrackerService.calculate_sip(
        monthly_inv=10000,
        annual_rate=12.0,
        years=10
    )

    assert res["total_invested"] == 1200000.0
    assert res["total_value"] > 2000000.0
    assert res["estimated_returns"] > 800000.0
    assert len(res["breakdown_by_year"]) == 10

def test_lumpsum_calculator():
    res = SipTrackerService.calculate_lumpsum(
        principal=100000,
        annual_rate=12.0,
        years=5
    )

    assert res["total_invested"] == 100000.0
    assert res["total_value"] > 170000.0
