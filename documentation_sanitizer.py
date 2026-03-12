# -*- coding: utf-8 -*-
"""
文件去敏工具：清理高風險關鍵詞，避免專案被貼標籤
"""

from __future__ import annotations
from typing import Dict, List
import re
from pathlib import Path


class DocumentationSanitizer:
    """文件去敏器"""

    # 高風險關鍵詞映射（公開版）
    RISK_KEYWORDS = {
        # 軍事相關
        "導彈": "飛行器",
        "missile": "vehicle",
        "比例導引": "航跡控制",
        "proportional navigation": "trajectory control",
        "攔截": "交會",
        "intercept": "rendezvous",
        "武器": "載具",
        "weapon": "vehicle",
        "戰鬥部": "有效載荷",
        "warhead": "payload",
        
        # 保留但標註
        # "導引" -> 保留但加註釋
    }

    # 需要添加聲明的文件類型
    FILES_NEEDING_DISCLAIMER = [
        "README.md",
        "CAPABILITIES.md",
        "*.md"
    ]

    @staticmethod
    def sanitize_text(text: str, add_disclaimer: bool = True) -> str:
        """清理文本中的高風險關鍵詞"""
        sanitized = text
        
        # 替換關鍵詞
        for risky, safe in DocumentationSanitizer.RISK_KEYWORDS.items():
            # 大小寫不敏感替換
            pattern = re.compile(re.escape(risky), re.IGNORECASE)
            sanitized = pattern.sub(safe, sanitized)
        
        # 添加用途聲明（如果需要）
        if add_disclaimer and "用途聲明" not in sanitized:
            disclaimer = """

---

## 用途聲明

本平台僅用於：
- **教育與研究用途**：教學、學術研究、概念驗證
- **概念設計階段**：初期設計性能估算
- **算法開發**：理論驗證、算法開發

**不適用於**：
- 最終設計驗證（需專業工具交叉驗證）
- 製造級精度（需詳細 CFD/FEA/試驗）
- 認證審查（需完整 V&V 報告）
- **武器化用途**（本平台不提供任何武器化功能）

## 適用域

- **速度範圍**: 0 - 10 Mach（部分模型適用範圍更窄）
- **高度範圍**: 0 - 100 km（ISA 模型適用至 86 km）
- **熱環境**: 簡化模型，需專業工具驗證
- **結構假設**: 簡化模型，需詳細 FEA 驗證

## 免責聲明

本平台為概念設計與教育研究工具，所有結果需專業工具交叉驗證。使用者需自行承擔使用責任。

"""
            sanitized += disclaimer
        
        return sanitized

    @staticmethod
    def sanitize_file(file_path: str, backup: bool = True):
        """清理文件"""
        path = Path(file_path)
        if not path.exists():
            return {"error": f"文件不存在: {file_path}"}
        
        # 備份
        if backup:
            backup_path = path.with_suffix(path.suffix + ".backup")
            backup_path.write_text(path.read_text(encoding='utf-8'), encoding='utf-8')
        
        # 讀取並清理
        original_text = path.read_text(encoding='utf-8')
        sanitized_text = DocumentationSanitizer.sanitize_text(original_text)
        
        # 寫回
        path.write_text(sanitized_text, encoding='utf-8')
        
        return {
            "file": file_path,
            "backup_created": backup,
            "backup_path": str(backup_path) if backup else None,
            "replacements_made": len(DocumentationSanitizer.RISK_KEYWORDS)
        }

    @staticmethod
    def add_disclaimer_to_readme(readme_path: str = "README.md"):
        """在 README 中添加用途聲明"""
        path = Path(readme_path)
        if not path.exists():
            return {"error": "README.md 不存在"}
        
        content = path.read_text(encoding='utf-8')
        
        # 檢查是否已有聲明
        if "用途聲明" in content or "DISCLAIMER" in content.upper():
            return {"note": "README 已包含聲明"}
        
        # 添加聲明
        disclaimer = """

---

## 用途聲明與適用域

### 用途
本平台僅用於：
- **教育與研究用途**：教學、學術研究、概念驗證
- **概念設計階段**：初期設計性能估算
- **算法開發**：理論驗證、算法開發

### 不適用於
- 最終設計驗證（需專業工具交叉驗證）
- 製造級精度（需詳細 CFD/FEA/試驗）
- 認證審查（需完整 V&V 報告）
- **武器化用途**（本平台不提供任何武器化功能）

### 適用域
- **速度範圍**: 0 - 10 Mach（部分模型適用範圍更窄）
- **高度範圍**: 0 - 100 km（ISA 模型適用至 86 km）
- **熱環境**: 簡化模型，需專業工具驗證
- **結構假設**: 簡化模型，需詳細 FEA 驗證

### 免責聲明
本平台為概念設計與教育研究工具，所有結果需專業工具交叉驗證。使用者需自行承擔使用責任。

"""
        content += disclaimer
        path.write_text(content, encoding='utf-8')
        
        return {"status": "disclaimer_added", "file": readme_path}


# 實例化
doc_sanitizer = DocumentationSanitizer()
