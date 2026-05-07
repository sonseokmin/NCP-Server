# verify API 경로 파일

from fastapi import APIRouter
from controllers import systemControllers

systemRouter = APIRouter()

# GET /system/version/{appId}
systemRouter.add_api_route(
    "/version/{appId}", systemControllers.getAppVersion, methods=["GET"]
)
