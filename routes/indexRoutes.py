# API Route 통합 파일

from fastapi import APIRouter

# 분리된 라우터들 임포트
from routes.verifyRoutes import verifyRouter
from routes.adminRoutes import adminRouter
from routes.systemRoutes import systemRouter

router = APIRouter()

# 1. 일반 유저 인증용 라우터 병합
router.include_router(verifyRouter, tags=["Verify"])

# 2. 관리자용 라우터 병합
router.include_router(adminRouter, prefix="/admin", tags=["Admin"])

# 3. 버전관리용 라우터 병합
router.include_router(systemRouter, prefix="/system", tags=["System"])
