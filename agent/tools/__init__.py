# -*- coding: utf-8 -*-
"""工具调用集(调用集)包: 构建完整工具注册表。"""
from .registry import Tool, ToolResult, ToolContext, ToolRegistry
from . import panel, filesystem, system, web, code, dynamic, app_control, findfile, agent_repair


def build_registry() -> ToolRegistry:
    r = ToolRegistry()
    panel.register(r)
    filesystem.register(r)
    system.register(r)
    web.register(r)
    code.register(r)
    dynamic.register(r)     # 小AI 工具工厂: synthesize_tool
    app_control.register(r)  # 软件操控: app_control / kill_process
    findfile.register(r)     # 查找文件: find_file
    agent_repair.register(r) # v3.25 自修复: read_agent_file / agent_repair(小AI 监管)
    return r
