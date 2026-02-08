from src.api.main import PredictRequest


def test_request_validates():
    req = PredictRequest(
        tenure_months=10,
        monthly_charges=80,
        total_charges=800,
        tickets_90d=1,
        contract_type="month-to-month",
        payment_method="credit_card",
        internet_service="fiber",
        region="NE",
    )
    assert req.tenure_months == 10
