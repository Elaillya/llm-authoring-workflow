# LLM Authoring Workflow

开放难题第五期完整出题与五模型排序工具，适用于 Codex 侧栏。选择专业领域 → 选择题型 → 助手生成并核实场景 → 冻结候选题面、Insight 和考点 → 用户提供 Seed 回复 → 判断 Seed → 用户提供 GPT 和 Claude 回复 → 三模型验证 → 用户提供 Arena 两个随机模型回复 → 五模型考点评估与排序 → Markdown 交付。

前三个模型固定为 Seed 2.1 Turbo、GPT-5.6 sol、Claude Opus 4.6。非决定性核心考点可选，没有时输出“无”。**不调用模型 API，不要求配置密钥，不生成截图。所有官方网页截图由用户另行提交甲方。**

## 第一次使用

1. Clone 本仓库，在 VS Code 打开仓库，在 Codex 侧栏发送：

   ```text
   按 AGENTS.md 为我创建独立工作区并开始完整出题流程。
   ```

2. 助手准备依赖和独立工作区。打开生成的 `Authoring.code-workspace`。
3. 告诉侧栏希望出题的专业领域，再从分析决策类、开放推荐类、How-to 类中选一种。问题、关键事实、限制和来源核实由助手完成；`materials/` 可以为空。

手动准备也可以：

```bash
python3 scripts/setup.py
.venv/bin/python scripts/lab.py workspace-create ../my-authoring-workspace
```

环境要求 Python≥3.10、Git、Linux/macOS；Windows 使用 WSL。默认只准备 Python 依赖，不下载浏览器和中文字体。

## 怎样提供五个模型的回答

冻结候选后，助手先创建 `model-input/rNNNN/prompt.md` 和 `model-input/rNNNN/Seed 2.1 Turbo.md`，并给你可点击链接。

复制 `prompt.md` 到对应型号的官方网页新会话；将完整回答的 Markdown 原文粘贴到 Seed 文件里，替换占位文字，保存后在侧栏说“Seed 已填好，继续”。不用自己创建文件，不用加任何标题、来源字段或外层代码块；不改写或补写模型回答。

助手导入并按冻结的决定性考点判断。**Seed 未达成全部决定性考点时，才创建 `GPT-5.6 sol.md` 和 `Claude Opus 4.6.md`。**这两个型号按项目要求使用中高推理模式，发送相同题面和格式指令，填好后说“GPT 和 Claude 已填好，继续”。如果官方页面不能确认规定型号，说明缺少该型号，不能用相近版本代替。

Seed 若全部达成，助手保留该结果，重新论证并修订候选；新题面重新取 Seed 回复。已有完整原件不覆盖、不重新索取；只修改 Insight 或考点时，对相同题面的原回复统一重评，不按现有回答倒推标准。

三模型门槛为 Seed 未全部达成、GPT 或 Claude 至少一个全部达成；三份完整原文均须保存。通过后助手创建 `arena-input/rNNNN/model-4.md`、`model-5.md` 和 `arena-prompt.md`。在 Arena Search + Battle 新会话获取随机两模型，填真实型号和完整原文，保存后说“两个 Arena 回复已填好，继续排序”。型号不得重复、不得与前三个相同、不得为 GPT/Claude 系列。

工作区对五份 Markdown 做完整性、版本绑定和逐点判断；用户提供的来源声明不等于工具已核验网页、型号、会话或随机过程。全部官方网页截图由你另行提交。

## 交付内容

最终交付六份方便复制的 Markdown：

- `delivery/vNNN/提交信息.md`：题目、题型、Insight、两类考点、五模型达成性及备注、具名排序和排序理由。
- `delivery/vNNN/models/`：五份按真实模型名命名的原回答，不在提交信息中重复内嵌。

没有非决定性核心考点时填写“无”。排序先比较全部决定性考点达成性，再在同一梯队按全部核心考点满足数比较，相同并列；排序和理由直接使用模型名称，理由至少 500 字。证据不足不能记为未达成。JSON、原始输入及哈希清单保留作记录，不生成交付 ZIP。

## 每道题打开一个窗口

在侧栏说“新建题目 <题目编号>”，把 `<题目编号>` 换成你希望使用的编号。助手运行 `bin/lab new <题目编号>`，创建 `tasks/<题目编号>/<题目编号>.code-workspace`，用新窗口打开即可。各题有独立 Git、题面、回复、判断和交付，共用运行环境；每道新题分别选择领域和题型。

已有题目可以运行 `bin/lab rename <新题目编号>` 改名，保留冻结 ID、证据、Git 历史和旧路径入口。

## 更新和接续

在工具仓执行 `git pull --ff-only`，再由侧栏运行 `scripts/lab.py --workspace <已有工作区> workspace-update` 更新说明。该命令保留既有题目、原文、判断和交付，不自动清空题目。

3.0.0 起默认手动提供所有回复；`collect`、`recover`、`render` 入口停止执行。旧 API 原件与截图可作为历史材料继续读取和导出，历史 API 渲染图不能充当新要求的官方网页截图。旧私有配置不会删除，新题不读取或要求配置它。

侧栏开始指令：

```text
按 AGENTS.md 开始或接续完整出题流程。使用手动 Markdown 模型输入，不调用 API。先询问领域和题型，冻结候选后先收 Seed，满足筛查条件后再收 GPT 和 Claude；所有网页截图由我自行提交。
```
