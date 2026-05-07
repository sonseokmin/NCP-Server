from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


# 단일 조회 수정
async def getAppVersion(db: AsyncSession, appId: str):
    query = text(
        """SELECT "currentVersion" FROM "appVersions" WHERE "appId" = :appId"""
    )
    result = await db.execute(query, {"appId": appId})
    return result.mappings().first()
