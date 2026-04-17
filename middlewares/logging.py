import sys
import time
import json
from fastapi import Request
from loguru import logger

# 로그 포맷 설정
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> <white>|</white> {message}",
    colorize=True,
)


async def log(request: Request, call_next):
    startTime = time.time()

    # 1. 요청 Body 읽기 (무한 로딩 방지를 위한 복구 작업 포함)
    bodyBytes = await request.body()

    async def customReceive():
        return {"type": "http.request", "body": bodyBytes}

    request._receive = customReceive  # 읽은 Body를 다시 Request 객체에 채워 넣음

    # 2. Body를 JSON으로 파싱 (실패 시 일반 텍스트로 처리)
    payload = {}
    if bodyBytes:
        try:
            payload = json.loads(bodyBytes)
        except json.JSONDecodeError:
            payload = bodyBytes.decode("utf-8")

    # 3. 다음 라우터로 넘기기
    response = await call_next(request)

    processTime = (time.time() - startTime) * 1000

    method = request.method
    path = request.url.path
    statusCode = response.status_code
    queryParams = dict(request.query_params)

    # 4. 로깅할 데이터 결정 (Body가 있으면 Body 출력, 없으면 쿼리 파라미터 출력)
    requestData = payload if payload else queryParams

    # 5. 색상 및 공백 규칙 적용
    logger.opt(colors=True).info(
        f"<green>{statusCode}</green> <white>|</white> "
        f"<cyan>{method} {path}</cyan> <white>|</white> "
        f"<yellow>{processTime:.2f}ms</yellow> <white>|</white> "
        f"<magenta>{requestData}</magenta>"
    )

    return response
