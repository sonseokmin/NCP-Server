# admin API 경로 파일

import os
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from typing import Callable

from controllers import adminControllers


class CustomErrorRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_handler = super().get_route_handler()

        async def custom_handler(request: Request):
            try:
                # 정상일 때는 그대로 통과
                return await original_handler(request)
            except HTTPException as exc:
                # 문지기가 에러를 던지면 여기서 잽싸게 가로채서 네 입맛대로 JSON 조립!
                return JSONResponse(
                    status_code=exc.status_code,
                    content={
                        "status": exc.status_code,  # 네가 원하던 status 추가!
                        "detail": exc.detail,  # detail 그대로 유지
                    },
                )

        return custom_handler


async def verifyAdminToken(xAdminToken: str = Header(None)):
    secretKey = os.getenv("ADMIN_SECRET_KEY")

    # 서버에 비밀키 세팅이 누락된 경우
    if not secretKey:
        raise HTTPException(
            status_code=500, detail="Server Configuration Error: Secret key is missing"
        )

    if xAdminToken != secretKey or xAdminToken is None:
        raise HTTPException(status_code=403, detail="Access Denied: Invalid Token")


adminRouter = APIRouter(
    route_class=CustomErrorRoute, dependencies=[Depends(verifyAdminToken)]
)

# POST /admin/licenses
adminRouter.add_api_route(
    "/licenses", adminControllers.creaFteNewLicense, methods=["POST"]
)

adminRouter.add_api_route("/licenses", adminControllers.getAllLicenses, methods=["GET"])

# 단일 조회
adminRouter.add_api_route(
    "/licenses/{licenseKey}", adminControllers.getLicense, methods=["GET"]
)

# 삭제
adminRouter.add_api_route(
    "/licenses/{licenseKey}", adminControllers.deleteLicense, methods=["DELETE"]
)

# 기간 연장
adminRouter.add_api_route(
    "/licenses/{licenseKey}/extend",
    adminControllers.extendLicense,
    methods=["PATCH"],  # 일부 데이터(날짜)만 수정하므로 PATCH가 적합
)

# 기기 등록 정보 초기화 (POST 또는 PATCH 권장)
adminRouter.add_api_route(
    "/licenses/{licenseKey}/reset", adminControllers.resetLicenseHw, methods=["POST"]
)
