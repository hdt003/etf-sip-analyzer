from fastapi import APIRouter
from backend.app.schemas.analytics import SIPCalculatorRequest, GoalCalculatorRequest
from backend.app.services.sip_tracker_service import SipTrackerService

router = APIRouter(prefix="/calculators", tags=["Calculators"])

@router.post("/sip")
def calculate_sip(req: SIPCalculatorRequest):
    return SipTrackerService.calculate_sip(
        req.monthly_investment,
        req.expected_return_rate,
        req.time_period_years
    )

@router.post("/lumpsum")
def calculate_lumpsum(amount: float, rate: float, years: int):
    return SipTrackerService.calculate_lumpsum(amount, rate, years)

@router.post("/goal")
def calculate_goal(req: GoalCalculatorRequest):
    return SipTrackerService.calculate_goal(
        req.target_amount,
        req.expected_return_rate,
        req.time_period_years
    )
