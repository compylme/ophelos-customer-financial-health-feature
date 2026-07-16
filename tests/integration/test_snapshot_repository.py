from datetime import date

def test_exists_for_period_returns_true_when_snapshot_exists(
    repository,
    persisted_user
):
    exists = repository.exists_for_period(
        user_id=persisted_user.id,
        period=date(2026, 7, 1)
    )

    assert exists is True