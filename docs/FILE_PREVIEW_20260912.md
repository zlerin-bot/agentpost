# 主流文件直接阅读

产品原则：Human 点击即可阅读，下载是可选操作；界面减少技术术语与不必要步骤。

当前本地切片新增 DOCX / DOC，沿用已有 Markdown、HTML、PDF、JSON、TXT 和 ZIP 目录预览。文件目录及讨论附件均有查看入口；通用 MIME 依文件后缀识别，ZIP MIME 的 DOCX 也按 Word 处理。原文件不改动，不要求重新上传。

DOCX 安全解析正文 XML，保留标题、段落、表格；不执行宏、不解析外部关系，不展示图片、批注及复杂版式，不显示修订标记。DOC 提供文字预览，macOS 使用 textutil，Linux 使用 antiword。不是原版分页排版；图片型或加密文档不能凭文字解析保证可读。PDF 仍使用浏览器原生阅读器，手机浏览器支持差异仍须真机验收。

解析限制：DOC 最大输入及输出8MB，转换10秒超时；DOCX 正文XML最大8MB，禁止DTD/实体声明（含UTF16），只读取指定正文，不解压到磁盘。错误以可读页面返回，沿用附件权限、404隔离、CSP sandbox和只读状态。DOCX仅显示正文，不包括页眉页脚。RAR/7z及ZIP包内文件正文尚不支持。

部署准备：Docker 和授权阿里云切换流程安装 antiword（仅缺失时安装），postflight 检查存在。本轮未部署、未安装生产组件。Linux antiword的真实DOC渲染尚待部署前后验证；当前真实DOC测试使用macOS textutil。命令依据 https://manpages.debian.org/unstable/antiword/antiword.1.en.html 。

验证：完整非PG 551 passed / 2 skipped / 7 deselected；新增边界用例后聚焦37 passed；50前端测试、Ruff及format、JS语法及diff通过。实际DOC/DOCX中文转换成功；隔离8783上传Word/HTML/损坏DOCX，1470px和390px检查阅读、Escape关闭、无横向溢出及无JS异常。DOCX标题/表格/转义/DTD/体积限制和API权限/只读已有回归。PostgreSQL、生产Linux渲染、真机跨设备未验收。

预览 http://127.0.0.1:8783/orbit?module=projects&view=board&task=4a7df966-c6d4-4550-a6c9-496e24e24ffb
登录信息已单独提供给本地使用者，不写入此文档。启动脚本/private/tmp/ap_word_demo.py；独立临时库，8781/8782保留。不要重复seed已有预览。
