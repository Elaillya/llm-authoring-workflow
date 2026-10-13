# LLM Authoring Workflow

开放难题第五期完整出题与五模型排序工具，适用于 Codex 侧栏。选择专业领域 → 选题型 → 生成并核实场景 → 冻结题面、Insight 和考点 → 三模型验证 → 填入 Arena 两个随机模型的 Markdown → 五模型考点评估和排序 → Markdown 交付。

前三个模型固定为 Seed 2.1 Turbo、GPT-5.6 sol、Claude Opus 4.6。非决定性核心考点可选，没有时输出“无”。流程直接接续 Arena 和排序。

## 第一次使用

1. Clone 或解压本仓，在 VS Code 打开仓库，在 Codex 侧栏发送：

   ```text
   按 AGENTS.md 为我创建独立工作区并开始完整出题流程。
   ```

2. 助手准备依赖和工作区，并提示填写 `local/providers.json` 中三个模型的服务地址、实际 model ID 和私有密钥。已配置的用户不用重新填写。
3. 打开生成的 `Authoring.code-workspace`，先告诉侧栏你要出题的专业领域，再从分析决策类、开放推荐类、How-to 类中选一种。领域可自由填写，例如数学、材料科学或计算机科学；问题、事实和限制由助手生成并核实。

手动准备也可以：

```bash
python3 scripts/setup.py
.venv/bin/python scripts/lab.py workspace-create ../my-authoring-workspace
```

打开返回的工作区文件，在侧栏发送：

```text
按 AGENTS.md 开始或接续完整出题流程。
```

环境基线为 Python≥3.10、Git、Linux/macOS；Windows 使用 WSL。实际验证环境为 Linux/Python3.12。setup 准备专用依赖、Chromium 和中文字体；缺系统库时按 Playwright 提示安装。

## 每道题打开一个窗口

在已有工作区的 Codex 侧栏发送“新建题目 ***，复用已有配置和运行环境”。助手运行 `bin/lab new ***`，创建独立题目及 `tasks/***/***.code-workspace`；用新窗口打开这个文件即可。每道题各自保存题面、回复、判断和交付，模型配置沿用父目录的 `local/providers.json`。

已有题目可以运行 `bin/lab rename ***` 改名。工具保留冻结版本、原始回复、评估和 Git 历史，也保留旧路径入口以便原对话接续。

## 已做完三模型的旧题如何接续

2.2.0 保留现有领域、题型、冻结版本、原回复、模型判断、API截图、自查及旧交付。更新侧栏说明即可继续缺失步骤，已有五模型和排序时直接导出新版 Markdown。已冻结题目沿用原领域；每道新题重新询问领域，不从其他题目自动继承。

在工具仓拉取更新，然后由侧栏执行（路径替换为已有工作区）：

```bash
git pull --ff-only
python3 scripts/lab.py --workspace ../my-authoring-workspace workspace-update
```

打开原来的工作区，在侧栏发送：

```text
保留现有题目、三模型回复和判断，按新版 AGENTS.md 从缺失的 Arena 和五模型排序步骤继续。
```

升级会备份并更新工具入口和侧栏 Skill；已有题目数据与模型配置保持。已完成且通过门槛的旧题会直接得到 Arena 填写文件，原 `delivery/v001` 保留，完整提交用 `v002` 等新目录。

## 最终复制哪些文件

助手生成新的 `delivery/vNNN/` 目录，给出六个 Markdown 文件的链接：

```text
提交信息.md
models/Seed 2.1 Turbo.md
models/GPT-5.6 sol.md
models/Claude Opus 4.6.md
models/实际 Arena 模型名称.md
models/另一个实际 Arena 模型名称.md
```

`提交信息.md` 包含专业领域、题目 prompt、题型、Insight、决定性与非决定性核心考点、各模型达成性及备注、五模型排序及理由、出题说明。五份模型回复保持原始 Markdown，分别复制即可。排序和备注直接使用实际模型名称，同分使用 `=`，高低使用 `>`。

最终交付直接使用 Markdown。助手保留原 API 截图及内部来源、校验记录，给出六份可复制文件；交付过程不生成 ZIP，也不把五份回复全文合并进提交信息。模型名称含路径特殊字符时，文件名做安全替换，真实型号仍保留在提交信息中。

## Arena 阶段只填两份 Markdown

助手运行 `lab arena-prepare --evaluation evaluations/three-rNNNN.json`，自动创建：

- `arena-input/rNNNN/model-4.md`
- `arena-input/rNNNN/model-5.md`
- `arena-input/rNNNN/arena-prompt.md`：用于 Arena 的题面。

打开前两份文件，将 `model_name: 待填写` 改为揭晓的完整型号，把分隔线下面的占位文字替换为完整原始 Markdown 回复。其余文件由工具管理。保存后在侧栏说：

```text
已填好两个 Arena 回复，请继续五模型考点评估、排序和完整交付。
```

使用 Arena Search 联网模式、Battle Mode、新会话获取随机两模型；不得重复，不得与前三个相同，不得属于 GPT/Claude 系列。**这里不用上传 Arena 截图，截图由你自行向甲方提交。** 工具记录 Markdown 为用户提供，不把它当作已独立核验的 Arena 页面。

## 验证与排序

候选题面、Insight 和考点先冻结，再筛查 Turbo；Turbo 未达成全部决定性点时才调用 GPT/Claude。最终必须保存三份完整真实回复，GPT 或 Claude 至少一个全部决定性达成。已有完整原件直接复用，不重新收费调用。

五模型使用同一冻结考点逐项判断：决定性点控制是否整体达成，非决定性点也进入排序。全部决定性达成的模型优先；同梯队按全部核心考点满足数排序，相同则并列。排序及理由直接显示实际型号。理由采用“总结＋逐模型具体考点说明”，不少于500字。

每题独立 Git；新题在侧栏说“新建 question-002 的独立工作区”。同一题保持一个写入者，旧版本和失败证据保留。

## 输出

完整提交使用上文列出的六份 Markdown。目录还保留 `fields.json`、冻结题目、评估、作者自查、API 截图及来源证据，用于复核与返修。Arena 截图单独由用户提交。

最终导出使用五模型评估和排序记录：

```bash
lab export --evaluation evaluations/five-rNNNN.json --self-review evaluations/self-review-rNNNN.json --ranking evaluations/ranking-rNNNN.json --output delivery/v002
```

目录已存在时不覆盖。详细接续与交付字段见 [提交接口](docs/HANDOFF.md)。API 截图明确标注 Markdown 渲染来源；数学原语法保留，外部图片不加载。

## 检查与发布

```bash
.venv/bin/python -m unittest discover -s tests
```

测试使用合成夹具。上传步骤见 [上传 GitHub](docs/PUBLISH.md)。代码 MIT 许可，字体使用其独立 SIL 许可证。
