"""
Steam MCP Tools - 查询Steam玩家状态的MCP服务
支持 stdio 本地模式 和 SSE 远程模式
"""
import os
import sys
import httpx
from mcp.server.fastmcp import FastMCP

STEAM_API_KEY = os.environ.get("STEAM_API_KEY", "")

mcp = FastMCP(
    "steam-tools",
    description="查询Steam玩家在线状态、正在玩的游戏、最近游玩记录等信息"
)

PERSONA_STATES = {
    0: "离线",
    1: "在线",
    2: "忙碌",
    3: "离开",
    4: "打盹",
    5: "想交易",
    6: "想玩游戏"
}


async def _steam_get(url: str, params: dict) -> dict:
    """统一的Steam API请求方法"""
    params["key"] = STEAM_API_KEY
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
async def check_steam_status(steam_id: str) -> str:
    """查询某个Steam用户的在线状态和正在玩的游戏。
    需要提供用户的Steam 64位ID（17位数字）。
    返回用户昵称、在线状态、正在玩的游戏等信息。"""
    if not STEAM_API_KEY:
        return "错误: 未配置STEAM_API_KEY环境变量"

    try:
        data = await _steam_get(
            "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/",
            {"steamids": steam_id}
        )
    except Exception as e:
        return f"请求Steam API失败: {e}"

    players = data.get("response", {}).get("players", [])
    if not players:
        return f"未找到Steam ID为 {steam_id} 的用户"

    p = players[0]
    name = p.get("personaname", "未知")
    state = PERSONA_STATES.get(p.get("personastate", 0), "未知")
    game = p.get("gameextrainfo")
    game_id = p.get("gameid")
    profile_url = p.get("profileurl", "")

    result = f"玩家: {name}\n状态: {state}"
    if game:
        result += f"\n正在玩: {game}"
    else:
        result += "\n当前没有在玩游戏"
    return result


@mcp.tool()
async def get_recently_played(steam_id: str, count: int = 5) -> str:
    """查询某个Steam用户最近玩过的游戏列表。
    需要提供用户的Steam 64位ID。
    可选指定返回数量，默认5个。"""
    if not STEAM_API_KEY:
        return "错误: 未配置STEAM_API_KEY环境变量"

    try:
        data = await _steam_get(
            "https://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v1/",
            {"steamid": steam_id, "count": count}
        )
    except Exception as e:
        return f"请求Steam API失败: {e}"

    games = data.get("response", {}).get("games", [])
    if not games:
        return f"该用户最近没有游玩记录，或资料设为私密"

    lines = [f"最近玩过的游戏 (共{len(games)}个):"]
    for g in games:
        name = g.get("name", "未知游戏")
        playtime_2weeks = g.get("playtime_2weeks", 0)
        playtime_forever = g.get("playtime_forever", 0)
        hours_2w = round(playtime_2weeks / 60, 1)
        hours_total = round(playtime_forever / 60, 1)
        lines.append(f"  - {name}: 最近两周 {hours_2w}h / 总计 {hours_total}h")
    return "\n".join(lines)


@mcp.tool()
async def get_owned_games_count(steam_id: str) -> str:
    """查询某个Steam用户拥有的游戏数量。
    需要提供用户的Steam 64位ID。"""
    if not STEAM_API_KEY:
        return "错误: 未配置STEAM_API_KEY环境变量"

    try:
        data = await _steam_get(
            "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/",
            {"steamid": steam_id, "include_played_free_games": 1}
        )
    except Exception as e:
        return f"请求Steam API失败: {e}"

    count = data.get("response", {}).get("game_count", 0)
    return f"该用户共拥有 {count} 款游戏"


if __name__ == "__main__":
    # 默认 stdio 模式，本地运行
    # 远程部署时使用: python server.py --sse
    if "--sse" in sys.argv:
        mcp.run(transport="sse")
    else:
        mcp.run()
