"""
Steam MCP Tools - 查询Steam玩家状态和游戏服务器状态的MCP服务
支持 stdio 本地模式 和 SSE 远程模式
"""
import os
import sys
import asyncio
import httpx
import a2s
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


@mcp.tool()
async def query_game_server(address: str, port: int = 27015) -> str:
    """查询Steam游戏服务器的状态信息。
    需要提供服务器IP地址和端口号（默认27015）。
    返回服务器名称、地图、在线人数、最大人数、延迟等信息。
    支持所有Source引擎游戏服务器，如Garry's Mod、CS2、TF2等。"""
    try:
        info = await asyncio.to_thread(
            a2s.info, (address, port), timeout=5
        )
    except Exception as e:
        return f"无法连接到服务器 {address}:{port}，可能离线或地址错误: {e}"

    result = (
        f"服务器名称: {info.server_name}\n"
        f"游戏: {info.game}\n"
        f"当前地图: {info.map_name}\n"
        f"在线人数: {info.player_count}/{info.max_players}\n"
        f"延迟: {round(info.ping * 1000)}ms\n"
        f"VAC: {'开启' if info.vac_enabled else '关闭'}\n"
        f"需要密码: {'是' if info.password_protected else '否'}"
    )
    return result


@mcp.tool()
async def query_server_players(address: str, port: int = 27015) -> str:
    """查询Steam游戏服务器上当前在线的玩家列表。
    需要提供服务器IP地址和端口号（默认27015）。
    返回每个玩家的名字和游玩时长。"""
    try:
        players = await asyncio.to_thread(
            a2s.players, (address, port), timeout=5
        )
    except Exception as e:
        return f"无法查询服务器 {address}:{port} 的玩家列表: {e}"

    if not players:
        return "服务器当前没有玩家在线"

    lines = [f"在线玩家 ({len(players)}人):"]
    for p in sorted(players, key=lambda x: x.duration, reverse=True):
        hours = int(p.duration // 3600)
        mins = int((p.duration % 3600) // 60)
        name = p.name if p.name else "(未知)"
        lines.append(f"  - {name}: 已游玩 {hours}h{mins}m")
    return "\n".join(lines)


if __name__ == "__main__":
    # 默认 stdio 模式，本地运行
    # 远程部署时使用: python server.py --sse
    if "--sse" in sys.argv:
        mcp.run(transport="sse")
    else:
        mcp.run()
