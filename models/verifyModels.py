import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

async def verifyLicense(db: AsyncSession, licenseKey: str):

    sql = text(
        """
        SELECT "id", "licenseKey", "expireDate", "maxDevices", "hwIds"
        FROM "subscriptions"
        WHERE "licenseKey" = :licenseKey
        """
    )

    result = await db.execute(sql, {"licenseKey": licenseKey})
    # 딕셔너리 형태로 반환받기 위해 mappings() 사용
    return result.mappings().first()

async def updateHwIds(db: AsyncSession, licenseKey: str, newHwIds: list):
    query = text(
        """
        UPDATE "subscriptions"
        SET "hwIds" = :newHwIds, "updatedAt" = NOW()
        WHERE "licenseKey" = :licenseKey
        """
    )

    await db.execute(query, {
        "licenseKey": licenseKey,
        "newHwIds": json.dumps(newHwIds)
    })

    await db.commit()