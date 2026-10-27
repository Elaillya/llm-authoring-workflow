# 分享工具到 GitHub

分享已提交的通用源码 Git；个人题目、模型回复、密钥和运行环境不加入仓库。推送前核实实际认证账号、仓库身份与可见性，检查 git status 和发布文件范围。

在自己的空仓库中添加 remote 并正常推送：

```bash
git remote add origin https://github.com/YOUR-ACCOUNT/YOUR-REPOSITORY.git
git push -u origin main
```

别人 Clone 后依 README 建自己的工作区。手动分支按Markdown填写流程执行；自动化分支的专家准备、启动口令、Arena交接和异常处理见[专家使用说明](AUTOMATION_EXPERT_GUIDE.md)。自动化使用专家自行准备的pi-web服务及已登录的ego-lite，不把个人配置、题目材料和运行环境加入公开源码。

已有远程分支时，先fetch并比较历史，再选择推送目标。独立原型分支保持原用途；当前流程在单独分支提交，通过面向main的PR审阅，不直接覆盖或强推既有分支。若本地未发布历史混有个人环境信息，可保留原本地分支，将审查后的完整源码快照整理为基于远程main的新提交；检查最终文件和将公开的提交历史。
