import uuid
from datetime import datetime, timedelta, timezone
from fastapi import Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from pydantic import BaseModel
from typing import Optional

from db.database import getDb
from models import adminModels


class ExtendLicensePayload(BaseModel):
    addDays: int


# 페이로드 (클라이언트가 보낼 데이터)
class CreateLicensePayload(BaseModel):
    maxDevices: int = 1
    durationDays: Optional[int] = None  # 값을 안 보내거나 null이면 무제한(Ultimate)


# 랜덤 라이선스 키 생성기 (예: KEY-A1B2C3-D4E5F6)
def generateRandomKey() -> str:
    part1 = uuid.uuid4().hex[:6].upper()
    part2 = uuid.uuid4().hex[:6].upper()
    return f"KEY-{part1}-{part2}"


def format_datetime(data):
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.strftime("%Y-%m-%d %H:%M:%S")
            # 🌟 만료일이 None(NULL)이면 "Ultimate"로 표시
            elif key == "expireDate" and value is None:
                data[key] = "Ultimate"
            elif isinstance(value, dict) or isinstance(value, list):
                format_datetime(value)
    elif isinstance(data, list):
        for item in data:
            format_datetime(item)
    return data


async def createNewLicense(
    payload: CreateLicensePayload, db: AsyncSession = Depends(getDb)
):
    try:
        newLicenseKey = generateRandomKey()

        # 만료일 계산
        expireDate = None
        if payload.durationDays is not None:
            expireDate = datetime.now(timezone.utc) + timedelta(
                days=payload.durationDays
            )

        # DB 저장 호출
        await adminModels.createLicense(
            db, newLicenseKey, payload.maxDevices, expireDate
        )

        logger.info(
            f"New License Generated - Key: {newLicenseKey}, Days: {payload.durationDays}, Devices: {payload.maxDevices}"
        )

        # 201 Created 응답
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": 201,
                "message": "라이선스가 성공적으로 발급되었습니다.",
                "data": {
                    "licenseKey": newLicenseKey,
                    "maxDevices": payload.maxDevices,
                    "expireDate": expireDate.strftime("%Y-%m-%d")
                    if expireDate
                    else "Ultimate",
                },
            },
        )

    except Exception as e:
        logger.error(f"License Creation Error: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": "Internal Server Error"},
        )


async def getLicense(licenseKey: str, db: AsyncSession = Depends(getDb)):
    try:
        row = await adminModels.getLicenseByKey(db, licenseKey)
        if not row:
            return JSONResponse(
                status_code=404,
                content={"status": 404, "detail": "라이선스를 찾을 수 없습니다."},
            )

        lic_dict = dict(row)
        now = datetime.now(timezone.utc)

        # 만료 여부 계산
        isExpired = False
        if lic_dict.get("expireDate"):
            exp = lic_dict["expireDate"]
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            isExpired = exp < now

        lic_dict["isExpired"] = isExpired

        safe_data = format_datetime(lic_dict)

        return JSONResponse(
            status_code=200,
            content={"status": 200, "detail": "조회 성공", "data": safe_data},
        )
    except Exception as e:
        logger.error(f"Get License Error: {e}")
        return JSONResponse(
            status_code=500, content={"status": 500, "detail": "Internal Server Error"}
        )


async def getAllLicenses(db: AsyncSession = Depends(getDb)):
    try:
        rows = await adminModels.getAllLicenses(db)
        now = datetime.now(timezone.utc)

        data = []
        for row in rows:
            lic_dict = dict(row)

            isExpired = False
            if lic_dict.get("expireDate"):
                exp = lic_dict["expireDate"]
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                isExpired = exp < now

            lic_dict["isExpired"] = isExpired
            data.append(format_datetime(lic_dict))

        return JSONResponse(
            status_code=200,
            content={"status": 200, "detail": "전체 조회 성공", "data": data},
        )
    except Exception as e:
        logger.error(f"Get All Licenses Error: {e}")
        return JSONResponse(
            status_code=500, content={"status": 500, "detail": "Internal Server Error"}
        )


async def deleteLicense(licenseKey: str, db: AsyncSession = Depends(getDb)):
    try:
        rowCount = await adminModels.deleteLicense(db, licenseKey)
        if rowCount == 0:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "detail": "삭제할 라이선스를 찾을 수 없습니다.",
                },
            )

        logger.info(f"License Deleted: {licenseKey}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "detail": "라이선스가 성공적으로 삭제되었습니다."},
        )
    except Exception as e:
        logger.error(f"Delete License Error: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "detail": "Internal Server Error"},
        )


async def extendLicense(
    licenseKey: str, payload: ExtendLicensePayload, db: AsyncSession = Depends(getDb)
):
    try:
        row = await adminModels.getLicenseByKey(db, licenseKey)
        if not row:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "detail": "연장할 라이선스를 찾을 수 없습니다.",
                },
            )

        currentExpireDate = row["expireDate"]

        # 무제한 라이선스인 경우 연장 불가 처리
        if currentExpireDate is None:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": 400,
                    "detail": "무제한(Ultimate) 라이선스는 연장할 수 없습니다.",
                },
            )

        now = datetime.now(timezone.utc)
        # 이미 만료되었다면 오늘 기준으로 연장, 아니면 남은 기간에 추가
        baseDate = now if currentExpireDate < now else currentExpireDate
        newExpireDate = baseDate + timedelta(days=payload.addDays)

        await adminModels.updateExpireDate(db, licenseKey, newExpireDate)
        logger.info(f"License Extended: {licenseKey} (+{payload.addDays} days)")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "detail": f"라이선스 기간이 {payload.addDays}일 연장되었습니다.",
                "data": {"newExpireDate": newExpireDate.strftime("%Y-%m-%d %H:%M:%S")},
            },
        )
    except Exception as e:
        logger.error(f"Extend License Error: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "detail": "Internal Server Error"},
        )


async def resetLicenseHw(licenseKey: str, db: AsyncSession = Depends(getDb)):
    try:
        rowCount = await adminModels.resetHwIds(db, licenseKey)

        if rowCount == 0:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "detail": "초기화할 라이선스를 찾을 수 없습니다.",
                },
            )

        logger.info(f"HWID Reset Success: {licenseKey}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "detail": "기기 등록 정보가 성공적으로 초기화되었습니다.",
            },
        )
    except Exception as e:
        logger.error(f"Reset HWID Error: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "detail": "Internal Server Error"},
        )
