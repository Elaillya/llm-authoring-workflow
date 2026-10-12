# 工具仓与第一轮出题

如果用户要求开始出题，先读 `README.md` 与 `skills/llm-authoring-workflow/SKILL.md`。在独立工作区执行，首次无工作区时用系统 Python 运行 `scripts/lab.py workspace-create ../llm-authoring-workspace`，再按 `scripts/setup.py` 准备依赖环境。先询问题型，同时提示填写新工作区 `local/providers.json` 中三个模型配置。

如果用户要求维护代码，以 `docs/SPEC.md` 和 `rules/authoring.md` 为依据，运行 `python -m unittest discover -s tests`。维护时不调用真实模型；专业场景和事实由出题流程生成，计算机科学为默认领域。

第一轮范围是题目、Insight、核心考点、三模型达成性验证、作者自查及交接。第二轮独立质检及排序通过 handoff.json 接续，不在本仓实现。真实任务、密钥和环境位于工作区或忽略目录，发布包只从 Git 跟踪的通用文件生成。
