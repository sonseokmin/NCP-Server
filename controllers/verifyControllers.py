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

    if not licenseKey:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status": 400,
                "detail": "Invalid Data"
            }
        )
    
    try:
        # 1. 라이선스 정보 조회
        requests = await verifyModels.verifyLicense(db, licenseKey)

        if not requests:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                content={"status": 401, "detail": "Unauthorized"}
            )
        
        if requests["expireDate"] and requests["expireDate"] < datetime.now(timezone.utc):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"status": 403, "detail": "Expired License"}
            )
        
        # 2. HWID 등록 및 검증 로직
        currentHwIds = list(requests["hwIds"]) # JSONB 리스트 가져오기
        isNewDevice = False # 🌟 새 기기 등록 여부를 추적하는 플래그

        if hwId not in currentHwIds:
            # 허용 대수 초과 여부 확인
            if len(currentHwIds) >= requests["maxDevices"]:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"status": 403, "detail": "Device Limit Exceeded"}
                )
            
            # 새 HWID 추가 및 DB 업데이트
            currentHwIds.append(hwId)
            await verifyModels.updateHwIds(db, licenseKey, currentHwIds)
            logger.info(f"New HWID registered: {hwId} for key: {licenseKey}")

            isNewDevice = True


        expireDate = requests["expireDate"]

        if expireDate is None:
            displayDate = "Ultimate"
        else:
            displayDate = expireDate.strftime("%Y-%m-%d")
            
        remainingDevices = requests["maxDevices"] - len(currentHwIds)


        return {
            "status": 200,
            "detail": "New HW Register" if isNewDevice else "Success",
            "remainingDevices": remainingDevices,
            "expireDate" : displayDate
        }

    except Exception as e:
        logger.error(f"Verification Error: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "detail": "Internal Server Error"}
        )