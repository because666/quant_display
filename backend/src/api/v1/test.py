from fastapi import APIRouter

router = APIRouter(tags=["test"])


@router.get("/test")
def api_test() -> dict[str, str]:
    return {"message": "Hello from backend"}
