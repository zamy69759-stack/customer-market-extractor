# customer-market-extractor

一个面向 Codex 的客户与市场知识萃取 Skill。它从邮件、聊天导出、会议逐字稿和项目资料中发现并关联真实业务事件，辅助生成可追溯、待审核的 MKT Markdown 知识卡。

## 安装

将本仓库克隆到 Codex Skills 目录：

```bash
git clone <your-repository-url> ~/.codex/skills/customer-market-extractor
cd ~/.codex/skills/customer-market-extractor
python3 run.py configure
```

Windows 可将仓库克隆到 `%USERPROFILE%\.codex\skills\customer-market-extractor`，然后运行 `py run.py configure`。

配置文件 `config.json` 只在本机生成并已加入 `.gitignore`。首次配置必须由用户亲自指定：

1. 原始语料库根目录；
2. 企业知识库根目录；
3. 工具工作目录。

## 使用

```bash
python3 run.py status
python3 run.py scan "客户日常沟通/Bayside"
python3 run.py validate
python3 run.py configure
```

也可以在 Codex 中说：

> 使用 customer-market-extractor 萃取客户日常沟通/Bayside，生成待审核 MKT 知识卡。

## 隐私与事实边界

- 原始语料默认只读。
- 不配置任何 API Key，不默认上传图片、音频或敏感业务资料。
- OCR、视觉模型或云转写必须在说明服务和传输范围后取得明确授权。
- 未提供的附件不会被当作已读取；不补写不存在的客户答复、订单、测试结果或市场结论。
- 图纸批准、预算批准和采购意向均不自动等于收到 PO。
- 输出知识卡默认为 `审核状态: 待审核`、`公开发布许可: 待确认`。

## 文件支持

核心解析器仅使用 Python 标准库，直接支持 TXT、CSV、HTML、EML、SRT、VTT 和 JSON。DOCX、XLSX、PDF、PPTX、MSG 使用可选本地依赖；详见 `references/input-support.md` 和 `pyproject.toml`。

## 开发与测试

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 /path/to/skill-creator/scripts/quick_validate.py .
```

测试使用合成资料，不包含客户数据。运行时产生的本机配置、指纹清单、解析报告和知识卡均不会被 Git 追踪。
