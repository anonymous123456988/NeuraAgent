# -*- coding: utf-8 -*-
"""NEURA Agent 通用工具函数"""
import datetime
import json
import os
import re
import threading
import unicodedata

_LOCKS: dict = {}
_LOCK_GUARD = threading.Lock()


def get_lock(key: str) -> threading.Lock:
    with _LOCK_GUARD:
        if key not in _LOCKS:
            _LOCKS[key] = threading.Lock()
        return _LOCKS[key]


def now_iso() -> str:
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def safe_filename(name: str, fallback: str = "file") -> str:
    name = unicodedata.normalize("NFKC", name or "")
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", name).strip(" .")
    return name[:120] or fallback


def truncate(text: str, n: int = 8000) -> str:
    if text is None:
        return ""
    text = str(text)
    return text if len(text) <= n else text[:n] + f"...[已截断, 共{len(text)}字符]"


def json_dumps_compact(obj) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return str(obj)


def read_json(path: str, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def write_json(path: str, data) -> bool:
    lock = get_lock(path)
    with lock:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
            return True
        except Exception:
            return False


def deep_merge(base: dict, patch: dict) -> dict:
    out = dict(base)
    for k, v in (patch or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def approx_chars_per_token_factor(text: str) -> float:
    """估算中文为主的文本 1 token ≈ 1.5 字符。"""
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    total = max(len(text), 1)
    ratio = cjk / total
    return 1.3 + 0.8 * ratio


def trim_messages_for_context(messages: list, max_chars: int) -> list:
    """按字符预算裁剪历史消息(保留最早的系统消息与最近的若干条)。"""
    if not messages:
        return messages
    kept = [messages[0]] if messages[0].get("role") == "system" else []
    rest = messages[1:] if kept else messages
    budget = max_chars - sum(len(json_dumps_compact(m)) for m in kept)
    acc = 0
    tail = []
    for m in reversed(rest):
        cost = len(json_dumps_compact(m))
        if acc + cost > budget and tail:
            break
        acc += cost
        tail.insert(0, m)
    return kept + tail


def extract_code_blocks(text: str):
    """从模型回复中提取代码块: 返回 [(language, code), ...]"""
    blocks = re.findall(r"```([\w+]*)\s*\n(.*?)```", text, flags=re.S)
    if blocks:
        return [(lang or "text", code.strip("\n")) for lang, code in blocks]
    return []


def human_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} TB"


def normalize_messages_for_api(messages: list) -> list:
    """发送给外部 API(DeepSeek/Ollama/OpenAI)前的消息规范化:
    - 丢弃孤立 tool 消息(前面无对应 assistant tool_calls);
    - 移除"已声明但从未收到 tool 回复"的 tool_calls(DeepSeek 严格校验:
      assistant 的每个 tool_call_id 都必须有 tool 消息回应, 否则 HTTP 400);
    - 只保留 API 允许的字段(严格端点会把多余字段如 name 判 400);
    - 末尾配对完整的 tool 消息保留(允许 tool 结尾继续轮次)。
    """
    out: list = []
    # 记录"已声明、等待回复"的 tool_call_id 集合
    pending: set = set()
    # 为每条带 tool_calls 的 assistant 保存索引 -> 其声明的 ids(用于补配对)
    for m in messages:
        if not isinstance(m, dict):
            continue
        role = str(m.get("role") or "")
        if role not in ("system", "user", "assistant", "tool"):
            continue
        if role == "tool":
            tcid = str(m.get("tool_call_id") or "")
            if tcid and tcid not in pending:
                continue                       # 孤立 tool 消息 -> 丢弃
            pending.discard(tcid)               # 已回复, 移出等待集合
            out.append({"role": "tool", "tool_call_id": tcid,
                        "content": m.get("content", "") if m.get("content") is not None else ""})
            continue
        if role == "assistant":
            tc = m.get("tool_calls")
            if tc:
                ids = set()
                norm_calls = []
                for c in tc:
                    if not isinstance(c, dict):
                        continue
                    cid = str(c.get("id") or "")
                    if not cid:
                        continue
                    ids.add(cid)
                    pending.add(cid)             # 声明待回复
                    fn = c.get("function") or {}
                    norm_calls.append({
                        "id": cid, "type": "function",
                        "function": {"name": str(fn.get("name") or ""),
                                     "arguments": str(fn.get("arguments") or "")},
                    })
                msg = {"role": "assistant", "content": m.get("content") or ""}
                if norm_calls:
                    msg["tool_calls"] = norm_calls
                out.append(msg)
            else:
                out.append({"role": "assistant", "content": m.get("content") or ""})
            continue
        # user / system
        content = m.get("content")
        out.append({"role": role, "content": content if content is not None else ""})

    # 配对修正(两遍法, 不依赖遍历状态): DeepSeek 严格校验【每一条】assistant 的
    # 每个 tool_call_id 都必须有 tool 消息回应, 否则 HTTP 400("insufficient tool
    # messages following tool_calls")。因此【所有】带 tool_calls 的 assistant 都要修正,
    # 不只末尾一条(多轮会话中早期轮次的声明残留同样会触发 400):
    #  - 已收到回复的 tool_calls 保留(配对完整);
    #  - 无回复的声明剔除(该 assistant 退化为纯文本, 保留 content 不丢信息);
    #  - 修正后若使后续 tool 消息变孤立, 一并移除(避免"tool 无前导声明"类 400)。
    replied = {str(m.get("tool_call_id")) for m in out
               if m.get("role") == "tool" and m.get("tool_call_id")}
    valid_calls_ids = set()
    for i in range(len(out) - 1, -1, -1):
        m = out[i]
        if m.get("role") != "assistant" or not m.get("tool_calls"):
            continue
        calls = []
        for c in m.get("tool_calls") or []:
            cid = str(c.get("id") or "")
            if cid in replied:
                calls.append(c)
                valid_calls_ids.add(cid)
        if calls:
            out[i] = {**m, "tool_calls": calls}
        else:
            out[i] = {**m}
            out[i].pop("tool_calls", None)
    # 兜底: 若仍有 assistant 声明 id 未被任何 tool 消息回复(理论已被上循环清空),
    # 或存在 tool 消息引用了已被剔除的声明 -> 移除孤立 tool 消息
    if valid_calls_ids:
        cleaned = []
        for m in out:
            if m.get("role") == "tool":
                tcid = str(m.get("tool_call_id") or "")
                if tcid not in valid_calls_ids:
                    continue          # 该 tool 回复的声明已被剔除 -> 一并移除
            cleaned.append(m)
        out = cleaned
    return out

def resolve_ai_mode(cfg: dict) -> str:
    """AI 启用选项多选一强互斥(开关【仅存在于 config.json 最顶部】)。

    顶层启用开关(唯一真源, ai 段不再保留任何开关):
      use_builtin_model  内置独家大模型 NeuraLM
      use_deepseek_api   DeepSeek API
      api_provider       预置通道: deepseek | openai | doubao | yuanbao
      custom_api_enabled 自定义 API(ai.api.custom)

    恰好一个开关生效(某开关为 true 则其余启用开关自动置 false, 如 use_deepseek_api=true
    则 use_builtin_model=false 等); 冲突时按 内置>DeepSeek>预置通道>自定义 优先级取一。
    规范化只写顶层并清理 ai 段冗余开关(旧版残留的 ai.use_* / ai.mode 一并移除)。
    兼容旧结构: 顶层缺失时从 ai 段读取一次用于推断, 推断后旧开关被移除。
    返回唯一模式名 builtin | deepseek | openai | doubao | yuanbao | custom。
    """
    ai = cfg.setdefault("ai", {})
    providers = ai.get("providers") or {}
    custom_cfg = (ai.get("api") or {}).setdefault("custom", {})

    # ---- 读取启用开关: 顶层优先, 兼容 ai 段残留(仅用于推断) ----
    use_builtin = bool(cfg.get("use_builtin_model", ai.get("use_builtin_model", True)))
    use_deepseek = bool(cfg.get("use_deepseek_api", ai.get("use_deepseek_api", False)))
    provider = str(cfg.get("api_provider", ai.get("api_provider", "deepseek")))
    custom_on = bool(cfg.get("custom_api_enabled", custom_cfg.get("enabled", False)))

    # ---- 判定唯一模式(优先级: 内置 > DeepSeek > 预置通道 > 自定义) ----
    if use_builtin:
        mode = "builtin"
    elif use_deepseek:
        mode = "deepseek"
    elif provider in ("openai", "doubao", "yuanbao"):
        mode = provider
    elif custom_on:
        mode = "custom"
    else:
        if custom_cfg.get("enabled"):
            mode = "custom"
        elif provider in ("openai", "doubao", "yuanbao"):
            mode = provider
        elif ai.get("use_deepseek_api"):
            mode = "deepseek"
        else:
            mode = "builtin"

    # ---- 规范化只写顶层(唯一真源) ----
    cfg["use_builtin_model"] = (mode == "builtin")
    cfg["use_deepseek_api"] = (mode == "deepseek")
    cfg["api_provider"] = mode if mode in ("openai", "doubao", "yuanbao") else "deepseek"
    cfg["custom_api_enabled"] = (mode == "custom")
    for p in providers:
        providers[p]["enabled"] = (mode == p and p in ("openai", "doubao", "yuanbao"))
    custom_cfg["enabled"] = (mode == "custom")

    # ---- 清理 ai 段冗余开关(旧版残留) ----
    for _k in ("use_builtin_model", "use_deepseek_api", "api_provider", "custom_api_enabled", "mode"):
        ai.pop(_k, None)
    return mode
