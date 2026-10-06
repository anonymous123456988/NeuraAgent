#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NEURA Agent —— 入口脚本
用法:
  python run.py                      # 启动服务器(读取 config.json)
  python run.py --config my.json     # 指定配置文件
  python run.py --host 0.0.0.0 --port 9000
  python run.py --regression         # 只运行自改进回归测试, 不启动服务器
  python run.py --rollback 2         # 回滚自改进到版本 2
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg


def _write_config(path: str, cfg: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="NEURA Agent")
    parser.add_argument("--config", default=os.path.join(ROOT, "config.json"))
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--regression", action="store_true", help="运行回归测试")
    parser.add_argument("--rollback", type=int, default=None, help="回滚自改进到指定版本")
    parser.add_argument("--list-tools", action="store_true", help="列出全部调用集(内置+自定义)")
    parser.add_argument("--remove-tool", default=None, metavar="NAME", help="删除一个自定义调用集")
    args = parser.parse_args()

    if args.rollback is not None:
        from agent.self_improver import SelfImprover
        improver = SelfImprover(os.path.join(ROOT, "system", "improvements.json"),
                                os.path.join(ROOT, "system", "backups"))
        ok = improver.rollback(args.rollback)
        print("回滚成功" if ok else "回滚失败(版本不存在或备份缺失)")
        return

    if args.regression:
        import tests.regression as reg
        ok, report = reg.run_all()
        print(report)
        sys.exit(0 if ok else 1)

    if args.list_tools or args.remove_tool:
        cfg = load_config(args.config)
        from agent.tools.dynamic import CustomToolStore
        from agent.tools import build_registry
        reg = build_registry()
        store = CustomToolStore(os.path.join(ROOT, "system", "custom_tools"), reg, cfg)
        store.load_all()
        if args.remove_tool:
            if not reg.is_custom(args.remove_tool):
                print(f"错误: {args.remove_tool} 不是自定义调用集(内置调用集不可删除)")
                sys.exit(1)
            print("已删除" if store.remove(args.remove_tool) else "删除失败")
            return
        print(f"调用集总数: {len(reg.names())} (内置 {sum(1 for n in reg.names() if not reg.is_custom(n))} + 自定义 {len(store.list())})")
        for t in reg._tools.values():
            if t.hidden:
                continue
            mark = "[自定义]" if t.source == "custom" else "[内置]"
            print(f"  {mark} {t.name}: {t.description[:50]}")
        return

    cfg = load_config(args.config)
    if args.host:
        cfg["server"]["host"] = args.host
    if args.port:
        cfg["server"]["port"] = args.port

    # ---- 模型模式多选一强互斥校验与自动修正 ----
    # 所有 AI 选项(内置NeuraLM/DeepSeek/OpenAI/豆包/元宝/自定义API)统一收敛到唯一模式 ai.mode,
    # 其余开关自动置 false(deepseek 为 true 则其他 AI 选项全为 false); 规范化结果写回 config.json。
    from agent.utils import resolve_ai_mode
    _sw_before = tuple(str(cfg.get(k)) for k in ("use_builtin_model", "use_deepseek_api", "api_provider", "custom_api_enabled"))
    ai_cfg = cfg.setdefault("ai", {})
    _mode_now = resolve_ai_mode(cfg)   # 多选一强互斥: 收敛唯一模式, 开关只存在于顶层
    _sw_after = tuple(str(cfg.get(k)) for k in ("use_builtin_model", "use_deepseek_api", "api_provider", "custom_api_enabled"))
    if _sw_after != _sw_before:
        print(f"[提示] AI 启用开关已收敛为唯一模式: {_mode_now} (其余 AI 启用开关已自动置 false)")
        _write_config(args.config, cfg)
    elif _mode_now == "deepseek" and not ai_cfg.get("api", {}).get("deepseek_api_key"):
        print("[警告] 你选择了 DeepSeek API 模式但未填写 API Key。")
        print("       DeepSeek API 接入已完整保留：填写 config.json 的 ai.api.deepseek_api_key 并重启即可切换。")
        print("       当前自动回退到内置独家大模型 NeuraLM（项目自研、零外部依赖，始终可用）。")
        cfg["use_builtin_model"] = True
        cfg["use_deepseek_api"] = False
        cfg["api_provider"] = "deepseek"
        cfg["custom_api_enabled"] = False
        _write_config(args.config, cfg)
    _mode_lbl = {
        "builtin": "内置独家大模型 NeuraLM (自研/零外部依赖)",
        "deepseek": "DeepSeek API (use_deepseek_api=true, 内置模型=false)",
        "openai": "ChatGPT / OpenAI API (ai.providers.openai)",
        "doubao": "豆包 API (火山方舟, ai.providers.doubao)",
        "yuanbao": "腾讯元宝 API (ai.providers.yuanbao)",
        "custom": "自定义 API (ai.api.custom, 用户自编调用格式)",
    }.get(_mode_now, _mode_now)
    print("=" * 62)
    if cfg["use_builtin_model"]:
        backend = ai_cfg.get("builtin", {}).get("backend", "nlm")
        if backend == "openai_compatible":
            print("  模型模式: 内置大模型 (OpenAI 兼容本地端点, use_deepseek_api=false)")
        elif backend == "ollama":
            print("  模型模式: 内置大模型 (Ollama, use_deepseek_api=false)")
        elif backend == "nlm":
            print("  模型模式: 内置独家大模型 NeuraLM (自研/零外部依赖, use_deepseek_api=false)")
        else:
            print("  模型模式: 内置引擎 NeuraBrain (use_deepseek_api=false)")
    else:
        print(f"  模型模式: {_mode_lbl}")
    print("=" * 62)

    import uvicorn
    from server.main import create_app

    app = create_app(cfg, root=ROOT)
    print("=" * 62)
    print(f"  NEURA Agent 已启动: http://{cfg['server']['host']}:{cfg['server']['port']}")
    backend = ai_cfg.get("builtin", {}).get("backend", "nlm")
    if cfg["use_builtin_model"]:
        mode = {"nlm": "内置独家大模型 NeuraLM", "ollama": "内置大模型 (Ollama)",
                "openai_compatible": "内置大模型 (本地端点)"}.get(backend, "内置引擎 NeuraBrain")
    elif cfg["use_deepseek_api"]:
        mode = "DeepSeek API"
    elif cfg["api_provider"] in ("openai", "doubao", "yuanbao"):
        mode = {"openai": "ChatGPT / OpenAI API", "doubao": "豆包 API", "yuanbao": "腾讯元宝 API"}.get(cfg["api_provider"], cfg["api_provider"])
    else:
        mode = "自定义 API"
    print(f"  模型模式: {mode}")
    print("=" * 62)
    uvicorn.run(app, host=cfg["server"]["host"], port=cfg["server"]["port"], log_level="info")


if __name__ == "__main__":
    main()
