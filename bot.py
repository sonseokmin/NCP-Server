import os
import discord  # 🌟 여기는 무조건 discord여야 해!
from discord import app_commands
import aiohttp
from dotenv import load_dotenv

load_dotenv()


# 봇 기본 설정
class AdminClient(discord.Client):  
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()


client = AdminClient()


#  /라이선스발급
@client.tree.command(
    name="라이선스발급", description="서버에 요청하여 새로운 라이선스를 생성합니다."
)
async def generateLicense(
    interaction: discord.Interaction, duration_days: int = 0, max_devices: int = 1
):
    await interaction.response.defer()

    apiUrl = "http://localhost:8000/admin/licenses"  # FastAPI 서버 주소

    # 0을 입력하면 무제한(None)으로 처리하도록 분기
    durationDays = None if duration_days == 0 else duration_days

    # 아까 우리가 만든 CreateLicensePayload 구조에 맞춤
    payload = {"maxDevices": max_devices, "durationDays": durationDays}

    # FastAPI 서버로 API 요청 쏘기
    async with aiohttp.ClientSession() as session:
        secretKey = os.getenv("ADMIN_SECRET_KEY")

        # 봇에 비밀키 세팅이 누락된 경우
        if not secretKey:
            await interaction.followup.send(
                "❌ 에러: 봇 환경변수(ADMIN_SECRET_KEY)가 설정되지 않았습니다."
            )
            return

        headers = {"xAdminToken": secretKey}

        async with session.post(apiUrl, json=payload, headers=headers) as response:
            if response.status == 201:
                data = await response.json()

                # FastAPI가 리턴해준 데이터 빼오기
                licenseKey = data["data"]["licenseKey"]
                expireDate = data["data"]["expireDate"]

                # 디스코드에 예쁘게 띄워줄 UI(Embed) 생성
                embed = discord.Embed(title="✅ 라이선스 발급 완료", color=0x00FF00)
                embed.add_field(
                    name="🔑 라이선스 키", value=f"`{licenseKey}`", inline=False
                )
                embed.add_field(
                    name="💻 허용 대수", value=f"{max_devices}대", inline=True
                )
                embed.add_field(name="📅 만료일", value=f"{expireDate}", inline=True)

                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(
                    "❌ 서버 에러: 라이선스 발급 API 호출에 실패했습니다."
                )


# /라이선스조회 (단일 조회) 수정
@client.tree.command(
    name="라이선스조회", description="특정 라이선스 키의 상세 정보를 조회합니다."
)
async def getLicense(interaction: discord.Interaction, license_key: str):
    await interaction.response.defer()
    apiUrl = f"http://localhost:8000/admin/licenses/{license_key}"
    secretKey = os.getenv("ADMIN_SECRET_KEY")

    async with aiohttp.ClientSession() as session:
        async with session.get(apiUrl, headers={"xAdminToken": secretKey}) as response:
            data = await response.json()
            if response.status == 200:
                lic = data["data"]
                status_text = "❌ 만료됨" if lic["isExpired"] else "✅ 활성"
                color = 0xE74C3C if lic["isExpired"] else 0x2ECC71

                embed = discord.Embed(
                    title=f"🔍 라이선스 상세 ({status_text})", color=color
                )
                embed.add_field(
                    name="🔑 라이선스 키", value=f"`{lic['licenseKey']}`", inline=False
                )
                # 등록 대수 출력 부분
                embed.add_field(
                    name="💻 기기 등록 현황",
                    value=f"**{lic['currentDevices']}** / {lic['maxDevices']} 대",
                    inline=True,
                )
                embed.add_field(
                    name="📅 만료일", value=f"`{lic['expireDate']}`", inline=True
                )
                embed.add_field(
                    name="🕒 생성일", value=f"{lic['createdAt']}", inline=False
                )
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(
                    f"❌ 에러: {data.get('detail', '오류 발생')}"
                )


# /라이선스전체조회 수정
@client.tree.command(
    name="라이선스전체조회", description="발급된 모든 라이선스 목록을 확인합니다."
)
async def getAllLicenses(interaction: discord.Interaction):
    await interaction.response.defer()
    apiUrl = "http://localhost:8000/admin/licenses"
    secretKey = os.getenv("ADMIN_SECRET_KEY")

    async with aiohttp.ClientSession() as session:
        async with session.get(apiUrl, headers={"xAdminToken": secretKey}) as response:
            data = await response.json()
            if response.status == 200:
                licenses = data["data"]
                if not licenses:
                    await interaction.followup.send("발급된 라이선스가 없습니다.")
                    return

                embed = discord.Embed(
                    title=f"📋 전체 라이선스 현황 (총 {len(licenses)}개)",
                    color=0x9B59B6,
                )

                # 모든 라이선스 출력 (단, 디스코드 필드 제한은 최대 25개이므로 주의!)
                for lic in licenses:
                    expired_mark = "🔴 [만료]" if lic["isExpired"] else "🟢 [활성]"
                    embed.add_field(
                        name=f"{expired_mark} `{lic['licenseKey']}`",
                        value=f"기기: `{lic['currentDevices']}/{lic['maxDevices']}` | 만료: `{lic['expireDate']}`",
                        inline=False,
                    )

                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(
                    "❌ 서버 에러: 목록을 불러오지 못했습니다."
                )


# /라이선스삭제
@client.tree.command(
    name="라이선스삭제", description="특정 라이선스를 영구적으로 삭제합니다."
)
async def deleteLicense(interaction: discord.Interaction, license_key: str):
    await interaction.response.defer()

    apiUrl = f"http://localhost:8000/admin/licenses/{license_key}"
    secretKey = os.getenv("ADMIN_SECRET_KEY")

    async with aiohttp.ClientSession() as session:
        async with session.delete(
            apiUrl, headers={"xAdminToken": secretKey}
        ) as response:
            data = await response.json()

            if response.status == 200:
                embed = discord.Embed(
                    title="🗑️ 라이선스 삭제 완료",
                    description=f"`{license_key}` 라이선스가 정상적으로 삭제되었습니다.",
                    color=0xE74C3C,
                )
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(
                    f"❌ 삭제 실패: {data.get('detail', '오류가 발생했습니다.')}"
                )


# /라이선스연장
@client.tree.command(
    name="라이선스연장", description="기존 라이선스의 만료 기간을 연장합니다."
)
async def extendLicense(
    interaction: discord.Interaction, license_key: str, add_days: int
):
    await interaction.response.defer()

    apiUrl = f"http://localhost:8000/admin/licenses/{license_key}/extend"
    secretKey = os.getenv("ADMIN_SECRET_KEY")
    payload = {"addDays": add_days}

    async with aiohttp.ClientSession() as session:
        async with session.patch(
            apiUrl, json=payload, headers={"xAdminToken": secretKey}
        ) as response:
            data = await response.json()

            if response.status == 200:
                newExpireDate = data["data"]["newExpireDate"]
                embed = discord.Embed(title="⏱️ 라이선스 기간 연장 완료", color=0xF1C40F)
                embed.add_field(
                    name="🔑 대상 키", value=f"`{license_key}`", inline=False
                )
                embed.add_field(name="➕ 추가 기간", value=f"{add_days}일", inline=True)
                embed.add_field(
                    name="📅 새 만료일", value=f"{newExpireDate}", inline=True
                )
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(
                    f"❌ 연장 실패: {data.get('detail', '오류가 발생했습니다.')}"
                )


# /라이선스초기화
@client.tree.command(
    name="라이선스초기화",
    description="해당 라이선스에 등록된 기기 정보(HWID)를 모두 초기화합니다.",
)
async def resetLicense(interaction: discord.Interaction, license_key: str):
    await interaction.response.defer()

    apiUrl = f"http://localhost:8000/admin/licenses/{license_key}/reset"
    secretKey = os.getenv("ADMIN_SECRET_KEY")

    async with aiohttp.ClientSession() as session:
        async with session.post(apiUrl, headers={"xAdminToken": secretKey}) as response:
            data = await response.json()

            if response.status == 200:
                embed = discord.Embed(
                    title="🔄 초기화 완료",
                    description=f"`{license_key}` 라이선스의 기기 등록 리스트가 비워졌습니다.\n이제 새 기기에서 등록이 가능합니다.",
                    color=0x34495E,
                )
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(
                    f"❌ 초기화 실패: {data.get('detail', '오류가 발생했습니다.')}"
                )


# 봇 실행
client.run(os.getenv("DISCORD_BOT_TOKEN"))
