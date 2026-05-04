<p align="center">
  <a href="#简体中文">简体中文</a> · <a href="#繁體中文">繁體中文</a> · <a href="#english">English</a>
</p>

---

<h1 id="简体中文">简体中文</h1>

<p align="center">
  <strong>SyncIndex</strong> — 轻量级增量数据同步与索引引擎 CLI<br/>
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue" alt="Python 3.8+"/>
  <img src="https://img.shields.io/badge/Dependencies-Zero-green" alt="Zero Dependencies"/>
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="MIT License"/>
  <img src="https://img.shields.io/badge/Tests-65%20passed-success" alt="65 Tests"/>
</p>

---

## 🎉 项目介绍

**SyncIndex** 是一款轻量级的增量数据同步与索引引擎，专为命令行场景设计。它能够智能地追踪数据源变更，仅对发生变化的文件执行同步操作，大幅减少不必要的 I/O 开销。

无论你是在管理代码仓库的文件索引、追踪数据目录的变更历史，还是需要实时监控关键文件的变动——**SyncIndex** 都能以极低的资源占用，为你提供精准、高效的同步体验。

> 💡 **核心理念**：用最简单的工具，解决最实际的数据同步问题。零外部依赖，开箱即用。

---

## ✨ 核心特性

| 特性 | 说明 |
|------|------|
| 📋 **YAML/JSON 驱动配置** | 通过声明式配置文件定义数据源与同步策略，告别繁琐的命令行参数 |
| 🔌 **多数据源支持** | 内置 FileSystem、JSON、CSV 三种数据源适配器，覆盖主流场景 |
| 🔍 **增量变更检测** | 采用 **哈希 + 时间戳双校验** 机制，精准识别新增、修改与删除的文件 |
| 👀 **实时文件监控** | 基于 watchdog 模式，文件变动后自动触发同步，毫秒级响应 |
| 🧩 **插件化扩展架构** | 数据源采用插件式设计，轻松扩展自定义数据源类型 |
| 📊 **丰富的报告生成** | 支持 **Markdown / JSON / CSV** 三种格式输出同步报告 |
| 🪶 **零外部依赖** | 纯 Python 标准库实现，**Python 3.8+** 即可运行，无需安装任何第三方包 |
| ✅ **完善的测试覆盖** | 内置 **65 个单元测试**，保障核心逻辑的稳定性与可靠性 |

---

## 🚀 快速开始

### 1. 安装

```bash
# 方式一：通过 pip 直接从 GitHub 安装
pip install git+https://github.com/gitstq/SyncIndex.git

# 方式二：克隆仓库后以开发模式安装
git clone https://github.com/gitstq/SyncIndex.git
cd SyncIndex
pip install -e .
```

### 2. 初始化配置

```bash
syncindex init
```

执行后会在当前目录生成默认配置文件 `syncindex.json`，你可以根据需要修改其中的数据源和输出选项。

### 3. 执行首次同步

```bash
syncindex sync
```

首次运行时，SyncIndex 会扫描所有配置的数据源，建立完整的文件索引。后续运行将自动执行**增量同步**，仅处理发生变更的文件。

### 4. 查看同步状态

```bash
syncindex status
```

### 5. 生成同步报告

```bash
syncindex report
```

> 🎉 **恭喜！** 到这里你已经掌握了 SyncIndex 的基本用法。接下来可以继续阅读详细使用指南，解锁更多高级功能。

---

## 📖 详细使用指南

### CLI 命令一览

| 命令 | 说明 | 示例 |
|------|------|------|
| `syncindex init` | 初始化配置文件 | `syncindex init` |
| `syncindex sync` | 执行增量同步 | `syncindex sync --config my-config.json` |
| `syncindex watch` | 启动实时监控模式 | `syncindex watch --interval 3` |
| `syncindex status` | 查看当前索引状态 | `syncindex status` |
| `syncindex report` | 生成同步报告 | `syncindex report --format csv` |

### 配置文件详解

以下是一个完整的 `syncindex.json` 配置示例：

```json
{
  "version": "1.0",
  "sources": [
    {
      "type": "filesystem",
      "name": "my-project",
      "path": "./src",
      "recursive": true,
      "include": ["*.py", "*.js"],
      "exclude": ["__pycache__", "node_modules"]
    }
  ],
  "output": {
    "index_path": ".syncindex.json",
    "report_format": "markdown",
    "report_path": "./sync-report.md"
  },
  "options": {
    "hash_algorithm": "md5",
    "watch_interval": 2
  }
}
```

#### 配置字段说明

**`version`** — 配置文件版本号，当前为 `"1.0"`。

**`sources`** — 数据源列表，支持同时配置多个数据源：

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | string | 数据源类型，可选 `filesystem`、`json`、`csv` |
| `name` | string | 数据源名称，用于标识和报告展示 |
| `path` | string | 数据源路径（文件路径或目录路径） |
| `recursive` | bool | 是否递归扫描子目录（仅 filesystem 类型） |
| `include` | list | 文件匹配规则白名单，支持 glob 模式 |
| `exclude` | list | 文件匹配规则黑名单，支持 glob 模式 |

**`output`** — 输出配置：

| 字段 | 类型 | 说明 |
|------|------|------|
| `index_path` | string | 索引文件的存储路径 |
| `report_format` | string | 报告格式，可选 `markdown`、`json`、`csv` |
| `report_path` | string | 报告文件的输出路径 |

**`options`** — 全局选项：

| 字段 | 类型 | 说明 |
|------|------|------|
| `hash_algorithm` | string | 哈希算法，可选 `md5`、`sha1`、`sha256` |
| `watch_interval` | int | 文件监控轮询间隔（秒） |

### 实时监控模式

```bash
# 启动监控，默认每 2 秒检查一次
syncindex watch

# 自定义监控间隔为 5 秒
syncindex watch --interval 5
```

监控模式启动后，SyncIndex 会持续监听数据源目录的文件变动。一旦检测到新增、修改或删除操作，将**自动触发增量同步**，并更新索引文件。

> ⚡ **提示**：在 CI/CD 流水线中，建议使用 `syncindex sync` 单次执行模式；在开发环境中，推荐使用 `syncindex watch` 实时监控模式。

### 报告生成

```bash
# 生成 Markdown 格式报告（默认）
syncindex report

# 生成 JSON 格式报告
syncindex report --format json

# 生成 CSV 格式报告
syncindex report --format csv

# 指定报告输出路径
syncindex report --format markdown --output ./reports/my-report.md
```

---

## 💡 设计思路与迭代规划

### 设计哲学

SyncIndex 的设计遵循以下核心原则：

- **简洁至上**：不引入任何外部依赖，用 Python 标准库构建全部功能
- **约定优于配置**：提供合理的默认值，开箱即用，同时保留充分的可定制性
- **增量优先**：通过哈希 + 时间戳双校验，最小化不必要的文件扫描与 I/O 操作
- **可扩展性**：插件化的数据源架构，方便社区贡献新的数据源类型

### 架构概览

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   CLI 层     │────▶│  同步引擎     │────▶│  索引存储     │
│  (cli.py)    │     │(sync_engine) │     │(indexer.py)  │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                    ┌──────▼───────┐
                    │  数据源层     │
                    │ (sources.py) │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │FileSystem│ │   JSON   │ │   CSV    │
        └──────────┘ └──────────┘ └──────────┘
```

### 未来规划

- [ ] 🗄️ **数据库数据源**：支持 SQLite、PostgreSQL 等数据库直连
- [ ] 🌐 **远程数据源**：支持 S3、FTP、HTTP 等远程存储
- [ ] 🔄 **双向同步**：支持源与目标之间的双向变更同步
- [ ] 📡 **Webhook 通知**：同步完成后推送通知到 Slack、钉钉等
- [ ] 🖥️ **Web UI**：提供可视化配置与状态监控面板
- [ ] 📦 **打包分发**：发布到 PyPI，支持 `pip install syncindex`

---

## 📦 安装与部署

### 环境要求

- **Python** >= 3.8
- **操作系统**：跨平台支持（Linux / macOS / Windows）
- **外部依赖**：无

### 安装方式

```bash
# 从 GitHub 安装（推荐）
pip install git+https://github.com/gitstq/SyncIndex.git

# 克隆后开发模式安装
git clone https://github.com/gitstq/SyncIndex.git
cd SyncIndex
pip install -e .

# 运行测试以验证安装
python -m pytest tests/ -v
```

### 卸载

```bash
pip uninstall syncindex
```

---

## 🤝 贡献指南

我们欢迎并感谢每一位贡献者！无论你是提交 Bug 报告、改进文档，还是贡献代码，都是对项目的宝贵支持。

### 贡献流程

1. **Fork** 本仓库
2. 创建特性分支：`git checkout -b feature/your-feature-name`
3. 提交变更：`git commit -m "feat: add your feature description"`
4. 推送分支：`git push origin feature/your-feature-name`
5. 提交 **Pull Request**

### 代码规范

- 遵循 **PEP 8** 编码规范
- 提交信息遵循 **Conventional Commits** 格式
- 新功能请附带对应的**单元测试**
- 保持 **零外部依赖**的原则

### 报告问题

如果在使用过程中遇到任何问题，请通过 [GitHub Issues](https://github.com/gitstq/SyncIndex/issues) 提交，并附上以下信息：

- 操作系统与 Python 版本
- 完整的错误信息或异常堆栈
- 复现问题的最小配置示例

---

## 📄 开源协议

本项目基于 **[MIT License](https://opensource.org/licenses/MIT)** 开源。

```
MIT License

Copyright (c) 2024 SyncIndex Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```

---

<h1 id="繁體中文">繁體中文</h1>

<p align="center">
  <strong>SyncIndex</strong> — 輕量級增量資料同步與索引引擎 CLI<br/>
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue" alt="Python 3.8+"/>
  <img src="https://img.shields.io/badge/Dependencies-Zero-green" alt="Zero Dependencies"/>
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="MIT License"/>
  <img src="https://img.shields.io/badge/Tests-65%20passed-success" alt="65 Tests"/>
</p>

---

## 🎉 專案介紹

**SyncIndex** 是一款輕量級的增量資料同步與索引引擎，專為命令列場景設計。它能夠智慧地追蹤資料來源變更，僅對發生變化的檔案執行同步操作，大幅減少不必要的 I/O 開銷。

無論你是在管理程式碼倉庫的檔案索引、追蹤資料目錄的變更歷史，還是需要即時監控關鍵檔案的變動——**SyncIndex** 都能以極低的資源佔用，為你提供精準、高效的同步體驗。

> 💡 **核心理念**：用最簡單的工具，解決最實際的資料同步問題。零外部依賴，開箱即用。

---

## ✨ 核心特性

| 特性 | 說明 |
|------|------|
| 📋 **YAML/JSON 驅動配置** | 透過宣告式設定檔定義資料來源與同步策略，告別繁瑣的命令列參數 |
| 🔌 **多資料來源支援** | 內建 FileSystem、JSON、CSV 三種資料來源適配器，涵蓋主流場景 |
| 🔍 **增量變更偵測** | 採用 **雜湊 + 時間戳雙校驗** 機制，精準識別新增、修改與刪除的檔案 |
| 👀 **即時檔案監控** | 基於 watchdog 模式，檔案變動後自動觸發同步，毫秒級回應 |
| 🧩 **外掛化擴展架構** | 資料來源採用外掛式設計，輕鬆擴展自訂資料來源類型 |
| 📊 **豐富的報告生成** | 支援 **Markdown / JSON / CSV** 三種格式輸出同步報告 |
| 🪶 **零外部依賴** | 純 Python 標準函式庫實作，**Python 3.8+** 即可運行，無需安裝任何第三方套件 |
| ✅ **完善的測試覆蓋** | 內建 **65 個單元測試**，保障核心邏輯的穩定性與可靠性 |

---

## 🚀 快速開始

### 1. 安裝

```bash
# 方式一：透過 pip 直接從 GitHub 安裝
pip install git+https://github.com/gitstq/SyncIndex.git

# 方式二：克隆倉庫後以開發模式安裝
git clone https://github.com/gitstq/SyncIndex.git
cd SyncIndex
pip install -e .
```

### 2. 初始化配置

```bash
syncindex init
```

執行後會在目前目錄生成預設設定檔 `syncindex.json`，你可以根據需要修改其中的資料來源與輸出選項。

### 3. 執行首次同步

```bash
syncindex sync
```

首次執行時，SyncIndex 會掃描所有設定的資料來源，建立完整的檔案索引。後續執行將自動進行**增量同步**，僅處理發生變更的檔案。

### 4. 檢視同步狀態

```bash
syncindex status
```

### 5. 生成同步報告

```bash
syncindex report
```

> 🎉 **恭喜！** 到這裡你已經掌握了 SyncIndex 的基本用法。接下來可以繼續閱讀詳細使用指南，解鎖更多進階功能。

---

## 📖 詳細使用指南

### CLI 命令一覽

| 命令 | 說明 | 範例 |
|------|------|------|
| `syncindex init` | 初始化設定檔 | `syncindex init` |
| `syncindex sync` | 執行增量同步 | `syncindex sync --config my-config.json` |
| `syncindex watch` | 啟動即時監控模式 | `syncindex watch --interval 3` |
| `syncindex status` | 檢視目前索引狀態 | `syncindex status` |
| `syncindex report` | 生成同步報告 | `syncindex report --format csv` |

### 設定檔詳解

以下是一個完整的 `syncindex.json` 設定範例：

```json
{
  "version": "1.0",
  "sources": [
    {
      "type": "filesystem",
      "name": "my-project",
      "path": "./src",
      "recursive": true,
      "include": ["*.py", "*.js"],
      "exclude": ["__pycache__", "node_modules"]
    }
  ],
  "output": {
    "index_path": ".syncindex.json",
    "report_format": "markdown",
    "report_path": "./sync-report.md"
  },
  "options": {
    "hash_algorithm": "md5",
    "watch_interval": 2
  }
}
```

#### 設定欄位說明

**`version`** — 設定檔版本號，目前為 `"1.0"`。

**`sources`** — 資料來源列表，支援同時設定多個資料來源：

| 欄位 | 類型 | 說明 |
|------|------|------|
| `type` | string | 資料來源類型，可選 `filesystem`、`json`、`csv` |
| `name` | string | 資料來源名稱，用於識別與報告展示 |
| `path` | string | 資料來源路徑（檔案路徑或目錄路徑） |
| `recursive` | bool | 是否遞迴掃描子目錄（僅 filesystem 類型） |
| `include` | list | 檔案匹配規則白名單，支援 glob 模式 |
| `exclude` | list | 檔案匹配規則黑名單，支援 glob 模式 |

**`output`** — 輸出設定：

| 欄位 | 類型 | 說明 |
|------|------|------|
| `index_path` | string | 索引檔案的儲存路徑 |
| `report_format` | string | 報告格式，可選 `markdown`、`json`、`csv` |
| `report_path` | string | 報告檔案的輸出路徑 |

**`options`** — 全域選項：

| 欄位 | 類型 | 說明 |
|------|------|------|
| `hash_algorithm` | string | 雜湊演算法，可選 `md5`、`sha1`、`sha256` |
| `watch_interval` | int | 檔案監控輪詢間隔（秒） |

### 即時監控模式

```bash
# 啟動監控，預設每 2 秒檢查一次
syncindex watch

# 自訂監控間隔為 5 秒
syncindex watch --interval 5
```

監控模式啟動後，SyncIndex 會持續監聽資料來源目錄的檔案變動。一旦偵測到新增、修改或刪除操作，將**自動觸發增量同步**，並更新索引檔案。

> ⚡ **提示**：在 CI/CD 流水線中，建議使用 `syncindex sync` 單次執行模式；在開發環境中，推薦使用 `syncindex watch` 即時監控模式。

### 報告生成

```bash
# 生成 Markdown 格式報告（預設）
syncindex report

# 生成 JSON 格式報告
syncindex report --format json

# 生成 CSV 格式報告
syncindex report --format csv

# 指定報告輸出路徑
syncindex report --format markdown --output ./reports/my-report.md
```

---

## 💡 設計思路與迭代規劃

### 設計哲學

SyncIndex 的設計遵循以下核心原則：

- **簡潔至上**：不引入任何外部依賴，用 Python 標準函式庫建構全部功能
- **約定優於配置**：提供合理的預設值，開箱即用，同時保留充分的可自訂性
- **增量優先**：透過雜湊 + 時間戳雙校驗，最小化不必要的檔案掃描與 I/O 操作
- **可擴展性**：外掛化的資料來源架構，方便社群貢獻新的資料來源類型

### 架構概覽

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   CLI 層     │────▶│  同步引擎     │────▶│  索引儲存     │
│  (cli.py)    │     │(sync_engine) │     │(indexer.py)  │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                    ┌──────▼───────┐
                    │  資料來源層   │
                    │ (sources.py) │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │FileSystem│ │   JSON   │ │   CSV    │
        └──────────┘ └──────────┘ └──────────┘
```

### 未來規劃

- [ ] 🗄️ **資料庫資料來源**：支援 SQLite、PostgreSQL 等資料庫直連
- [ ] 🌐 **遠端資料來源**：支援 S3、FTP、HTTP 等遠端儲存
- [ ] 🔄 **雙向同步**：支援來源與目標之間的雙向變更同步
- [ ] 📡 **Webhook 通知**：同步完成後推送通知至 Slack、釘釘等
- [ ] 🖥️ **Web UI**：提供視覺化設定與狀態監控面板
- [ ] 📦 **打包分發**：發佈至 PyPI，支援 `pip install syncindex`

---

## 📦 安裝與部署

### 環境需求

- **Python** >= 3.8
- **作業系統**：跨平台支援（Linux / macOS / Windows）
- **外部依賴**：無

### 安裝方式

```bash
# 從 GitHub 安裝（推薦）
pip install git+https://github.com/gitstq/SyncIndex.git

# 克隆後開發模式安裝
git clone https://github.com/gitstq/SyncIndex.git
cd SyncIndex
pip install -e .

# 執行測試以驗證安裝
python -m pytest tests/ -v
```

### 解除安裝

```bash
pip uninstall syncindex
```

---

## 🤝 貢獻指南

我們歡迎並感謝每一位貢獻者！無論你是提交 Bug 回報、改進文件，還是貢獻程式碼，都是對專案的寶貴支持。

### 貢獻流程

1. **Fork** 本倉庫
2. 建立特性分支：`git checkout -b feature/your-feature-name`
3. 提交變更：`git commit -m "feat: add your feature description"`
4. 推送分支：`git push origin feature/your-feature-name`
5. 提交 **Pull Request**

### 程式碼規範

- 遵循 **PEP 8** 編碼規範
- 提交資訊遵循 **Conventional Commits** 格式
- 新功能請附帶對應的**單元測試**
- 保持 **零外部依賴**的原則

### 回報問題

如果在使用過程中遇到任何問題，請透過 [GitHub Issues](https://github.com/gitstq/SyncIndex/issues) 提交，並附上以下資訊：

- 作業系統與 Python 版本
- 完整的錯誤資訊或例外堆疊
- 重現問題的最小設定範例

---

## 📄 開源協議

本專案基於 **[MIT License](https://opensource.org/licenses/MIT)** 開源。

```
MIT License

Copyright (c) 2024 SyncIndex Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```

---

<h1 id="english">English</h1>

<p align="center">
  <strong>SyncIndex</strong> — Lightweight Incremental Data Sync & Index Engine CLI<br/>
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue" alt="Python 3.8+"/>
  <img src="https://img.shields.io/badge/Dependencies-Zero-green" alt="Zero Dependencies"/>
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="MIT License"/>
  <img src="https://img.shields.io/badge/Tests-65%20passed-success" alt="65 Tests"/>
</p>

---

## 🎉 About SyncIndex

**SyncIndex** is a lightweight incremental data synchronization and indexing engine built for the command line. It intelligently tracks changes across your data sources and syncs only what has changed, dramatically reducing unnecessary I/O overhead.

Whether you're maintaining file indexes for code repositories, tracking change history in data directories, or monitoring critical files in real time — **SyncIndex** delivers precise, efficient synchronization with minimal resource consumption.

> 💡 **Core Philosophy**: Solve real-world data sync problems with the simplest possible tool. Zero external dependencies. Ready to use out of the box.

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 📋 **YAML/JSON Driven Config** | Define data sources and sync strategies via declarative config files — no more tangled CLI flags |
| 🔌 **Multi-Source Support** | Built-in adapters for **FileSystem**, **JSON**, and **CSV** data sources covering mainstream use cases |
| 🔍 **Incremental Change Detection** | Dual verification with **hash + timestamp** to accurately identify new, modified, and deleted files |
| 👀 **Real-Time File Monitoring** | Watchdog-based mode that auto-triggers sync on file changes with millisecond-level responsiveness |
| 🧩 **Plugin-Based Architecture** | Pluggable data source design makes it easy to extend with custom source types |
| 📊 **Rich Report Generation** | Export sync reports in **Markdown / JSON / CSV** formats |
| 🪶 **Zero External Dependencies** | Built entirely with the Python standard library — runs on **Python 3.8+** with no third-party packages |
| ✅ **Comprehensive Test Coverage** | **65 unit tests** ensuring the stability and reliability of core logic |

---

## 🚀 Quick Start

### 1. Installation

```bash
# Option A: Install directly from GitHub via pip
pip install git+https://github.com/gitstq/SyncIndex.git

# Option B: Clone the repo and install in development mode
git clone https://github.com/gitstq/SyncIndex.git
cd SyncIndex
pip install -e .
```

### 2. Initialize Configuration

```bash
syncindex init
```

This generates a default `syncindex.json` config file in the current directory. Customize the data sources and output options to fit your needs.

### 3. Run Your First Sync

```bash
syncindex sync
```

On the first run, SyncIndex scans all configured data sources and builds a complete file index. Subsequent runs automatically perform **incremental sync**, processing only files that have changed.

### 4. Check Sync Status

```bash
syncindex status
```

### 5. Generate a Sync Report

```bash
syncindex report
```

> 🎉 **Congratulations!** You've mastered the basics of SyncIndex. Read on for the detailed usage guide to unlock more advanced features.

---

## 📖 Detailed Usage Guide

### CLI Commands Overview

| Command | Description | Example |
|---------|-------------|---------|
| `syncindex init` | Initialize a config file | `syncindex init` |
| `syncindex sync` | Execute incremental sync | `syncindex sync --config my-config.json` |
| `syncindex watch` | Start real-time monitoring | `syncindex watch --interval 3` |
| `syncindex status` | View current index status | `syncindex status` |
| `syncindex report` | Generate a sync report | `syncindex report --format csv` |

### Configuration File Reference

Here is a complete `syncindex.json` configuration example:

```json
{
  "version": "1.0",
  "sources": [
    {
      "type": "filesystem",
      "name": "my-project",
      "path": "./src",
      "recursive": true,
      "include": ["*.py", "*.js"],
      "exclude": ["__pycache__", "node_modules"]
    }
  ],
  "output": {
    "index_path": ".syncindex.json",
    "report_format": "markdown",
    "report_path": "./sync-report.md"
  },
  "options": {
    "hash_algorithm": "md5",
    "watch_interval": 2
  }
}
```

#### Field Reference

**`version`** — Config file version. Currently `"1.0"`.

**`sources`** — List of data sources. Multiple sources can be configured simultaneously:

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Data source type: `filesystem`, `json`, or `csv` |
| `name` | string | Source name used for identification and report display |
| `path` | string | Path to the data source (file or directory) |
| `recursive` | bool | Whether to recursively scan subdirectories (filesystem only) |
| `include` | list | File inclusion patterns (glob syntax) |
| `exclude` | list | File exclusion patterns (glob syntax) |

**`output`** — Output configuration:

| Field | Type | Description |
|-------|------|-------------|
| `index_path` | string | Path where the index file is stored |
| `report_format` | string | Report format: `markdown`, `json`, or `csv` |
| `report_path` | string | Path where the report file is written |

**`options`** — Global options:

| Field | Type | Description |
|-------|------|-------------|
| `hash_algorithm` | string | Hash algorithm: `md5`, `sha1`, or `sha256` |
| `watch_interval` | int | File monitoring poll interval (seconds) |

### Real-Time Watch Mode

```bash
# Start watching with default 2-second interval
syncindex watch

# Custom watch interval of 5 seconds
syncindex watch --interval 5
```

Once watch mode is active, SyncIndex continuously monitors your data source directories for file changes. When it detects additions, modifications, or deletions, it **automatically triggers an incremental sync** and updates the index file.

> ⚡ **Tip**: For CI/CD pipelines, use `syncindex sync` in single-run mode. For local development, `syncindex watch` real-time mode is recommended.

### Report Generation

```bash
# Generate Markdown report (default)
syncindex report

# Generate JSON report
syncindex report --format json

# Generate CSV report
syncindex report --format csv

# Specify custom output path
syncindex report --format markdown --output ./reports/my-report.md
```

---

## 💡 Design Philosophy & Roadmap

### Design Principles

SyncIndex is built on the following core principles:

- **Simplicity First**: No external dependencies — everything is built with the Python standard library
- **Convention Over Configuration**: Sensible defaults out of the box, with full customizability when needed
- **Incremental by Default**: Hash + timestamp dual verification minimizes unnecessary file scans and I/O
- **Extensibility**: Plugin-based data source architecture makes it easy for the community to contribute new source types

### Architecture Overview

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  CLI Layer   │────▶│  Sync Engine │────▶│ Index Store  │
│  (cli.py)    │     │(sync_engine) │     │(indexer.py)  │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                    ┌──────▼───────┐
                    │ Source Layer  │
                    │ (sources.py) │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │FileSystem│ │   JSON   │ │   CSV    │
        └──────────┘ └──────────┘ └──────────┘
```

### Roadmap

- [ ] 🗄️ **Database Sources**: Direct support for SQLite, PostgreSQL, and more
- [ ] 🌐 **Remote Sources**: S3, FTP, HTTP, and other remote storage backends
- [ ] 🔄 **Bidirectional Sync**: Two-way change synchronization between source and target
- [ ] 📡 **Webhook Notifications**: Push notifications to Slack, DingTalk, etc. after sync
- [ ] 🖥️ **Web UI**: Visual configuration and status monitoring dashboard
- [ ] 📦 **PyPI Distribution**: Publish to PyPI for `pip install syncindex`

---

## 📦 Installation & Deployment

### Requirements

- **Python** >= 3.8
- **Operating System**: Cross-platform (Linux / macOS / Windows)
- **External Dependencies**: None

### Installation

```bash
# Install from GitHub (recommended)
pip install git+https://github.com/gitstq/SyncIndex.git

# Clone and install in development mode
git clone https://github.com/gitstq/SyncIndex.git
cd SyncIndex
pip install -e .

# Run tests to verify the installation
python -m pytest tests/ -v
```

### Uninstall

```bash
pip uninstall syncindex
```

---

## 🤝 Contributing

We welcome and appreciate every contributor! Whether you're filing bug reports, improving documentation, or submitting code — it all helps make SyncIndex better.

### How to Contribute

1. **Fork** this repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Commit your changes: `git commit -m "feat: add your feature description"`
4. Push the branch: `git push origin feature/your-feature-name`
5. Submit a **Pull Request**

### Code Standards

- Follow **PEP 8** coding conventions
- Use **Conventional Commits** format for commit messages
- Include **unit tests** for any new features
- Maintain the **zero external dependency** principle

### Reporting Issues

If you encounter any issues, please file a report via [GitHub Issues](https://github.com/gitstq/SyncIndex/issues) with the following information:

- Operating system and Python version
- Full error message or exception stack trace
- Minimal config example to reproduce the issue

---

## 📄 License

This project is released under the **[MIT License](https://opensource.org/licenses/MIT)**.

```
MIT License

Copyright (c) 2024 SyncIndex Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```
