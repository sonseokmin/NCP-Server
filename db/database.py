import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# .env 로드
load_dotenv()

dbUser = os.getenv("DB_USER")
dbPassword = os.getenv("DB_PASSWORD")
dbHost = os.getenv("DB_HOST")
dbPort = os.getenv("DB_PORT")
dbName = os.getenv("DB_NAME")

# PostgreSQL 비동기 연결 URL
dbUrl = f"postgresql+asyncpg://{dbUser}:{dbPassword}@{dbHost}:{dbPort}/{dbName}"

# 엔진 생성
engine = create_async_engine(dbUrl, echo=False)

# 세션 생성기
sessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


# 모델용 베이스 클래스
class Base(DeclarativeBase):
    pass


# 의존성 주입을 위한 DB 세션 함수
async def getDb():
    async with sessionLocal() as session:
        yield session
