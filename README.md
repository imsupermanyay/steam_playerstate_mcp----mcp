# Steam MCP Tools

查询 Steam 玩家状态的 MCP 服务。

## 功能

- `check_steam_status` - 查询玩家在线状态、正在玩的游戏
- `get_recently_played` - 查询玩家最近玩过的游戏列表
- `get_owned_games_count` - 查询玩家拥有的游戏数量

## 环境变量

- `STEAM_API_KEY` - Steam Web API Key（在 https://steamcommunity.com/dev/apikey 申请）

## 运行方式

本地 stdio 模式：
```bash
STEAM_API_KEY=你的key python server.py
```

远程 SSE 模式：
```bash
STEAM_API_KEY=你的key python server.py --sse
```

## AstrBot MCP 配置示例

本地模式：
```json
{
  "mcpServers": {
    "steam-tools": {
      "command": "python",
      "args": ["server.py"],
      "env": {
        "STEAM_API_KEY": "你的Steam API Key"
      }
    }
  }
}
```

远程 SSE 模式：
```json
{
  "mcpServers": {
    "steam-tools": {
      "url": "https://你的魔搭链接/sse"
    }
  }
}
```
