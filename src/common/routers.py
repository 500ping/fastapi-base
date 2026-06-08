from fastapi import APIRouter

from src.common.dtos.responses.success import SuccessResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=SuccessResponse,
    response_model_exclude_none=True,
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status_code": 200,
                        "msg": "Service is healthy",
                    }
                }
            },
        }
    },
)
async def health_check() -> SuccessResponse:
    return SuccessResponse(msg="Service is healthy")
