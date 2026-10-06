# NEURA —— AI Agent Web 智能体

一个**完整闭环的 AI Agent**：内置**独家自研大模型 NeuraLM**（纯 NumPy 从零训练，零外部依赖）+ DeepSeek API 双模式切换、完整工具调用集（调用集）、Web 图形界面（科技幽蓝透明控制板）、联网搜索/天气、代码编写→运行→自动调试→打包下载、**小AI 动态调用集工厂**（最高修改权 + 分层安全审查）、**带回归防线的自我改进**。

```
┌────────────────────────────────────────────────────────────┐
│  顶部: 会话列表                                              │
├──────────────────────────┬─────────────────────────────────┤
│ 左侧: 控制板(科技幽蓝透明)  │ 右侧: 对话框                    │
│  AI 操作结果在此弹窗展示     │  只输出文本/摘要                │
│  窗口可拖动/关闭/最大化      │  工具调用过程以卡片实时展示       │
└──────────────────────────┴─────────────────────────────────┘
```

---

## 1. 快速开始

```bash
# 1) 安装依赖 (Python 3.9+)
pip install -r requirements.txt

# 2) 配置模型(互斥二选一, 见 config.json)
#    · 内置独家大模型 NeuraLM(默认): use_builtin_model = true, use_deepseek_api = false,
#        builtin.backend = "nlm" —— 项目从零自研的 Transformer 语言模型,
#        权重由内置中文语料训练并随项目交付, 开箱即用, 完全离线, 不用任何别人的模型。
#       - 可选增强(不改变默认): backend = "ollama"(本地 Ollama 大模型, 用 setup_model.py 一键部署)
#       - 或 backend = "openai_compatible"(任意本地 OpenAI 兼容服务)
#    · DeepSeek API: use_builtin_model = false, use_deepseek_api = true,
#       并填写 api.deepseek_api_key
python run.py
```

打开浏览器访问 `http://127.0.0.1:8765` 即可使用。

## 2. 配置文件开关（核心 · 互斥强校验）

```jsonc
// config.json —— 模型模式互斥: 二者只可其一, 启动时自动强制修正
"ai": {
  "use_builtin_model": true,    // ← true=内置大模型; false=DeepSeek API
  "use_deepseek_api": false,    // ← 显式互斥开关: 内置模型时强制为 false
  "builtin": { "backend": "ollama" | "openai_compatible" | "engine",
               "model_name": "qwen2.5:7b", ... },
  "api": {
    "deepseek_api_key": "",     // ← use_builtin_model=false 时必填
    "model": "deepseek-chat",   //    deepseek-chat = 关闭深度思考(非推理模型)
    "disable_reasoning": true   //    丢弃任何 reasoning_content, 只留答案/工具调用
  }
}
```

**互斥规则（已实现强校验与自动修正）**：
- `use_builtin_model=true`（选择内置 AI）→ 强制 `use_deepseek_api=false`；
- `use_builtin_model=false`（选择 DeepSeek）→ 强制 `use_deepseek_api=true`（且内置 AI 为 false）；
- 两个开关同时为 true / 同时为 false 时，`run.py` 启动即自动修正并写回配置并提示，不会以错误状态运行。

**DeepSeek 模式下的工作方式（按你的要求）**：
1. Agent 先把**完整的调用集（全部工具 JSON Schema）**发给 DeepSeek；
2. 使用 `deepseek-chat`（非 `deepseek-reasoner`）+ 显式丢弃 `reasoning_content`，即**关闭深度思考**；
3. Agent 把对话历史与**每个工具结果实时回传**（每执行完一个工具立即作为 tool 消息发回），DeepSeek 基于最新数据继续决策；
4. DeepSeek 返回工具调用 → Agent 执行 → 结果回流 → 循环，直到输出最终文本。

## 3. 内置 AI 大模型（use_builtin_model = true）

一个模型必须经过**互联网预训练**才能真正理解自然语言，代码文件无法自带权重（动辄几十 GB），因此内置模式提供三种后端，确保"内置 AI 就是大模型 AI"：

| 后端 | 说明 |
|---|---|
| **Ollama（推荐）** | 连接本机 Ollama，使用互联网预训练大模型（Qwen / Llama 等），支持流式与工具调用。`ollama pull qwen2.5:7b` 一条命令即可。 |
| **OpenAI 兼容本地大模型** | `backend = "openai_compatible"`：连接 LM Studio / vLLM / 任意本地 OpenAI 兼容端点（配置 `openai_base_url` 指向已加载模型的地址），同样支持流式与工具调用，等于把任何本地大模型变成"内置 AI"。 |
| **内置引擎 NeuraBrain（零依赖兜底）** | 纯 Python 实现的增强引擎：MiniAI 意图理解 + **多轮上下文**（引用上一操作："再查一次"→ 复用 get_time）+ **多工具计划**（"查看文件然后统计字数" → 一次返回多个调用，其中统计能力不足时自动触发小AI 合成）+ 记忆/自改进规则注入 + 智能降级答复。无需联网、无需安装任何东西，闭环完整。 |

配置 `builtin.backend` 为 ollama / openai_compatible 且端点不可用时，自动按 `auto_fallback_to_engine` 降级到 NeuraBrain，不会崩。

## 3.5 电影级丝滑窗口系统（v3.0）

控制板窗口全面升级为电影质感的交互体验（对应"像电影中 AI 那样滑动窗口"的需求）：

- **玻璃拟态**：双层渐变 + `backdrop-filter` 毛玻璃 + 顶部 HUD 光条 + 深阴影，聚焦窗口带呼吸光晕动画；
- **丝滑开合**：窗口打开/关闭/最小化/还原均为弹性曲线动画（轻微过冲 `cubic-bezier` + 模糊渐变），不再生硬闪现；
- **自由滑动窗口**：Pointer Events 统一处理鼠标/触摸，拖拽全程用 `transform` 跟手（零重排、不掉帧），拖拽中窗口微放大并带光晕；**双击标题栏最大化/还原**；
- **窗口缩放**：右下角缩放手柄可自由拖拽调整窗口大小（hover 显现）；
- **窗口坞**：chips 滑入动画、悬浮上浮、聚焦高亮，点击还原最小化窗口；
- 内容动效：表格行/文件行/日志行依次滑入，气泡消息与工具卡片渐入。

## 3.6 取消任务修复（v3.1）

修复了截图反馈的"连续弹出多个『已取消当前任务』"问题，整体改动三处：

- **前端误取消 bug（根因）**：旧版 `sendCurrent()` 在每次发送指令后都会无条件发送 `cancel`，导致新指令打断上一条仍在执行的任务并触发取消提示，连点指令就会堆叠多个"已取消当前任务"。现已移除该调用——**发送指令不再取消任何任务**；
- **取消收尾**：手动按 `Ctrl+Enter` 停止时，服务端在真正取消成功后广播空文本 `message_done` 收尾事件并回到 idle，前端据此结束流式气泡（本地先打 `(已停止)` 标记兜底），不再卡在半截"生成中"状态；仅在有任务运行时提示一次"已取消当前任务"；
- **toast 去重**：相同文本、相同级别的提示在显示期间只刷新计时，不再叠加重复气泡（对服务端所有提示通用）。

## 3.7 HTML 运行修复 + 输入框固定（v3.2）

修复了截图反馈的 `SyntaxError: invalid decimal literal` 与输入框随对话变长移动两个问题：

- **HTML 不再交给解释器执行（根因）**：旧版"帮我写一个计算器程序"生成 `calculator.html` 后，仍用 `python calculator.html` 运行，Python 把 HTML 当源码解析 CSS 里的 `margin:0;` 等，报 `SyntaxError: invalid decimal literal`。现按**文件扩展名**选择运行方式：`.py/.js/.sh` 进沙箱执行；`.html/.htm` 浏览器渲染类代码**不经解释器**，直接在控制板内弹出「运行预览」窗口（iframe 沙箱渲染，可拖拽/缩放），随后照常打包下载（下载后浏览器直接打开）；
- **输入框悬浮固定最底部**：`#chat` 锁定视口剩余高度，`.chat-log` 增加 `min-height: 0`——对话再长也只在其内部滚动，输入栏永远悬浮固定在对话框最底部，不随对话变长移动；输入栏加玻璃拟态底与上浮阴影，视觉悬浮感更强。

## 3.8 四项整体升级（v3.3）

1. **修复 Windows 编码崩溃（图二根因）**：脚本输出 Emoji/生僻字时，Windows 控制台按 GBK 编码抛 `UnicodeEncodeError: 'gbk' codec can't encode character`。现已双重修复：沙箱在所有平台（含 Windows）强制 `PYTHONIOENCODING=utf-8` + `PYTHONUTF8=1`，且内置代码模板（爬虫/问候/通用）在脚本内 `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` 兜底——Emoji 输出不再崩溃。

2. **完整内置大模型（图一：不再只是引擎模式提示）**：`python setup_model.py` 一键部署真正的互联网预训练大模型——自动检测/安装 Ollama（Windows/macOS/Linux 官方命令），自动拉取模型（默认 `qwen2.5:1.5b`，可 `--model qwen2.5:7b`），写回 config（`use_builtin_model=true, use_deepseek_api=false` 互斥），重启即用。需要大模型能力时的提示升级为给出 A/B 两个即时可用方案并附一键部署指引。

3. **AI 可关闭/滑动窗口**：新增 `panel_control` 工具（close/close_all/move/focus/minimize/restore），小AI 理解「关闭所有窗口」「把窗口移动到 100,200」「最小化窗口」等指令并执行；code_task 等任务结束自动关闭过程窗口（编辑器/预览窗口保留）。窗口未指定 ID 时作用于当前聚焦窗口。

4. **《极限审判》全息科技风**：控制板画布叠加六边形 HUD 网格科技花纹；窗口升级为全息投影样式——四角科技端点、外晕发光、标题栏 HUD 扫描线、底部全息标识条；开合/最小化动画带全息投影展开/消散效果（clip-path + 亮度），配合幽蓝配色与既有丝滑拖拽/缩放。

## 3.9 内置独家大模型 NeuraLM（v3.4）

**内置 AI 大模型不再使用任何外部/第三方模型**（不用 Ollama / DeepSeek / LM Studio 等），改为项目**从零自研的独家大模型 NeuraLM**：

- **自研架构**：`agent/nlm/` 模块 —— `vocab.py`（中文优先的字符级词表）、`model.py`（纯 NumPy 实现的 Mini Transformer：词嵌入 + 位置编码 + 多层 Causal Self-Attention + FFN + LayerNorm，含**手写反向传播**并经数值梯度自检）、`train.py`（Adam 训练器 + 交叉熵 + checkpoint）、`corpus.py`（内置中文知识语料 = 项目自带的离线预训练数据）、`engine.py`（NeuraLM 推理引擎：加载/自动训练/续训/采样生成）。
- **独家权重**：权重由内置语料真实训练生成（约 2.1MB，`system/nlm/model.npz`），**随项目交付**，首次启动即加载，完全离线、零网络依赖。
- **完整闭环**：用户指令 → 小AI 意图解析（最高修改权 + 危险拦截）→ 有工具意图走调用集执行；无工具意图（闲聊/总结）由 **NeuraLM 真实推理生成中文**；工具结果回合由 NeuraLM 生成总结。
- **自我提升不退化**：`python train_model.py` 手动训练 / `--corpus 我的语料.txt` 追加语料在线续训（自我改进），`--d 192 --layers 3` 可升级模型规格；所有规则修改仍须通过回归测试（50 项）。
- **配置**：`config.json → ai.builtin.backend = "nlm"`（默认）。Ollama / OpenAI 兼容本地端点保留为可选后端，不影响默认闭环。

## 3.10 DeepSeek API 接入（完整保留，与 NeuraLM 互斥切换）

**DeepSeek API 接入从头到尾完整保留**——内置模型不用别人的模型，但用户仍可随时切换到 DeepSeek 大模型驱动 Agent：

- **互斥二选一**：`config.json` 中 `ai.use_builtin_model`（内置独家 NeuraLM，默认）与 `ai.use_deepseek_api`（DeepSeek API）互斥，二者同 true 时强制使用内置并写回；同 false 时强制内置。
- **切换为 DeepSeek**：`use_builtin_model = false`、`use_deepseek_api = true`，填写 `ai.api.deepseek_api_key`（也支持 `base_url`/`model`，默认 `deepseek-chat`），重启 `run.py` 即生效。
- **关闭深度思考**：`ai.api.disable_reasoning = true`（默认）→ 使用非推理模型 `deepseek-chat`，流式响应中丢弃 `reasoning_content`，只保留最终答案与工具调用。
- **完整调用集 + 实时回传**：DeepSeek 模式下，Agent 把**完整调用集（tool schemas）**随对话发给 DeepSeek；DeepSeek 返回工具调用后，Agent 执行并将**每个工具结果实时回传**，如此多轮直到任务完成——即"Agent 帮 AI 完成任何合法操作"。
- **无 Key 自动回退**：选了 DeepSeek 模式但未填 Key 时不再退出——自动回退到内置独家大模型 NeuraLM 并提示填写方式，服务不中断。
- **前端标识**：模式栏实时显示 `DeepSeek(deepseek-chat) · 内置模型:OFF · DeepSeek:ON` 或 `内置模型 · 独家大模型 NeuraLM · DeepSeek:OFF`。

## 3.11 三项修复（v3.5）

1. **修复答非所问**：工具结果回合不再由 NeuraLM 自由续写（曾输出无关语料片段），改为**确定性结果模板**——按最近执行的工具名与结果生成对应中文总结（`现在时间是…` / `已列出 … 个文件…` / `已为你查询 X 今日天气…`），回答必与所问相关。NeuraLM 仍负责无工具意图的闲聊生成。
2. **管理员操作分级 + 红色警示窗口**：新增 `permissions.admin_commands`（ps/top/free/systeminfo/netstat/tasklist/whoami/ipconfig/reg 等敏感只读查询）。AI 可调用任何合法操作：命中管理员命令 → **放行**并在左侧控制板弹出**红色警示窗口**（标题 `⚠ 管理员操作 · …`，红色脉冲边框 + 警示条），对话框工具卡片同步红色标记；高危破坏性命令仍由小AI 拦截。
3. **文件夹路径解析修复**：`resolve_path` 相对路径基准改为**用户主目录**（不再解析到服务器进程目录）；`list_directory` 支持纯文件夹名映射（`desktop→~/Desktop`、`下载→~/Downloads`、`我的桌面` 等），目录不存在自动回退主目录并提示；小AI 新增「进入/打开 X 文件夹」「X 文件夹中的文件」意图，以及「查看系统进程」（→ `ps aux`/`tasklist`，红色警示窗口）、「打开cmd/终端/记事本/浏览器」「查看股票」等意图，修复"查看指定文件夹却显示根目录"。

## 3.12 六项升级（v3.6）：软件操控 / 进程管理 / 窗口自主布局 / 预览 / 信息整理 / 布局优化

1. **AI 可运行并操控电脑里的任何软件**：新增 `app_control` 调用集（Windows 注册表/PATH 定位、macOS `open -a`、Linux `which`+`xdg-open`），支持 `launch` 启动任意应用（QQ/微信/浏览器/Steam…）、`send_message` 自动发消息（启动应用→聚焦→输入→回车，含 QQ/微信别名表）、`type_text` 输入文本、`screenshot` 截取软件界面渲染到控制板、`focus` 聚焦窗口。注入防护：应用名/参数含 shell 元字符（`;`/`&&`/`|`/`$`…）直接拒绝。操控软件时左侧控制板以 **appview 软件窗口**渲染（有截图显示实时画面，无截图显示运行状态与操作步骤，可双击放大）。
2. **按指令杀死进程**：新增 `kill_process`（`taskkill /IM` / `pkill -x` 精确进程名，避免误杀无关进程），系统关键进程（system/svchost/lsass/explorer 等）黑名单保护拒绝；属于**管理员级操作**，成功/失败均在控制板弹红色警示窗口。
3. **AI 自主连续调整窗口（一次指令完成，非"说一声动一下"）**：`panel_control` 新增 `layout` 动作——`kind=maximize_all`（全部窗口依次最大化）或 `kind=grid`（网格平铺），前端以**串联 setTimeout 丝滑动画**逐窗口自主连续调整；新增 `maximize` 单窗最大化；关闭/滑动/聚焦/最小化/还原全部保留。
4. **上网搜索 + 信息整理**：`web_search`（DuckDuckGo/Bing 双通道）返回结构化 `results`（标题/链接/摘要）在控制板表格窗口渲染；小AI 意图覆盖「搜索 X」「查看股票」等联网需求。
5. **按指令预览可预览内容**：新增 `preview_file`——图片 → 控制板 image 窗口（base64 渲染，**双击最大化**）；HTML → html_preview 窗口（安全渲染）；文本 → code 窗口；目录/别名（桌面/下载）→ files 窗口（复用别名映射与回退）。
6. **布局优化**：控制板与对话框网格由 `38%/62%` 调整为 **`55%/45%`**（扩大控制板、稍减对话框）；新增 `.pbody-appview`/`.pbody-image` 科技幽蓝样式。
7. **小AI 意图全面升级**：运行/打开任意软件、用 QQ/微信发消息、截取界面、杀死/结束进程、预览图片/文件、整理/平铺/最大化窗口（含"放大天气窗口"不再被天气分支抢占——窗口管理分支已前移）；并修复「运行微信」被 run_command 抢占（软件操控分支前移）、预览路径提取（桌面/下载别名 + 兜底）。

## 3.13 完全操控 + 三级安全中枢（v3.7）：系统登录密码解锁 / 恶意直拦 / 全操作上板 / API 全能力

1. **AI 可完全操控宿主机的所有合法操作**：删除文件/文件夹（新增 `delete_file`/`delete_folder` 调用集，递归删除+根路径/主目录/系统关键目录保护）、结束任意进程、运行/操控任意软件、联网搜索、窗口管理、代码编写调试下载、预览等，凡是用户提出的合法要求都会尝试完成。
2. **三级安全中枢（`agent/security.py` 新增）**：
   - **恶意操作直接拦截**：`classify_operation` 对每次工具调用做风险分级，命中恶意特征（擦盘/格式化/关闭安全软件/篡改系统密码/提权建号/后门自启动/攻击性命令/删除根路径/杀系统关键进程等）→ **不执行、不询问**，控制板弹 `⛔ 恶意操作已拦截` 红色窗口；小AI 文本层同步加强（关闭杀毒/防火墙、改他人密码、root 建号、ddos、勒索挖矿等直接拒绝）。
   - **高危操作需系统登录密码解锁**：删除文件/文件夹、杀进程、卸载软件、清理磁盘等 → 在控制板弹出**幽蓝科技风密码验证窗口**（非系统弹窗），输入**系统登录密码**：Windows 走 `LogonUserW`、Linux/macOS 走 `libpam`（子进程隔离验证，崩溃不影响主服务）；无系统认证环境（无头 VM）可配置 `security.fallback_password_hash`（sha256）兜底。密码正确 → 解锁执行（红色管理员窗口标注）；错误 → 拒绝并允许重试；超时/取消 → 自动放弃。
   - **常规操作直接执行**（白名单/管理员命令/软件/搜索/窗口等一切正常能力不受影响）。
3. **所有操作都显示在控制板**：工具成功 → 按类型弹窗（文件/表格/代码/天气/软件界面/图片预览…）；工具失败 → 控制板弹**红色错误窗口**（`❌ 操作失败 · 原因`），对话框同步输出——"能显示的显示，不能显示的显示是否成功与提示"。
4. **DeepSeek API 模式完整调用全部调用集**：API 模式与内置模型共用同一工具调用循环——每轮把**全部调用集 schema** 发给 DeepSeek（`deepseek-chat` 非推理模型=关闭深度思考），Agent 实时回传数据、按返回调用集执行并把结果再发给模型；小AI 意图补全/危险拦截/密码解锁/动态合成在两种模式下完全一致。配置 `ai.use_builtin_model=false, use_deepseek_api=true` 并填 `api.deepseek_api_key` 即启用。

## 3.14 答非所问根治 + 宿主机操作必达（v3.8）

1. **宿主机操作必达（"给QQ号发消息/扩大窗口"等真正执行）**：
   - 新增「给 QQ 号发消息」调用规则：`给3909296166QQ号发送你好消息` → 自动识别 QQ 号（数字号段）为接收方、app 默认为 QQ、正文智能清洗（"送你好消息"→"你好"），直接执行 `app_control.send_message` 并在控制板渲染/提示；
   - 窗口管理意图补齐 `扩大`（最大化/放大/扩大/铺满窗口）→ `panel_control.maximize`，前端丝滑放大动画。
2. **答非所问根除（三层防线）**：
   - 工具结果回合一律**确定性模板**总结（按最近工具名生成，回答必与所问相关），不交给模型续写；
   - 用户回合三分支：操作类请求（含意图落空）→ 确定性模板；纯闲聊（问候/自我介绍/感谢）→ 才交给独家大模型 NeuraLM 生成；未知意图 → 模板引导（"我可以帮你完成几乎任何宿主机操作…"）——绝不出现"好的，正在大型的最新信"这类残缺续写；
   - NeuraLM 生成过质量门（长度/中文/残缺语料检测），劣质输出自动回退模板。
3. **天气数据修复**：`None`/字符串"None"/空值统一归一为 `--℃`，城市缺失显示"本地"，温度/体感/风速各字段独立容错（实测真实联网输出 `已为你查询 宜昌 今日天气：大部晴朗 温度 28.7℃…`）。
4. **联网搜索容错**：并发双通道（DuckDuckGo/Bing）失败后**串行兜底重试**一次全部通道；失败文案明确（"已自动重试全部通道仍失败；请稍后重试，或换一个更具体的关键词"），杜绝超时后无意义续写。

## 3.15 应用定位器 + 知识问答 + 文案标点（v3.9）

1. **应用启动不再触发系统"找不到文件"弹窗**：`app_control.launch` 与发消息启动应用前，先经**跨平台应用定位器**定位真实可执行文件——Windows（环境 PATH → 注册表 `App Paths` → 常见安装目录扫描 → 开始菜单 `.lnk` 快捷方式解析）、macOS（`/Applications/*.app`）、Linux（PATH → 常见目录 → `.desktop` 的 `Exec` 解析）。找不到时**返回友好失败**（红色控制板窗口+提示"未找到「QQ」的可执行程序，已尝试…可配置 `ai.app_paths`"），不再把裸应用名交给 shell 触发 Windows 报错弹窗。
2. **知识问答不再答非所问**：`BTC是什么/什么是区块链/为什么…/怎么…/解释…/区别…` 等知识型问题 → 自动进入**联网搜索**（web_search 查询原文并整理到控制板信息窗口），不再把"我可以帮你完成几乎任何宿主机操作…"的功能引导当作回答；同时排除"打开/删除/写代码/股票/天气/文件/窗口"等操作类表达，不抢占原有意图。
3. **失败文案标点归一**：工具失败总结去除尾部重复句号（"关键词。。可换个说法" → "关键词。可换个说法"）。

## 3.16 系统信息窗口修复 + 消息理解增强（v3.10）

1. **系统信息窗口不再显示 HTML 源码**：前端 `renderInfo` 之前对整个生成的 kv HTML 再转义一次，导致 `<div class="kv-row">…` 以源码文本显示；现改为**仅转义键/值文本**，HTML 结构正常渲染，系统信息（os/系统/硬件/存储/内存/磁盘/Python/主目录）以清晰的键值行展示。
2. **QQ 消息理解增强（两种格式 + 5 种变体）**：`给QQ号3909296166发送消息“你好”`、`给3909296166QQ号发送你好消息`、`给123456789发消息：晚上一起吃饭` 等全部识别为 `app_control.send_message`（app=QQ, to=QQ号, text=正文），正文智能清洗（去"发送/送/消息"前后缀与引号）。
3. **闲聊判定防误伤**：用户回合分流改为**操作类优先**——"给QQ号…你好"这类内容里带"你好"的操作请求不会再被当作闲聊交给 NeuraLM（此前会产生"用。支持加放的工具可以把多个文件压成ZIP压"这类残缺续写），一律走确定性模板。
4. **语言理解增强**：无意图操作请求的提示语按语义分 12 类（天气/系统信息/进程/文件/编程/发消息/软件/窗口/搜索/删除/预览/股票），回复必与用户所说相关，不再笼统"功能列表"。

## 3.17 窗口自由缩放 + 查找文件 + 拦截消息变红 + 语言理解再升级（v3.11）

1. **窗口自由缩放（像《极限审判》的 AI 一样自由调整控制板窗口）**：新增 `panel_control.resize` 调用集与前端丝滑缩放动画——`缩小窗口 / 稍微缩小一点 / 将窗口稍微缩小一点 / 放大一点窗口 / 稍微放大一点` 全部识别并执行；"放大窗口/最大化窗口"仍为最大化；程度词（一点/稍微/再）自动区分最大化与缩放；"把字体缩小/把图片放大一点"等非窗口对象不误抢。
2. **查找文件调用集（新 `find_file`）**：`查找所有名为run.py的文件 / 找出桌面的图片` → 在指定根目录（默认主目录）内按文件名跨平台检索（自动跳过系统/缓存/隐藏目录，限时 20 秒），结果在控制板文件窗口展示。
3. **小AI 拦截的那一次消息变红**：文本级拦截（格式化C盘/删根路径等）与工具级恶意拦截（`删除 /`）的回复，`message_done.blocked=true` → 前端**仅该条气泡整条变红**（红色边框+红字+警示图标+红光晕），其余消息样式不变；正常执行的消息不变红。
4. **语言理解与执行能力再升级**：
   - QQ 消息新增格式 `给QQ号为3909296166发送消息"你好"`（QQ号前带"为/是"）；
   - 操作词表补全（发送/消息/给/窗口/缩小/放大/查找/搜索文件/进程/系统…），意图落空时不会误入闲聊答非所问；
   - 闲聊判定改为**问候词句首限定**（内容里的"你好"不再误判）+ 征询类（你觉得/行吗/怎么样/建议/怎么办）改为**联网搜索并整理信息**（真实执行，不再由模型硬编残缺语料）；
   - 纯问候/自我介绍（你好/你是谁）才交给独家大模型 NeuraLM 生成。
5. **小AI 调用集权力（保留）**：已存在调用集直接执行；不存在则小AI 理解+联网+生成+安全审查后动态新增（`synthesize_tool`），危险调用集直接拦截不生成。

## 3.18 依赖询问安装 + 真实系统利用率 + 复合推理 + 持久记忆 + AI 自动整理（v3.12）

1. **执行缺依赖 → 控制板弹窗询问是否安装**：运行代码/命令缺 Python 模块（ModuleNotFoundError）时，控制板弹【是否安装】确认窗口（非系统弹窗）；选【安装】→ pip 自动安装并弹电影级流光**进度条窗口**实时显示，完成后自动重试原操作；选【取消】→ 取消安装并取消任务。
2. **真实系统资源利用率（不再只显示固定系统信息）**：新增 `system_stats` 调用集——纯 stdlib 跨平台真实采样 **CPU 利用率% / 内存利用率%(总/已用MB) / 磁盘利用率%(总/已用/剩余GB)**；`查看CPU利用率 / 内存占用多少 / 磁盘使用情况` 全部真实采集，不再是 `system_info` 固定语法。
3. **内置大模型复合推理（不是 if 器）**：`明天我要去上海旅游，天气怎么样 / 我明天要去北京玩` → 自动分解为 **天气查询 + 攻略搜索** 两条调用集真实执行，再由 NeuraLM 推理**整理信息、组织语言、按天气数据推导出行建议**（带伞/加外套/防晒等由温度与天气条件推导，非硬编码）。
4. **持久记忆与项目记忆**：事实记忆 + **项目记忆**（"我在D:/work写个项目叫XX"自动记录）+ **最近访问路径**（每次查看/读取/写文件自动记录，跨会话持久），注入上下文供后续使用。
5. **AI 自动整理控制板窗口**：跨回合统计窗口数，≥4 个时 AI 自主平铺网格布局（60 秒冷却），≥7 个时自动收起最早的信息窗口，始终让用户看得清楚；用户手动关闭窗口计数自动递减。
6. **DeepSeek API 通道全能力同步**：CPU 利用率/旅行复合推理/缩放窗口/拦截红标/缺依赖询问全部在 API 模式共享生效（回归 4/4）。
7. **天气简体 + 真实 + 外地**：Open-Meteo 实时真实数据（非假报）；返回文本统一**简体化**（繁简替换表覆盖气象/城市/行政区常用字）；`上海天气/北京天气` 等外地城市按指定城市真实查询（不显示本地）。

## 3.19 联网 5 通道修复 + 实时命令终端 + 超强上下文记忆与语言理解（v3.13）

1. **联网搜索修复（图1 超时红窗）**：`web_search` 升级为 **5 通道容错搜索**——必应中国 `cn.bing.com`、百度、搜狗（国内可达，优先串行单连避免窄带宽拖垮）+ DuckDuckGo + 必应国际；国内通道优先串行、国际通道并行兜底、全失败再串行重试；任一通道成功立即返回。配合 3 个新解析器（h2 带 class 属性的真实页面结构），实测返回真实结果，不再超时红窗。
2. **AI 实时执行命令（控制板实时命令终端）**：控制板左上角新增 **⌘ 命令** 按钮 → 打开「实时命令终端」HOLO 窗口（输入框 + 流式输出区）；用户在控制板直接输入命令执行，输出**逐行流式追加**（电影级终端感），支持绝对路径命令按 basename 白名单判定（`/opt/.../python3` 等价 `python3`）。
3. **超强上下文记忆与语言理解**（所有场景生效，不只是天气）：
   - **语病自动修正**：`宜昌是天气`→自动归一为 `宜昌天气` 并成功查询；`查看下C盘文件 / 打开一下QQ / 帮我看看我的家目录` 等口语冗余自动修正后**直接执行**；
   - **失败纠错回路**：上次因城市口误失败（如 `宜昌是市` 查不到）→ 本次同样口误**自动修正为上次意图城市**并给出真实天气；上次失败的城市 → 说 `宜昌市天气` 时**理解上下文补全**直接出结果；
   - **上下文重试**：失败后说 `再试一次 / 重新查询 / 换个说法` → 自动重试**最近失败的操作**；`换成上海再查一次 / 换成深圳` → 替换城市参数重试天气类失败；
   - **会话级推送器并发安全**：修复多会话并行时 emitter 竞态崩溃（每会话独立绑定推送器）。
4. **DeepSeek API 通道全能力同步**：5 通道搜索 / 实时命令终端 / 上下文纠错与重试 / 拦截红标在 API 模式全部共享生效（回归 4/4）。

## 3.19.1 修复：发消息失效 + 界面异常（v3.13.1）

- **根因**：`app.js` 在 `const App = (() => {...})()` 的 IIFE 内部直接写 `App.currentSid = ...`，触碰 const 的暂时性死区（TDZ），整段脚本加载即抛 ReferenceError → `DOMContentLoaded` 监听不注册 → 发送按钮/回车无事件、会话与快捷指令不渲染、界面交互全部失效。
- **修复**：删除 IIFE 内对 `App` 的引用，改为在 IIFE 返回对象中导出 `currentSid: () => currentSid`（控制板命令窗口 `App.currentSid()` 调用不受影响）。
- **验证**：真实浏览器（1920×993）实测——输入"今天天气怎么样"回车 → 用户气泡出现、控制板弹出「天气预报」窗口（含 —/□/✕ 控制钮）、AI 回复正常；快捷指令 chips、新会话按钮、⌘ 命令按钮全部可交互。

## 3.20 搜索答非所问修复 + 股票真实趋势图/通用图表 + 国家级旅行识别（v3.14）

- **搜索关键词规范化**：`web.py::_clean_search_query` 迭代剥壳（时间词→意愿词→方向动词→查看看→疑问/语气词→"的X"连接词→标点），
  「明天我要去天津旅游」→「天津旅游」、「美国的首都在哪儿」→「美国首都」、「去美国旅游」→「美国旅游」，彻底修复搜出「明天（鲁迅小说）」类无关结果。
- **知识问答**：mini_ai 正则扩展（首都/首府/省会/在哪儿/位于/是谁/哪国/人口/面积/历史/由来等），提问 → 干净关键词联网检索 → 整理成条目式回答（例：美国首都 → 华盛顿哥伦比亚特区，直接答出）。
- **国家级旅行识别**：旅游分支识别 60+ 国家名单，「我要去美国旅游」→ 天气用国家名（不再拼"美国市"查不到）+ 搜索「美国旅游攻略」；目的地攻略关键词清洗，天气真实（Open-Meteo，简体，多日）。
- **股票真实趋势图**：新调用集 `stock_chart`（腾讯行情日K，国内可达真实数据，A股/港股/美股名称或代码）→ 控制板「股票趋势图」窗口（canvas 折线+面积渐变+均线图例，科技幽蓝），
  `brain` 由真实数据推导趋势解读（MA5/MA20、区间涨跌、近5日方向）并给出建议；`chart` 通用图表调用集支持折线/柱状/饼图。
- **AI 自主构建可视化**：天气多日预报 ≥3 天自动追加「温度曲线」图表窗口；小AI 新增「画XX图/走势/K线」意图路由。
- **KeyError 'k' 修复**：`dynamic.py` generic 模板字典推导花括号未转义被 `str.format` 误解析 → 已双写转义，六模板 format+编译回归全过。
- **geocode 修复**：「天津市/上海市」等带行政后缀查询失败/歧义 → 去后缀优先 + 中国行政区结果优先。
- **模型通道容错**：股票/检索大 JSON 超 8000 截断导致总结落空 → 数据精简（points 仅日期+收盘）+ `_safe_json` raw_decode 容错。
- **验证**：全量回归 50 PASS；WS 冒烟 5/5（天津/美国旅游、美国首都、茅台/腾讯趋势图，工具+面板+回答相关性）；API(DeepSeek) 模式 4/4（天气/知识/股票/文件）；
  真实浏览器实测「给我画一下贵州茅台的股票趋势图」→ 控制板趋势图窗口渲染折线（刻度 1384.9/1325.1/1285.2、图例"茅台"）+ 完整建议文本。

## 4. Agent 架构

```
web/ (前端)  ←WebSocket→  server/main.py (FastAPI) →  agent/core.py (AgentCore)
                                                          │
                    ┌─────────────┬──────────────┬────────┴────────┐
                 brain.py      mini_ai.py      tools/registry.py  self_improver.py
              DeepSeek/Ollama  意图理解+调用集   完整工具调用集    自改进(回归防线)
              /引擎 三种后端     生成/参数补全/    文件/系统/联网/    + memory.py
                                 失败修复       编程/面板/打包      长期记忆
```

### 核心模块
- **agent/core.py** — 会话管理、工具调用循环（模型 → 工具 → 实时回传 → 循环）、代码自动调试闭环、自改进触发。
- **agent/brain.py** — 三后端大脑：DeepSeek API（流式 SSE、工具调用累积）、Ollama（流式 NDJSON）、内置引擎。
- **agent/mini_ai.py** — 内置**小型 AI**：负责理解用户操作、生成新的调用集（工具调用序列）、补全/校验参数、失败后建议修复；任何模式下都参与。
- **agent/tools/** — 调用集（注册表 + 15 个工具）：
  `list_directory / read_file / write_file / create_folder / package_download / run_command / system_info / open_app / get_time / calculator / get_weather(Open-Meteo) / web_search(DDG+Bing) / fetch_webpage / code_task / write_code_file / run_code / package_project / panel_popup / panel_update / panel_close / notify`
- **agent/self_improver.py** — 自我提升与改造，见下节。
- **agent/memory.py** — 长期记忆（记住用户偏好/目录/城市，后续自动使用）。
- **agent/safety.py** — 命令白名单/黑名单、路径约束、沙箱（超时/内存/输出上限）。

## 5. 自我改进 —— 为什么“不会改退化”

SelfImprover 只允许学习**规则/参数提示/记忆**，且每一条都过安全闸门：

```
工具失败 → 记录失败签名(tool+error_type) → 同签名失败≥2次
        → 生成候选规则 → ★ 回归测试(tests/regression.py) 必须全过
        → 通过: 自动备份当前状态(improvements_vN.json) → 激活规则(带版本号)
        → 不通过: 规则被拒绝(rejected_by_regression), 永不激活
```

- 回归测试覆盖：计算器、时间、文件读写、ZIP 打包往返、危险命令拦截、路径黑名单、意图识别、沙箱执行。
- 任何版本可回滚：`python run.py --rollback 2`
- **核心工具代码对自改进不可写** —— 模型/规则永远不会自动改写工具实现本身。

## 6. 安全边界（重要）

- `run_command` 只允许白名单命令（`ls/cat/echo/ping/python/git…`），黑名单与危险正则（`rm -rf /`、`format`、`shutdown`、shell 元字符等）一律拒绝并提示原因。
- 路径执行前经黑名单检查（默认禁止 `/etc/shadow` 等敏感文件）。
- 代码在沙箱中运行：超时（默认 30s）、内存上限（默认 512MB）、输出截断；可选 firejail 网络隔离。
- 所有沙箱执行与系统命令都有完整日志（`system/logs/tool_logs.jsonl`）。

## 6.5 小AI 动态调用集系统（v2.0 核心）

**设计目标**：用户提出任何合法操作，只要现有调用集没有对应能力，小AI 就为 Agent **新增/升级调用集**并立即执行——永不简化、永不模拟。

**判定流程（三路）**
1. 调用命令**已存在**（别名表/名称包含/描述模糊检索命中）→ 不新增调用集，Agent 直接执行；
2. 调用命令**危险/恶意**（删除/格式化/提权/后门/木马/病毒/挖矿/绕过安全/监控隐私等 19 组高危关键词）→ 小AI 直接拦截，绝不生成；
3. 调用命令**不存在** → 小AI 理解需求 → 联网检索参考（web_search）→ 思考生成代码（优先 DeepSeek/Ollama 大模型编程，失败回退内置模板库：统计/HTTP/文件统计/日期/CSV/通用）→ **五层安全审查** → 注册 + 版本化持久化 → 立即用调用参数试执行并把结果回显。

**五层安全审查（辨别能力的执行层）**
| 层 | 检查 | 说明 |
|---|---|---|
| L1 | 意图级拦截 | 需求文本命中危险关键词即拒 |
| L2 | AST 导入白名单 | 只允许 json/re/math/datetime/os.path/httpx 等安全库；拒绝 subprocess/ctypes/socket/pickle/paramiko/sys 等 |
| L3 | 危险模式扫描 | os.system/os.popen/eval/exec/__import__/rm -rf/format/dd 等正则 |
| L4 | 破坏性操作拦截 | os.remove/shutil.rmtree/写文件/改名/截断/杀进程；os 属性白名单 |
| L5 | 行为试运行 | 纯计算类工具用哑上下文 6s 超时试跑，崩溃即拒 |

**其他特性**
- 自定义调用集持久化在 `system/custom_tools/<name>/`（tool.py + tool.json + _backups 历史版本），重启自动加载；
- 自定义调用集**连续失败 2 次** → 小AI 自动理解错误并升级该调用集（自动升级 vN+1）；
- 调用集管理：`GET/DELETE /api/tools/{name}`，命令行 `python run.py --list-tools / --remove-tool <name>`；
- 小AI 的意图引擎新增 `blocked`（安全拦截）与 `synthesize`（动态合成）两个动作；
- 前端新增 `tool_synthesized` 事件：控制板弹出新调用集代码窗口 + 成功通知。

## 7. 界面功能速览

| 位置 | 功能 |
|---|---|
| 顶部会话栏 | 新建 / 切换 / 删除会话 |
| 左侧控制板 | AI 结果的图形化弹窗：文件列表、天气(表格+温度曲线图)、代码编辑器、运行过程日志、搜索表格、下载窗口、**小AI 工具工厂进度窗(synth_flow)**；窗口可**拖动/最小化/最大化/关闭**，底部有窗口坞 |
| 右侧对话框 | 用户指令输入、AI 文本流式输出、工具调用卡片实时状态(执行中/成功/失败/自动重试) |
| 输入区 | 常用指令快捷 chips；Enter 发送，Shift+Enter 换行 |

**典型指令**：`查看我的家目录文件`、`今天天气怎么样`、`帮我写一个计算器程序`（自动运行→若失败自动调试→打包下载）、`搜索 人工智能最新进展`、`我的电脑配置`、`帮我求一下 5 和 8 的平均值`（无现成调用集 → 小AI 动态合成并执行）、`把系统文件全部删除`（被小AI 安全辨别拦截）。

## 8. 常见问题

- **报“Ollama 不可用 → 降级到内置引擎”**：说明本机没有 Ollama 或模型未拉取。`ollama pull qwen2.5:7b` 后重启。
- **DeepSeek 模式报 Key 未配置**：`config.json` → `ai.api.deepseek_api_key` 填入 Key，且 `use_builtin_model=false`。
- **DeepSeek API 模式下调用集如何工作**：Agent 把全部调用集 schema 完整发给 DeepSeek（`disable_reasoning=true` 关闭深度思考），工具调用结果实时回流；模型返回不存在的调用名时，小AI 自动判定合成或拦截。
- **命令被拒绝**：白名单在 `permissions.allowed_commands`，可自行按需添加（不建议放开破坏性命令）。
- **端口被占用**：`python run.py --port 9000`。
- **只想测试自改进防线**：`python run.py --regression`（v2.0 已扩到 50 项，覆盖动态合成/审查/拦截）。
- **查看当前全部调用集**：`python run.py --list-tools`。

## 9. 目录结构

```
NeuraAgent/
├── config.json / config.example.json   # 配置(模型开关/权限/主题/动态调用集)
├── run.py                              # 入口(--regression/--rollback/--list-tools/--remove-tool)
├── requirements.txt
├── agent/                              # Agent 核心
│   ├── core.py  brain.py  mini_ai.py
│   ├── memory.py  self_improver.py  safety.py  utils.py
│   └── tools/                          # 调用集(注册表+全部工具+动态工厂)
│       └── dynamic.py                  # 小AI 工具工厂: 五层审查 + 合成 + 持久化
├── server/                             # FastAPI + WebSocket + 下载 + /api/tools
├── web/                                # 前端(科技幽蓝透明)
├── system/                             # 会话/记忆/改进状态/日志/备份/custom_tools
├── workspace/                          # 代码工作区(按会话隔离)
└── tests/regression.py                 # 自改进安全闸门(50 项断言)
```

## 3.21 QQ 真实 GUI 发送 + 国家天气识别 + AI 绘画 + 通用安装 + 实时任务 + 搜索相关性过滤（v3.15）

- **QQ/微信真实发送（Windows）**：`_gui_send_msg` 定位应用主窗 → 搜索接收人 → 进入会话 → 聚焦输入 → 回车 → 自动截图证据（控制板图片窗口），失败自动降级全局键入。
- **国家天气识别**：60+ 国家表，`_pick_city` 国家优先（"美国天气"→"美国"，不再拼成"美国市"），失败纠错同步国家保护。
- **AI 绘画 `draw_image`**：内置确定性 SVG 绘画引擎（动物/风景/科技/城市/通用，科技幽蓝风），控制板图片预览 + `~/NEURA绘画/neura_*.svg` 文件保存与下载。
- **通用安装 `install_package`**：12 种包管理器命令安装（实时进度窗口）；软件/GUI 包联网搜官方下载源（白名单域名监管）→ 下载 → 启动安装向导 → 自动点击（小AI 全程监管）。
- **实时任务 `monitor_task`**：持续采样（CPU/内存/磁盘或任意命令），控制板命令窗口实时刷新，30 轮上限可关窗停止。
- **搜索相关性过滤**：`_rank_results` 关键词命中打分 + URL/标题去重，只保留与问题相关的核心结果（根治"搜出鲁迅《明天》"类跑题）。
- **DeepSeek API 通道共享全部新能力**（工具注册层统一，双模式回归通过）。

## 3.22 安装进度实时化 + 关闭窗口根治 + 股票建议上下文 + 搜索净化 + 空间 HUD（v3.16）

- **安装进度全程实时**：命令安装逐行推进；图形化安装按阶段增量（检索→流式下载按字节 45→85%→启动→自动点击），任何失败推到 100% 失败态并给明确文案，绝不卡 0%；搜索 10s 收敛不死锁。
- **关闭所有窗口根治**：前端 `closedFor` 标记——关闭后禁止被 panel_update 自动重建（此前 monitor 推送会复活已关窗口）；clearAll 同步直删；"都关掉/统统关闭/全关"等变体词全部识别。
- **股票建议上下文**："你觉得可以买这个股票吗"无标的 → 不搜索、直接给建议；上下文最近提到的代码（如 688836）自动关联做真实趋势图+数据面参考；"贵州茅台股票行情"等明确标的正常净化查询。
- **搜索净化**：`_clean_search_query` 剥"你觉得/可以买/这个/那个"等口语壳，"你觉得可以买这个股票吗"→"股票"；建议类提问不再搜出"你(汉字)百科"。
- **QQ 窗口定位增强**：pywinauto UIA + psutil 进程 PID → win32gui EnumWindows 关联可见窗口（兼容新版 QQ/微信标题）+ 前台窗口兜底。
- **Windows 内存修复**：GlobalMemoryStatusEx 初始化 dwLength，内存不再显示 0。
- **空间 HUD 界面**：深空渐变 + 星点闪烁 + 六边形网格漂移 + 扫描线 + 暗角 + HUD 角标 + 窗口内发光渐变（幽蓝空间感透明，清爽不过饱和）。
- **自动上板去重**：已自建进度/命令/绘画窗口的工具不再重复弹"0% 安装中"误导窗口。

## 3.22 v3.16 回复错位根治 + 安装进度修复 + 关闭全部窗口 + 内存采集 + QQ 定位增强 + HUD 界面硬核化

- **回复错位根治**：`_summarize_tool_result` 只取**本轮工具链**（末尾反向遇 user/assistant 即停），工具链内部搜索失败不再落到旧轮搜索总结（修复"安装github后回复却是旧股票检索"）。
- **股票建议**："你觉得可以买这个股票吗"类无标的提问直接给数据面建议（不再搜出"你"字百科）；有明确标的才搜真实行情。
- **安装进度不卡 0%**：命令安装有输出即推进进度（每行 +2%，下载/解压/配置各阶段加速），3 秒无输出也强制推进并继续等待，绝不静止在 0%。
- **关闭所有窗口**：前端 `panel_control close` 未指定窗口 ID 时清空全部弹窗（"关闭窗口"即关全部）；"关闭所有窗口"意图正确路由 close_all。
- **内存采集**：Windows GlobalMemoryStatusEx 显式签名 + psutil + /proc/meminfo 多通道兜底，不再显示 total 0。
- **QQ 真实发送增强**：主窗匹配放宽（排除设置/帮助/登录类标题）+ 系统托盘图标激活唤出主窗 + 消息输入框控件定位点击聚焦。
- **界面 HUD 硬核化**：全局圆角收紧（14→4px）、圆形元素改菱形/斜切、按钮/面板 HUD 折角 clip-path、等宽数据字体、聚焦光静态化去呼吸、进度条单色幽蓝数据流、emoji 图标全部替换为几何字符（▣▮◆▲▸▦），深空星点+六边形网格+扫描线+暗角 HUD 面板。

## 3.23 v3.17 修复 DeepSeek 流式响应未读错误(ResponseNotRead)

- **根因**：httpx `client.stream()` 流式模式下，HTTP 状态错误(如 401)分支直接访问 `e.response.text` 而未先 `read()`，抛 `httpx.ResponseNotRead`（"Attempted to access streaming response content, without having called read()"），被 `except Exception` 吞成"连接失败"乱码。
- **修复**：DeepSeek / Ollama / OpenAI 兼容三处错误分支统一先 `await e.response.aread()` 再取响应体，失败回退 `str(e)`。现在无效 Key/服务错误会清晰显示真实原因（如 "HTTP 401: Authentication Fails, key invalid"）。
- config.json 已写入 DeepSeek API Key（use_deepseek_api=true 时使用）。

## 3.24 v3.18 修复 DeepSeek HTTP 400 (消息结构规范化 + max_tokens 钳制)

- **400 根因**：长会话按字符预算截断时可能切断 assistant(tool_calls) 与 tool 结果的配对，产生孤立 tool 消息 / 孤立 tool_calls，DeepSeek 校验失败返回 HTTP 400。
- **修复**：新增 `normalize_messages_for_api`（utils.py）——丢弃孤立 tool 消息、移除末尾无回复的 tool_calls、结尾非 tool 消息；DeepSeek/Ollama/OpenAI 三条通道统一接入。
- **max_tokens 钳制**：`max_tokens` 上限钳制为 4096（DeepSeek 官方兼容值，避免 8192 在带 tools 请求下触发 400）。
- **错误诊断**：HTTP 错误分支在响应体为空时附提示"请检查 config.json 的 ai.api 配置(model/max_tokens/api_key)"。

## 3.25 v3.19 任意 AI 模型 API 接入 + 400 根治 + 小AI 操作级监管

- **DeepSeek 400 根治**：tool 消息不再携带 `name` 等多余字段（DeepSeek 严格校验多余字段返回 400），normalize_messages_for_api 严格字段化（system/user/assistant/tool 只保留允许字段），并保留配对完整的末尾 tool 消息。
- **任意 AI 模型 API 接入**：config.json 新增 `ai.api_provider`（deepseek|openai|doubao|yuanbao|custom）+ `ai.providers` 预置 ChatGPT/OpenAI、豆包(火山方舟)、腾讯元宝三套配置（enabled=true 即启用）；`ai.api.custom` 支持用户自定义任意厂商 API——format="openai"（OpenAI 兼容流式+自动带工具）或 format="template"（用户自写请求模板, 占位符 {messages}/{tools}/{model}/{api_key} + response_text_path/response_tools_path 点路径解析）。
- **API 模式放开 AI 自主**：Agent 不对 AI 的回答/操作做严格约束（回复风格、思考、推理完全自主），系统提示改为"工具使用教学"：列出全部调用集、教 AI 如何调用工具、如何通过 synthesize_tool(update_name) 增加/修改/升级调用集。
- **小AI 安全与权限监管**：操作级监管（security.classify_operation 基于工具+参数分级：恶意直接拦截红窗、高危需系统登录密码确认）+ 消息级辨别（detect_dangerous_request）+ 调用集增改审查（五层安全审查, 恶意增改拦截, 修改同名覆盖版本+1）。
- Brain 互斥逻辑兼容新模式：api_provider/custom 模式下不再被"未选模式强制内置"误伤。

## 3.26 v3.20 config 顶层键序规范化 + 多 AI 只选一

- config.json 顶层键序固定为: server → ai → agent → permissions → security → panel → network; 所有 AI 选项(开关/内置/API/预置 provider/自定义)统一集中在顶部 ai 段, 开关字段(use_builtin_model / use_deepseek_api)位于 ai 段最前。
- 多 AI 只选一: Brain 互斥强化——use_builtin_model=true 时忽略一切外部通道; 外部多通道(DeepSeek/provider/custom)同时启用时按优先级只启用一个并打印警告。

## 3.26 v3.20 AI 选项集中 + 多选一强互斥

- 所有 AI 模型选项统一集中在 config.json 顶部 `ai` 段(紧随 server 之后): use_builtin_model(内置NeuraLM) / use_deepseek_api(DeepSeek) / api_provider(openai|doubao|yuanbao) / api.custom(自定义API)。
- 新增 `ai.mode` 唯一模式真源(builtin|deepseek|openai|doubao|yuanbao|custom): `resolve_ai_mode` 启动时把全部开关规范化为"恰好一个为 true"(如 deepseek=true 则其他 AI 选项全 false), 并写回 config.json 持久化; 兼容旧开关推断。
- run.py 启动校验 + Brain 构造双保险; 模式打印适配全部通道。

## 3.27 v3.21 AI 启用选项统一置于 config.json 最顶部

- config.json 最顶部(server 之前)统一放置全部 AI 启用开关:
  "use_builtin_model": true, "use_deepseek_api": false, "api_provider": "deepseek", "custom_api_enabled": false
  ai 段保留详细配置(内置权重/API Key/端点/模型名/providers 明细)。
- 多选一强互斥: 任一启用开关为 true 其余自动置 false(deepseek=true 则 use_builtin_model=false 等),
  冲突时按 内置>DeepSeek>预置通道>自定义 优先级取一; 规范化结果写回 config.json 持久化。
- resolve_ai_mode 顶层开关优先, 兼容旧结构(开关在 ai 段时自动提升到顶层), Brain 仍读 ai 段。

## 3.28 v3.22 消除重复开关: AI 启用选项唯一存在于 config.json 顶层

- config.json 顶层(server 之前)唯一保留全部 AI 启用开关:
  "use_builtin_model": true, "use_deepseek_api": false, "api_provider": "deepseek", "custom_api_enabled": false
- ai 段不再包含任何开关(use_builtin_model/use_deepseek_api/api_provider/custom_api_enabled/mode 全部移除),
  只保留详细配置 builtin/api/providers; 旧配置残留的 ai 段开关在启动时自动迁移到顶层并清理。
- resolve_ai_mode 只写顶层(唯一真源); Brain/run.py 统一读顶层; 多选一互斥保持不变。

## 3.29 v3.23 修复 Windows 启动 NameError: cfg 未定义

- brain.py `_init` 内 `provider = cfg.get("api_provider")` 误用裸 `cfg`(该作用域无此变量, 仅 self.cfg), Windows 启动即崩。
- 修复为 `self.cfg.get("api_provider")`; 四通道(内置/deepseek/doubao/custom)构造实测通过。

## 3.30 v3.24 修复 DeepSeek 400 + 控制板用户点击交互 + 调用集只增不减 + 操作放权

- **修复 DeepSeek HTTP 400(tool_calls 后缺 tool 回复)**: `agent/utils.py::normalize_messages_for_api` 重写为两遍法——
  首遍过滤同时跟踪全部 tool_call_id, 末尾用 replied 集合(全文实际 tool 回复 id)只保留"已收到回复"的 tool_calls, 未回复声明剔除;
  user/system/assistant/tool 严格字段化, 完整配对末尾 tool 保留; 单测 3 项全过。
  `agent/core.py` 工具链重构: 循环体提取为 `_run_tool_call` 方法, 循环内 try/await/except——
  工具链任意异常不中断循环并补配对 tool 消息(avoid 400), 用户取消依赖安装返回 False 终止本轮; 回归 50/50 + WS 冒烟全绿。
- **控制板用户点击交互(不再是纯展示)**: `web/js/panel.js` 文件行可点击(data-act)——
  目录行点击进入子目录, 文件行点击预览/打开; 事件委托发送 `panel_action` 至后端;
  `server/main.py` panel_action 分支接入 `core.handle_panel_action`(list_dir/preview_file/run_cmd),
  复用调用集与上板逻辑实时刷新控制板窗口; 同名同类型窗口自动复用(避免重复开窗)。
- **调用集"只增不减不弱化"监管**: `agent/tools/dynamic.py::synthesize_and_register` ——
  内置调用集不可被覆盖(拒绝并提示用新名称); 升级自定义调用集时新参数集必须为旧参数超集(删除参数=能力弱化拦截), 只允许增。
- **小AI 加强 + 操作放权**: `agent/security.py` 移除过宽 `sudo/su` 全拦(普通 sudo 命令放行, 仅拦截提权修改组合);
  `kill -9` 收窄为系统根/守护进程恶意(普通进程降为高危密码确认); 新增 8 类恶意特征(凭据/密钥窃取、数据外泄、
  键盘记录/剪贴板窃取、勒索加密、凭据转储、入侵渗透、口令爆破、钓鱼仿冒、清除痕迹);
  config.json 命令白名单 37→75(新增 curl/wget/mkdir/cp/mv/touch/head/tail/grep/awk/sed/env/export/which/tar/unzip/zip/
  make/cmake/docker/java/go/rustc/cargo/sqlite3/redis-cli/chmod/chown/kill/psql/mysql/npx/pnpm/yarn/composer/gradle/mvn)。
- 其余全部不变: 独家 NeuraLM 内置大模型 + DeepSeek 等多 API 通道全能力共享、输入框悬浮固定底部、窗口丝滑可拖/缩放/关闭/最大化/自主整理、小AI 拦截红气泡、高危管理员密码解锁、天气简体真实、持久记忆、联网搜索总结、股票趋势图/绘画/软件操控/进程管理。

## 3.31 v3.25 赋予 AI 修改 Agent 能力: 自修复回路 + 小AI 实时监管(只允许修复性修改)

- **AI 可直接修改 Agent**: 新增调用集 `agent_repair`(提交修复补丁 file/old/new + reason)与
  `read_agent_file`(读取 Agent 源码定位问题)。当某个调用集/命令执行报错且判定为 Agent 自身代码缺陷时,
  内置 AI 与 DeepSeek/多 API 通道的 AI 都能调用 agent_repair 直接修改 Agent 代码, 修改后热重载立即生效并重试原操作。
- **自修复闭环**(agent/core.py): `_maybe_repair_agent` 失败钩子——工具报错(exec/module/import/type/attr/syntax 等
  可修复类型) → 控制板提示"正在由 AI 自修复(小AI 实时监管)" → 大模型分析报错并产出修复补丁
  (内置 NeuraLM / DeepSeek / 多 API 通道均走 brain.chat) → agent_repair 提交 → 小AI 监管审查 →
  应用/重试; 规则引擎有限 auto 修复兜底; 每回合最多 max_agent_repair_rounds=1 次, 防无限循环。
- **热重载**: `rebuild_registry()` 重建内置工具注册表 + 重载自定义调用集(持久化), 修复后新代码立即可用。
- **小AI 实时监管**(agent/security.py::review_agent_patch): 只允许修复性修改——
  ① 受保护文件 agent/security.py / config.json / agent/mini_ai.py 禁止直接修改(安全核心/权限边界);
  ② system/ workspace/ server/downloads/ 禁止修改(记忆/沙箱隔离);
  ③ 恶意意图特征拦截(关闭安全防护/禁用杀毒/绕过白名单/后门/挖矿/勒索/窃取/键盘记录/清除痕迹/提权等);
  ④ 补丁新增代码引入危险调用(subprocess/os.system/eval/exec/socket/__import__ 等)拦截;
  ⑤ 应用前备份到 system/backups/agent_patches/, .py 语法验证失败自动回滚, 大规模删除(疑似弱化能力)拦截。
- config.json agent 段新增: agent_repair_enabled / max_agent_repair_rounds; 系统提示补充自修复能力说明。
- 其余全部不变: 独家 NeuraLM + 多 API 通道全能力共享、控制板用户点击交互、调用集只增不减不弱化、
  白名单 75 命令、输入框悬浮固定底部、窗口丝滑可拖/缩放/关闭/最大化/自主整理、小AI 拦截红气泡、
  高危管理员密码解锁、天气简体真实、持久记忆、联网搜索总结、股票趋势图/绘画/软件操控/进程管理。

## 3.32 v3.26 去除调用集中转: AI 直接操控 Agent + 小AI 监管全面加强

- **去除调用集中转**: `agent/core.py::_run_tool_call` 移除"小AI 判断调用集是否存在 -> 不存在则合成注册新调用集"
  的中间层(不再自动 synthesize 并注册)。AI(内置 NeuraLM / DeepSeek / 多 API 通道)直接操控 Agent:
  直接指定操作名+参数, Agent 直接执行并把真实结果实时返回, 全程无"调用集注册"环节。
- **直接操控通道** `_direct_act`: 能力清单外操作不再注册调用集——
  ① 小AI 意图解析(mini_ai.interpret_action: 名称模糊匹配 + 中文/英文操作表述关键词映射,
  如"查看文件夹"→list_directory、"今天天气"→get_weather、"股票趋势图"→stock_chart);
  ② 小AI 加强监管(意图文本级, 不只工具名+参数): 恶意直接拦截(红色窗口), 高危需系统登录密码;
  ③ 可映射则直通现有能力直接执行; ④ 无法映射则提示 AI 直接用 run_code/run_command 或现有能力
  组合实现该操作(小AI 对其实现实时监管)。全程不注册任何新调用集。
- **小AI 监管全面加强**(agent/security.py):
  - 新增 `classify_llm_action`: 对 AI 直接操控的【操作意图文本】做恶意/高危检测, 复用全部
    恶意/高危特征表 + 新增中文恶意意图表(格式化/清空/删除盘符级全部内容/关闭安全防护/绕过验证/
    窃取凭据/注入后门/口令爆破/提权渗透);
  - 执行层监管不变(每个操作都过 classify_operation: 恶意拦截 / 高危密码解锁 / 正常执行)。
- **系统提示重写**: "你直接操控 Agent, 不存在中间调用集"; 能力清单外直接用执行能力实现;
  可选保留 synthesize_tool(仅当想沉淀可复用能力时, 非必经之路)。config.json system_prompt 同步重写。
- 其余全部不变: 独家 NeuraLM + 多 API 通道全能力共享、自修复回路(agent_repair)、控制板用户点击交互、
  调用集只增不减不弱化(仅作用于可选能力沉淀)、白名单 75 命令、输入框悬浮固定底部、窗口丝滑、
  小AI 拦截红气泡、高危管理员密码解锁、天气简体真实、持久记忆、联网搜索总结、股票趋势图/绘画/软件操控/进程管理。

## 3.33 v3.27 AI 直接控制 Agent: 无小AI 中转, 小AI 只负责监管

- **AI 直接控制, 无小AI 中转**: `agent/core.py::_direct_act` 移除小AI 的意图解析/能力合成/决策中转——
  AI 的每个操作指令都由 Agent 直接执行。小AI 不再替 AI 理解需求/决定怎么做, 只做安全监管。
- **不受能力清单短缺限制**: 能力清单没有的能力, AI 依然直接控制 Agent 完成——
  ① 直接调用 run_code 提供 Python 实现代码(小AI 代码级监管后沙箱执行); ② 直接调用 run_command 提供命令;
  ③ 组合现有能力; ④ 调用 agent_repair 直接修改 Agent 代码扩展/实现能力。AI 拥有 Agent 的直接控制权。
- **小AI 只监管(不中转)**: 每个直接操作过三道监管——意图文本级(classify_llm_action: 恶意拦截/高危需
  系统登录密码)、执行级(classify_operation)、代码级(沙箱审查); 全程不注册任何调用集。
- **系统提示重写**: "你直接控制 Agent——不存在任何中间调用集, 也不需要小AI 替你做意图解析/能力合成;
  你拥有 Agent 的直接控制权, 不受能力清单短缺限制; 小AI 只负责安全监管"。config.json system_prompt 同步。
- 其余全部不变: 独家 NeuraLM + 多 API 通道全能力共享、自修复回路(agent_repair)、控制板用户点击交互、
  白名单 75 命令、输入框悬浮固定底部、窗口丝滑、小AI 拦截红气泡、高危管理员密码解锁、天气简体真实、
  持久记忆、联网搜索总结、股票趋势图/绘画/软件操控/进程管理。

## 3.34 v3.28 修复 DeepSeek 真实模式 400: tool_calls 配对全量修正(多轮残留真凶)

- **根因**: `agent/utils.py::normalize_messages_for_api` 原实现只修正【最靠近末尾】的一条
  assistant(tool_calls)(循环带 break)。多轮会话中, 早期轮次若其 tool 回复被上下文裁剪
  (trim_messages_for_context 按字符预算从尾部逆序截断) 或执行异常移除, 该条 assistant 的
  tool_calls 声明会【原样残留】在发送给 DeepSeek 的消息里——DeepSeek 严格校验【每一条】
  assistant 的每个 tool_call_id 都必须有 tool 消息回应, 残留声明即触发
  HTTP 400 "insufficient tool messages following tool_calls"(如 write_code_file 双工具调用成功后总结时报错)。
- **修复(整体)**:
  1. normalize 配对修正改为【全量】: 遍历所有带 tool_calls 的 assistant, 每条只保留
     "已收到 tool 回复"的声明(id 在 replied 集合), 无回复的声明剔除、该条退化为纯文本
     (content 保留, 不丢信息);
  2. 新增兜底清理: 修正后被剔除声明所对应的 tool 回复消息一并移除(避免孤立 tool 消息);
  3. 原有能力保留: 孤立 tool 丢弃、同轮部分回复剔除、字段严格化、完整配对不误删。
- **单测覆盖 6 场景全过**: 多轮无回复剔除(400 真凶)/同轮部分回复/孤立 tool/完整配对/
  双轮完整/trim 孤立+完整。
- 其余全部不变: 直接控制 Agent(无小AI 中转)+ 小AI 只监管、自修复回路、控制板点击交互、
  白名单 75 命令、输入框悬浮固定底部、窗口丝滑、拦截红气泡、高危密码解锁、天气简体真实、
  持久记忆、联网搜索总结、股票趋势图/绘画/软件操控/进程管理。

## 3.35 v3.29 图形化安装包落位 AI 目录(不再迷失于系统下载目录)

- **修复**: `agent/tools/system.py::_gui_install` 原把安装包下载到 `~/Downloads`(系统下载目录),
  AI 的进程/沙箱无法定位安装包, 图形化安装找不到文件而失败。
- **整体改造**:
  1. 下载目标一律落在【AI 所造的目录】: Agent 下载目录 `server/downloads/installers/<pkg>/`
     (每次安装独立子目录, 避免同名覆盖; 目录自动创建, 失败则回退到 Agent 下载目录);
  2. 下载前清除同名旧包, 防止残留损坏文件被启动;
  3. 下载完成校验 + 兜底迁移: 若文件被浏览器/外部下载器截获到系统下载目录
     (~/Downloads 或 ~/下载), 自动识别同名/含包名安装包(.exe/.msi/.dmg/.deb/.rpm),
     用 shutil.move 迁移到 AI 目录后再启动安装向导;
  4. 步骤记录与进度文案同步(安装包路径、迁移来源)。
- 其余全部不变。

## 3.36 v3.30 软件复用已打开实例 + 图形化操作提速精准

- **复用已打开实例(所有'打开软件'操作通用)**: `agent/tools/app_control.py` 新增
  `_detect_and_focus` —— 打开软件前先做【前台窗口 + 后台进程】双通道检测
  (Windows: tasklist 进程检测 + pywinauto 标题窗口检测; Linux/macOS: pgrep):
  - 已运行 → 直接聚焦现有实例(set_focus + SetForegroundWindow + 最小化恢复),
    返回 already_running, 不重新打开新实例(QQ/微信/浏览器等同理, 避免多开/资源占用/发错实例);
  - 未运行 → 才走启动流程。
  新增 `_find_window_by_title`(标题过滤设置/帮助/登录等非主窗, 短标题主窗优先)、
  `_activate_window`(快速精准聚焦)、`_title_exclude`。
- **图形化操作提速精准**: `_gui_send_msg` 定位循环 0.8s->0.35s 快速轮询收敛;
  键盘步骤 sleep 0.7/0.9/1.2s -> 0.35/0.5/0.6s; 托盘激活 1.6s->0.8s。
- app_control 工具描述同步: launch 已打开则自动复用现有实例。
- 其余全部不变。

## 3.37 v3.31 修复 focus 报错 + 复用检测强化(不再新开实例) + 图形化再提速

- **修复 focus 报错**: `app_control action=focus` 原用 `Application.connect(title_re=).set_focus()`
  (Application 无 set_focus 方法 -> "Neither GUI element (wrapper) nor wrapper method 'set_focus'")。
  改为 `_find_window_by_title` + `_activate_window`: 找不到窗口返回清晰提示
  "未找到「XX」的窗口, 请先打开该软件", 找到则精准聚焦。
- **复用检测强化(解决仍新开实例)**: `_detect_and_focus` Windows 进程检测由
  `tasklist /FI IMAGENAME eq XX.exe`(完全匹配, QQ 变体进程名会漏) 改为
  【全量 tasklist CSV 子串匹配映像名 + psutil 进程名/命令行子串兜底】,
  兼容 QQ.exe/QQScLauncher/Weixin/新版 QQ 等变体;
  `_find_window_by_title` 优先 win32gui EnumWindows 毫秒级快速通道(标题匹配),
  失败再退 UIA(win32 backend 比 uia 快)。
- **send_message 复用**: 发消息流程原直接 `_launch_cmd` 新开实例; 现先 `_detect_and_focus`,
  已运行则直接复用并跳过等待(低延迟), 未运行才启动(等待 2.5s -> 1.0s)。
- **图形化再提速**: 主窗轮询 0.35->0.25s; 键盘步骤 0.35/0.5/0.6 -> 0.25/0.3/0.4s; 托盘 0.8->0.5s。
- 其余全部不变。

## 3.38 v3.32 AI 自主自动化控制 Agent + 小AI 监管加强减误判 + 修复"打开QQ没打开"

- **AI 自主自动化控制 Agent**: 系统提示新增自主条(core + config 同步)——
  AI 是自主智能体: 接到任务后自行规划执行步骤, 连续自主调用工具获取所需信息
  (搜索->抓取->总结->展示->建议/查天气/查股票/查文件/运行软件等), 不需要用户逐条指定
  调用哪个工具; 目标合法就自动拆解按序执行, 失败自动重试/换路径, 只有缺关键信息才追问。
  工具调用对 AI 透明, 可自主发起任意合法调用(小AI 实时监管)。
- **小AI 监管加强**: 恶意意图表新增勒索加密/钓鱼仿冒/挖矿/键盘记录/数据外泄/篡改hosts/
  自启动后门/清除安全审计日志/凭据转储/入侵渗透等 10 类中文模式(恒拦截)。
- **减少误判 + 减小限制**: "清空回收站"与"删除浏览器历史记录"由恶意拦截【降级】为高危
  (系统登录密码确认, 属正常用户操作); "清除安全/系统/审计日志/取证痕迹"仍恒拦截;
  进程复用检测不再把 Agent 自身(python/node/java/php/nginx)误判为目标应用。
- **修复"打开QQ没打开"**: `_detect_and_focus` 改为【窗口优先判定】——
  只有找到可见主窗才判定复用(聚焦不新开); 仅后台进程/无窗口时返回 process_only(reuse=False),
  `_launch_app`/`_send_message` 会【继续启动新实例】, 保证"打开QQ"等指令一定有结果;
  进程检测按映像名/进程名模糊匹配(兼容 QQ.exe/QQScLauncher/Weixin 变体)且排除无关进程。
- 其余全部不变。
