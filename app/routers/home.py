from fastapi import APIRouter, Response, status

from app.startup import home_service

router = APIRouter(tags=["home"])


@router.get("/health")
async def healthcheck(response: Response) -> dict:
    result = await home_service.healthcheck()
    if result["status"] != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result
