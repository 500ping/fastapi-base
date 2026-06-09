from src.auth.dtos.responses.auth import UserResponse
from src.common.dtos.responses.success import Pagination, SuccessResponse


def test_generic_data_is_serialized() -> None:
    """A parametrized SuccessResponse keeps the nested ``data`` payload."""
    payload = SuccessResponse[dict](msg="ok", data={"a": 1})

    dumped = payload.model_dump()

    assert dumped["status_code"] == 200
    assert dumped["data"] == {"a": 1}


def test_typed_model_payload() -> None:
    user = {
        "id": 1,
        "email": "user@example.com",
        "is_active": True,
        "created_at": "2026-06-09T00:00:00Z",
    }
    payload = SuccessResponse[UserResponse](
        msg="ok", data=UserResponse.model_validate(user)
    )

    dumped = payload.model_dump()

    assert dumped["data"]["email"] == "user@example.com"
    assert dumped["data"]["id"] == 1


def test_exclude_none_drops_empty_fields() -> None:
    dumped = SuccessResponse(msg="ok").model_dump(exclude_none=True)

    assert dumped == {"status_code": 200, "msg": "ok"}


def test_pagination_included_when_set() -> None:
    payload = SuccessResponse[list](
        msg="ok", data=[1, 2], pagination=Pagination(page=1, size=2, total=5)
    )

    dumped = payload.model_dump(exclude_none=True)

    assert dumped["pagination"] == {"page": 1, "size": 2, "total": 5}
