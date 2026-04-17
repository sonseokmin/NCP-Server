import json
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional


async def createLicense(
    db: AsyncSession, licenseKey: str, maxDevices: int, expireDate: Optional[datetime]
):
    query = text(
        """
        INSERT INTO "subscriptions" ("licenseKey", "expireDate", "maxDevices", "hwIds", "createdAt", "updatedAt")
        VALUES (:licenseKey, :expireDate, :maxDevices, CAST(:hwIds AS JSONB), NOW(), NOW())
        """
    )

    await db.execute(
        query,
        {
            "licenseKey": licenseKey,
            "expireDate": expireDate,
            "maxDevices": maxDevices,
            "hwIds": json.dumps([]),  # 초기 기기는 0대이므로 빈 배열
        },
    )
    await db.commit()


# 전체 조회 수정
async def getAllLicenses(db: AsyncSession):
    # jsonb_array_length를 사용해 현재 등록된 HWID 개수 계산
    query = text(
        """
        SELECT *, jsonb_array_length("hwIds") as "currentDevices" 
        FROM "subscriptions" 
        ORDER BY "createdAt" DESC
        """
    )
    result = await db.execute(query)
    return result.mappings().all()


# 단일 조회 수정
async def getLicenseByKey(db: AsyncSession, licenseKey: str):
    query = text(
        """
        SELECT *, jsonb_array_length("hwIds") as "currentDevices" 
        FROM "subscriptions" 
        WHERE "licenseKey" = :licenseKey
        """
    )
    result = await db.execute(query, {"licenseKey": licenseKey})
    return result.mappings().first()


async def deleteLicense(db: AsyncSession, licenseKey: str):
    query = text('DELETE FROM "subscriptions" WHERE "licenseKey" = :licenseKey')
    result = await db.execute(query, {"licenseKey": licenseKey})
    await db.commit()
    return result.rowcount


async def updateExpireDate(db: AsyncSession, licenseKey: str, newExpireDate: datetime):
    query = text(
        'UPDATE "subscriptions" SET "expireDate" = :newExpireDate, "updatedAt" = NOW() WHERE "licenseKey" = :licenseKey'
    )
    result = await db.execute(
        query, {"licenseKey": licenseKey, "newExpireDate": newExpireDate}
    )
    await db.commit()
    return result.rowcount


async def resetHwIds(db: AsyncSession, licenseKey: str):
    # JSONB 타입을 빈 배열로 초기화
    query = text(
        'UPDATE "subscriptions" SET "hwIds" = \'[]\'::jsonb, "updatedAt" = NOW() WHERE "licenseKey" = :licenseKey'
    )
    result = await db.execute(query, {"licenseKey": licenseKey})
    await db.commit()
    return result.rowcount
