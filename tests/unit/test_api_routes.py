from __future__ import annotations

from collections.abc import Callable
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.exceptions import SnapshotAlreadyExists, SnapshotNotFound
from app.models.models import Direction, MonthlySnapshot
from app.schemas.financial_health import SnapshotResponse


# ---------------------------------------------------------------------------
# POST /snapshots
# ---------------------------------------------------------------------------


class TestSubmitSnapshot:
    def test_valid_request_returns_201(
        self,
        client: TestClient,
        mock_service: MagicMock,
        sample_snapshot: MonthlySnapshot,
        valid_submit_payload_factory: Callable[..., dict],
    ) -> None:
        mock_service.submit_snapshot.return_value = sample_snapshot

        response = client.post("/snapshots", json=valid_submit_payload_factory())

        assert response.status_code == 201
        SnapshotResponse.model_validate(response.json())

    def test_response_contains_all_expected_fields(
        self,
        client: TestClient,
        mock_service: MagicMock,
        sample_snapshot: MonthlySnapshot,
        valid_submit_payload_factory: Callable[..., dict],
    ) -> None:
        mock_service.submit_snapshot.return_value = sample_snapshot

        response = client.post("/snapshots", json=valid_submit_payload_factory())
        body = SnapshotResponse.model_validate(response.json())

        assert body.id == sample_snapshot.id
        assert body.user_id == sample_snapshot.user_id
        assert body.period == sample_snapshot.period
        assert body.submitted_at == sample_snapshot.submitted_at
        assert len(body.financial_items) == 2
        assert body.assessment is not None
        assert body.assessment.status.value == "HEALTHY"
        assert body.assessment.total_income == Decimal("2500.00")
        assert body.assessment.total_expenditure == Decimal("1500.00")
        assert body.assessment.disposable_income == Decimal("1000.00")

    def test_snapshot_already_exists_maps_to_409(
        self,
        client: TestClient,
        mock_service: MagicMock,
        valid_submit_payload_factory: Callable[..., dict],
    ) -> None:
        mock_service.submit_snapshot.side_effect = SnapshotAlreadyExists(
            "A snapshot already exists for this period"
        )

        response = client.post("/snapshots", json=valid_submit_payload_factory())

        assert response.status_code == 409
        assert response.json() == {
            "detail": "A snapshot already exists for this period"
        }

    def test_missing_user_id_returns_422(
        self,
        client: TestClient,
        mock_service: MagicMock,
        valid_submit_payload_factory: Callable[..., dict],
    ) -> None:
        payload = valid_submit_payload_factory()
        del payload["user_id"]

        response = client.post("/snapshots", json=payload)

        assert response.status_code == 422
        mock_service.submit_snapshot.assert_not_called()

    def test_missing_items_returns_422(
        self,
        client: TestClient,
        mock_service: MagicMock,
        valid_submit_payload_factory: Callable[..., dict],
    ) -> None:
        payload = valid_submit_payload_factory()
        del payload["items"]

        response = client.post("/snapshots", json=payload)

        assert response.status_code == 422
        mock_service.submit_snapshot.assert_not_called()

    def test_empty_items_list_returns_422(
        self,
        client: TestClient,
        mock_service: MagicMock,
        valid_submit_payload_factory: Callable[..., dict],
    ) -> None:
        payload = valid_submit_payload_factory()
        payload["items"] = []

        response = client.post("/snapshots", json=payload)

        assert response.status_code == 422
        mock_service.submit_snapshot.assert_not_called()

    def test_item_with_non_positive_amount_returns_422(
        self,
        client: TestClient,
        mock_service: MagicMock,
        valid_submit_payload_factory: Callable[..., dict],
    ) -> None:
        payload = valid_submit_payload_factory()
        payload["items"][0]["amount"] = "0"

        response = client.post("/snapshots", json=payload)

        assert response.status_code == 422
        mock_service.submit_snapshot.assert_not_called()

    def test_item_with_empty_description_returns_422(
        self,
        client: TestClient,
        mock_service: MagicMock,
        valid_submit_payload_factory: Callable[..., dict],
    ) -> None:
        payload = valid_submit_payload_factory()
        payload["items"][0]["description"] = ""

        response = client.post("/snapshots", json=payload)

        assert response.status_code == 422
        mock_service.submit_snapshot.assert_not_called()

    def test_invalid_user_id_returns_422(
        self,
        client: TestClient,
        mock_service: MagicMock,
        valid_submit_payload_factory: Callable[..., dict],
    ) -> None:
        payload = valid_submit_payload_factory()
        payload["user_id"] = "not-a-uuid"

        response = client.post("/snapshots", json=payload)

        assert response.status_code == 422
        mock_service.submit_snapshot.assert_not_called()


# ---------------------------------------------------------------------------
# GET /snapshots/{user_id}/history
# ---------------------------------------------------------------------------


class TestGetHistory:
    def test_returns_200_with_list_of_snapshots(
        self,
        client: TestClient,
        mock_service: MagicMock,
        sample_snapshot: MonthlySnapshot,
        in_memory_snapshot_factory: Callable[..., MonthlySnapshot],
    ) -> None:
        snapshots = [
            in_memory_snapshot_factory(
                snapshot_id=uuid4(),
                period=date(2026, 7, 1),
            ),
            in_memory_snapshot_factory(
                snapshot_id=uuid4(),
                period=date(2026, 6, 1),
            ),
        ]
        mock_service.get_history.return_value = snapshots

        response = client.get(f"/snapshots/{sample_snapshot.user_id}/history")

        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)
        assert len(body) == 2
        for item in body:
            SnapshotResponse.model_validate(item)

    def test_empty_history_returns_200_with_empty_list(
        self,
        client: TestClient,
        mock_service: MagicMock,
        sample_snapshot: MonthlySnapshot,
    ) -> None:
        mock_service.get_history.return_value = []

        response = client.get(f"/snapshots/{sample_snapshot.user_id}/history")

        assert response.status_code == 200
        assert response.json() == []

    def test_default_limit_passed_to_service(
        self,
        client: TestClient,
        mock_service: MagicMock,
        sample_snapshot: MonthlySnapshot,
    ) -> None:
        mock_service.get_history.return_value = []

        client.get(f"/snapshots/{sample_snapshot.user_id}/history")

        mock_service.get_history.assert_called_once_with(
            user_id=sample_snapshot.user_id, limit=12
        )

    def test_explicit_limit_passed_to_service(
        self,
        client: TestClient,
        mock_service: MagicMock,
        sample_snapshot: MonthlySnapshot,
    ) -> None:
        mock_service.get_history.return_value = []

        client.get(
            f"/snapshots/{sample_snapshot.user_id}/history",
            params={"limit": 5},
        )

        mock_service.get_history.assert_called_once_with(
            user_id=sample_snapshot.user_id, limit=5
        )

    def test_response_contains_only_returned_snapshots(
        self,
        client: TestClient,
        mock_service: MagicMock,
        sample_snapshot: MonthlySnapshot,
        in_memory_snapshot_factory: Callable[..., MonthlySnapshot],
    ) -> None:
        first_id = UUID("11111111-1111-1111-1111-111111111111")
        second_id = UUID("22222222-2222-2222-2222-222222222222")
        snapshots = [
            in_memory_snapshot_factory(
                snapshot_id=first_id, period=date(2026, 7, 1)
            ),
            in_memory_snapshot_factory(
                snapshot_id=second_id, period=date(2026, 6, 1)
            ),
        ]
        mock_service.get_history.return_value = snapshots

        response = client.get(
            f"/snapshots/{sample_snapshot.user_id}/history",
            params={"limit": 2},
        )
        body = [SnapshotResponse.model_validate(item) for item in response.json()]

        assert len(body) == 2
        assert body[0].id == first_id
        assert body[0].period == date(2026, 7, 1)
        assert body[1].id == second_id
        assert body[1].period == date(2026, 6, 1)

    def test_invalid_user_id_returns_422(
        self,
        client: TestClient,
        mock_service: MagicMock,
    ) -> None:
        response = client.get("/snapshots/not-a-uuid/history")

        assert response.status_code == 422
        mock_service.get_history.assert_not_called()


# ---------------------------------------------------------------------------
# GET /snapshots/{user_id}/{period}
# ---------------------------------------------------------------------------


class TestGetSnapshot:
    def test_existing_snapshot_returns_200(
        self,
        client: TestClient,
        mock_service: MagicMock,
        sample_snapshot: MonthlySnapshot,
    ) -> None:
        mock_service.get_snapshot.return_value = sample_snapshot

        response = client.get(
            f"/snapshots/{sample_snapshot.user_id}/{sample_snapshot.period.isoformat()}"
        )

        assert response.status_code == 200
        SnapshotResponse.model_validate(response.json())

    def test_response_contains_financial_items_and_assessment(
        self,
        client: TestClient,
        mock_service: MagicMock,
        sample_snapshot: MonthlySnapshot,
    ) -> None:
        mock_service.get_snapshot.return_value = sample_snapshot

        response = client.get(
            f"/snapshots/{sample_snapshot.user_id}/{sample_snapshot.period.isoformat()}"
        )
        body = SnapshotResponse.model_validate(response.json())

        assert len(body.financial_items) == 2
        assert body.financial_items[0].id == sample_snapshot.financial_items[0].id
        assert body.financial_items[0].direction == Direction.INCOME
        assert body.financial_items[0].description == "Salary"
        assert body.financial_items[0].amount == Decimal("2500.00")
        assert body.financial_items[1].id == sample_snapshot.financial_items[1].id
        assert body.financial_items[1].direction == Direction.EXPENSE
        assert body.assessment.total_income == Decimal("2500.00")
        assert body.assessment.total_expenditure == Decimal("1500.00")
        assert body.assessment.disposable_income == Decimal("1000.00")
        assert body.assessment.status.value == "HEALTHY"
        assert body.assessment.explanation == "Test explanation"

    def test_snapshot_not_found_maps_to_404(
        self,
        client: TestClient,
        mock_service: MagicMock,
        sample_snapshot: MonthlySnapshot,
    ) -> None:
        mock_service.get_snapshot.side_effect = SnapshotNotFound(
            "No snapshot found for this period"
        )

        response = client.get(
            f"/snapshots/{sample_snapshot.user_id}/{sample_snapshot.period.isoformat()}"
        )

        assert response.status_code == 404
        assert response.json() == {"detail": "No snapshot found for this period"}

    def test_invalid_user_id_returns_422(
        self,
        client: TestClient,
        mock_service: MagicMock,
        sample_snapshot: MonthlySnapshot,
    ) -> None:
        response = client.get(
            f"/snapshots/not-a-uuid/{sample_snapshot.period.isoformat()}"
        )

        assert response.status_code == 422
        mock_service.get_snapshot.assert_not_called()

    def test_invalid_period_format_returns_422(
        self,
        client: TestClient,
        mock_service: MagicMock,
        sample_snapshot: MonthlySnapshot,
    ) -> None:
        response = client.get(f"/snapshots/{sample_snapshot.user_id}/not-a-date")

        assert response.status_code == 422
        mock_service.get_snapshot.assert_not_called()
