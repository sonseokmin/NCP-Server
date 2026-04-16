# 실제 기능 프로세스를 담당하는 파일

from datetime import datetime, timezone

from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from fastapi import Depends , status
from loguru import logger
from typing import Optional

from db.database import getDb
from models import verifyModels

class VerifyPayload(BaseModel):
    licenseKey: Optional[str] = None
    hwId: Optional[str] = None

async def verifyLicense(payload: VerifyPayload, db: AsyncSession = Depends(getDb)):
    licenseKey = payload.licenseKey
    hwId = payload.hwId

    # 1. 라이선스 키 미입력 (400)
    if not licenseKey:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": 400, "detail": "Invalid Data"}
        )
    
    try:
        # DB에서 라이선스 정보 조회
        requests = await verifyModels.verifyLicense(db, licenseKey)

        # 2. 존재하지 않는 키 (401)
        if not requests:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                content={"status": 401, "detail": "Unauthorized"}
            )
        
        # 공통으로 사용할 정보 미리 정리
        expireDateRaw = requests["expireDate"]
        displayDate = expireDateRaw.strftime("%Y-%m-%d") if expireDateRaw else "Ultimate"
        maxDevices = requests["maxDevices"]
        currentHwIds = list(requests["hwIds"])

        # 3. 라이선스 기간 만료 (403)
        if expireDateRaw and expireDateRaw < datetime.now(timezone.utc):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "status": 403, 
                    "detail": "Expired License",
                    "expireDate": displayDate, # ◀ 추가
                    "remainingDevices": 0      # ◀ 추가
                }
            )
        
        # 4. HWID 등록 및 검증
        isNewDevice = False
        if hwId not in currentHwIds:
            # 허용 대수 초과 확인
            if len(currentHwIds) >= maxDevices:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "status": 403, 
                        "detail": "Device Limit Exceeded",
                        "expireDate": displayDate, # ◀ 추가: 대수 초과라도 만료일은 보여줌
                        "remainingDevices": 0      # ◀ 추가
                    }
                )
            
            # 새 기기 등록
            currentHwIds.append(hwId)
            await verifyModels.updateHwIds(db, licenseKey, currentHwIds)
            isNewDevice = True

        # 5. 최종 성공 (200)
        return {
            "status": 200,
            "detail": "New HW Register" if isNewDevice else "Success",
            "remainingDevices": maxDevices - len(currentHwIds),
            "expireDate" : displayDate
        }

    except Exception as e:
        logger.error(f"Verification Error: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "detail": "Internal Server Error"}
        )