# LLM Authoring Workflow

开放难题第五期 **第一轮出题** 工具包，适用于 Codex 侧栏。默认计算机科学：先询问题型，助手生成并核实场景，写题面、Insight与考点，完成三个模型验证和完整Markdown截图，导出给第二轮的交接包。

固定模型：Seed 2.1 Turbo、GPT-5.6 sol、Claude Opus 4.6。非决定性核心考点可选，没有时输出“无”。

## 第一次从GitHub使用

1. Clone或解压本仓，在VS Code打开仓库，在Codex侧栏发送：

   ```text
   按 AGENTS.md 为我创建独立工作区并开始第一轮出题。
   ```

2. 助手会准备本仓独立环境与工作区，提示填写新工作区 `local/providers.json`。请填三个服务的base_url、实际model ID、api_key（或私有密钥文件/环境变量）。密钥留在私有文件，勿贴到聊天中。
3. 在生成的 `Authoring.code-workspace` 中继续侧栏任务，从分析决策类、开放推荐类、How-to类中选一种。问题和限制由助手生成，不要求先填背景文件。

准备过程也可以手动执行：

```bash
python3 scripts/setup.py
.venv/bin/python scripts/lab.py workspace-create ../my-authoring-workspace
```

打开输出的工作区文件，侧栏发送：

```text
按 AGENTS.md 使用 llm-authoring-workflow 开始第一轮出题。
```

`scripts/setup.py`下载当前工具专用Python依赖、Chromium和中文字体。环境基线Python≥3.10、Git和Linux/macOS；Windows使用WSL。实际验证环境为Linux/Python3.12，其他平台需自行验证。缺Chromium系统库时按Playwright提示安装；脚本不改账户登录、全局Python或系统服务。

## 开始后的流程

题型选择 → 配置检查 → 自动生成并核实场景 → 记录并冻结候选题面/Insight/考点 → Turbo筛查 → Turbo未达成时验证GPT/Claude → 三模型逐点评估及作者自查 → 锁定提交版并交接。

Seed必须未满足全部决定性点；GPT或Claude至少一个满足全部决定性点。网络错误或截断记证据不足。各次真实原件保留，修改题面重新采集，修改考点统一重评。

每题一个Git仓。新题在侧栏说“新建 question-002 的独立出题工作区”，打开返回的工作区文件即可并行工作；同一题目保持一个写入者。每道新题都会先询问题型，已经完整的共用API配置不会重复要求填写。

## 输出与边界

题目目录 `delivery/v001/` 包含 `出题提交.md`、`fields.json`、`question.json`、`sources.md`、三模型 `evaluation.json`、`author-self-review.json`、三份原Markdown、三张截图、API原始证据、`handoff.json`与文件哈希。下一版使用v002，旧证据保留。

第一轮到交接结束；独立质检、返修意见、Arena两模型和五模型排序属于第二轮，见 [交接接口](docs/HANDOFF.md)。作者自查不能冒充独立专家质检或最终验收。

截图明确标注API Markdown渲染，呈现模型版本和完整正文。数学原语法保留，首版无专用公式排版，外部图片不加载。是否满足平台截图接收条件由实际规则决定。

## 检查与打包

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/python scripts/build_release.py --output dist/llm-authoring-workflow-v1.0.1.zip
```

发布脚本只打包已提交且属于通用目录的Git文件。源码修改先检查并提交。测试都是合成夹具；测试通过不证明正式题目的专业判断或供应商在线可用。

准备好后，将ZIP解压内容放入自己的新GitHub仓库，或把本工具仓设置为新仓的remote后push。发布操作由仓库所有者执行；详见 [上传GitHub](docs/PUBLISH.md)。代码MIT许可，字体使用其独立SIL许可证；项目方原始作业文档未放入源码发布包。
