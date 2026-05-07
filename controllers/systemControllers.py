from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import JSONResponse
from db.database import getDb
from models import systemModels


async def getAppVersion(appId: str, db: AsyncSession = Depends(getDb)):
    try:

        row = await systemModels.getAppVersion(db, appId)

        if not row:
            return JSONResponse(
                status_code=404,
                content={"status": 404, "detail": "등록되지 않은 프로그램입니다."},
            )

        return JSONResponse(
            status_code=200,
            content={"status": 200, "detail": "조회 성공", "data": dict(row)},
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": 500, "detail": str(e)})
