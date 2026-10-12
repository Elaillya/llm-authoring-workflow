# 将工具上传到自己的GitHub仓库

源码ZIP可以解压后作为新仓库内容上传，也可直接使用工具源码Git。只分享通用工具；个人工作区、密钥、模型回复、调用记录和环境都留在工作区。

在GitHub创建自己的空仓库。以下命令在本工具源码目录执行，仓库URL替换为自己的：

```bash
git remote add origin https://github.com/YOUR-ACCOUNT/YOUR-REPOSITORY.git
git push -u origin main
```

如果从ZIP开始，先初始化本地源码仓库：

```bash
git init -b main
git add .
git commit -m "Add first-round LLM authoring workflow"
```

再添加remote并push。发布前看git status，确认只有工具文件；发布脚本会拒绝非空凭据JSON和发布范围外的Git文件。此工具不会替你创建远端仓库或自动push。

别人Clone后依README在自己的环境建立工作区，第一次会看到三个模型配置提示；每道新题会看到题型选择。你分享的是流程与工具版本，不是你的服务账号或题目历史。
