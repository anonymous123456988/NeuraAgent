# -*- coding: utf-8 -*-
"""NEURA 服务器: FastAPI + WebSocket + 下载接口 + 静态页面。"""
import asyncio
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from agent.core import AgentCore
from server.emitter import PanelEmitter


def _config_summary(cfg: dict) -> dict:
    api = cfg.get("ai", {}).get("api", {})
    key = api.get("deepseek_api_key", "")
    masked = (key[:6] + "***" + key[-4:]) if len(key) > 10 else ("已配置" if key else "未配置")
    builtin = cfg.get("ai", {}).get("builtin", {})
    use_builtin = bool(cfg.get("ai", {}).get("use_builtin_model", True))
    use_deepseek = bool(cfg.get("ai", {}).get("use_deepseek_api", not use_builtin))
    return {
        "mode": "builtin" if use_builtin else "api",
        "use_builtin_model": use_builtin,
        "use_deepseek_api": use_deepseek,
        "builtin_backend": builtin.get("backend", "nlm"),
        "builtin_model": builtin.get("model_name", ""),
        "api_model": api.get("model", "deepseek-chat"),
        "api_key_masked": masked,
        "agent_name": cfg.get("agent", {}).get("name", "NEURA"),
    }


def create_app(cfg: dict, root: str = ROOT):
    app = FastAPI(title="NEURA Agent", version="1.0.0")
    app.state.core = AgentCore(cfg, root=root)
    app.state.cfg = cfg

    @app.get("/api/health")
    async def health():
        core: AgentCore = app.state.core
        return {"ok": True, "mode": core.brain.mode_label(),
                "sessions": len(core.sessions.sessions)}

    @app.get("/api/config")
    async def get_config():
        return _config_summary(app.state.cfg)

    @app.get("/api/sessions")
    async def list_sessions():
        core: AgentCore = app.state.core
        return {"sessions": core.sessions_list()}

    @app.delete("/api/sessions/{sid}")
    async def delete_session(sid: str):
        core: AgentCore = app.state.core
        ok = core.sessions.delete(sid)
        if not ok:
            raise HTTPException(404, "会话不存在")
        return {"ok": True}

    @app.get("/api/tools")
    async def list_tools():
        """查看当前 Agent 的全部调用集(内置 + 小AI 动态合成)。"""
        core: AgentCore = app.state.core
        builtin = [{"name": t.name, "source": "builtin", "category": t.category}
                   for t in core.registry._tools.values() if not t.hidden and t.source == "builtin"]
        custom = core.custom_tools.list()
        return {"count": len(builtin) + len(custom), "builtin": builtin, "custom": custom}

    @app.delete("/api/tools/{name}")
    async def remove_tool(name: str):
        """删除一个小AI 动态合成的自定义调用集(内置调用集不可删)。"""
        core: AgentCore = app.state.core
        if not core.registry.is_custom(name):
            raise HTTPException(400, "只能删除自定义调用集(custom)")
        if not core.custom_tools.remove(name):
            raise HTTPException(404, "调用集不存在")
        return {"ok": True, "removed": name}

    @app.get("/api/downloads/{session_id}/{filename}")
    async def download(session_id: str, filename: str):
        core: AgentCore = app.state.core
        dl_dir = core.downloads_dir
        target = os.path.realpath(os.path.join(dl_dir, session_id, filename))
        if not target.startswith(os.path.realpath(dl_dir) + os.sep) or not os.path.exists(target):
            raise HTTPException(404, "文件不存在")
        return FileResponse(target, filename=os.path.basename(target))

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await ws.accept()
        core: AgentCore = app.state.core
        emitter = PanelEmitter(ws)
        tasks: dict = {}
        try:
            await emitter.hello(core.sessions_list(), _config_summary(app.state.cfg))
            while True:
                raw = await ws.receive_text()
                import json
                try:
                    msg = json.loads(raw)
                except Exception:
                    await emitter.error("消息格式错误")
                    continue
                mtype = msg.get("type")
                if mtype == "user_message":
                    sid = msg.get("session_id") or ""
                    text = str(msg.get("text", "")).strip()
                    if not text:
                        await emitter.error("消息为空")
                        continue
                    session = core.sessions.get(sid)
                    if session is None:
                        session = core.sessions.create()
                        sid = session.id
                        await emitter.session_created(session.to_dict())
                    if sid in tasks and not tasks[sid].done():
                        await emitter.error("该会话正在处理中，请等待完成")
                        continue
                    task = asyncio.create_task(
                        core.start_turn(sid, text, emitter),
                        name=f"turn_{sid}")
                    tasks[sid] = task

                    async def _cleanup(t, s=sid):
                        try:
                            await t
                        except asyncio.CancelledError:
                            pass
                        except Exception as e:
                            import traceback
                            traceback.print_exc()
                            try:
                                await emitter.error(f"处理出错: {e}")
                            except Exception:
                                pass
                        finally:
                            tasks.pop(s, None)

                    asyncio.create_task(_cleanup(task))
                elif mtype == "cancel":
                    sid = msg.get("session_id") or ""
                    task = tasks.get(sid)
                    if task and not task.done():
                        task.cancel()
                        tasks.pop(sid, None)
                        await emitter.agent_status("idle", core.brain.mode_label())
                        # 广播收尾事件(空文本), 前端据此结束流式气泡, 避免半截卡住
                        await emitter.message_done(sid, "", [])
                        await emitter.notify("已取消当前任务", level="warning")
                    # 无任务在跑: 静默忽略, 不弹无意义提示
                elif mtype == "new_session":
                    session = core.sessions.create()
                    await emitter.session_created(session.to_dict())
                elif mtype == "delete_session":
                    sid = msg.get("session_id") or ""
                    if sid in tasks:
                        tasks[sid].cancel()
                    core.sessions.delete(sid)
                    await emitter.session_deleted(sid)
                elif mtype == "panel_action":
                    # 控制板用户点击交互: 打开文件/进入目录/刷新/执行命令
                    sid = msg.get("session_id") or ""
                    act = str(msg.get("action") or "")
                    params = msg.get("params") or {"path": msg.get("path") or "", "command": msg.get("command") or ""}
                    try:
                        await core.handle_panel_action(sid, act, params, emitter)
                    except Exception as e:
                        await emitter.error(f"控制板操作失败: {e}")
                elif mtype == "admin_auth":
                    # 用户提交系统登录密码 -> 验证通过则解锁挂起的高危操作
                    op_id = msg.get("operation_id") or ""
                    password = str(msg.get("password") or "")
                    if op_id:
                        await core.handle_admin_auth(op_id, password, emitter)
                elif mtype == "admin_cancel":
                    op_id = msg.get("operation_id") or ""
                    if op_id:
                        await core.handle_admin_cancel(op_id, emitter)
                elif mtype == "run_command_direct":
                    # 控制板实时命令窗口: 用户在控制板直接输入命令执行
                    sid = msg.get("session_id") or ""
                    cmd = str(msg.get("command", "")).strip()
                    if cmd:
                        asyncio.create_task(core.handle_command_direct(sid, cmd, emitter))
                elif mtype == "confirm_response":
                    # 用户对控制板确认窗口(如"是否安装依赖")的选择: yes 安装 / no 取消
                    cid = msg.get("confirm_id") or ""
                    yes = bool(msg.get("yes"))
                    if cid:
                        await core.handle_confirm(cid, yes, emitter)
        except WebSocketDisconnect:
            for t in tasks.values():
                if not t.done():
                    t.cancel()
            return

    # 静态资源
    web_dir = os.path.join(root, "web")
    app.mount("/static", StaticFiles(directory=web_dir), name="static")

    @app.get("/")
    async def index():
        return FileResponse(os.path.join(web_dir, "index.html"))

    return app
