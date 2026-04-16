# verify API 경로 파일

from fastapi import APIRouter
from controllers import verifyControllers

verifyRouter = APIRouter()

# POST /verify
verifyRouter.add_api_route(
    "/verify", 
    verifyControllers.verifyLicense, 
    methods=["POST"]
)
