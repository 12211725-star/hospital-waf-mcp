"""
知识库模块化管理器
支持核心知识库 + 可插拔模块
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class KnowledgeBaseManager:
    """知识库管理器"""
    
    def __init__(self, product_dir: str, product_name: str):
        """
        初始化知识库管理器
        
        Args:
            product_dir: 产品根目录
            product_name: 产品名称
        """
        self.product_dir = Path(product_dir)
        self.product_name = product_name
        self.kb_dir = self.product_dir / "knowledge-base"
        self.core_dir = self.kb_dir / "core"
        self.modules_dir = self.kb_dir / "modules"
        self.active_dir = self.kb_dir / "active"
        
        # 确保目录存在
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保所有必需的目录存在"""
        self.kb_dir.mkdir(parents=True, exist_ok=True)
        self.core_dir.mkdir(parents=True, exist_ok=True)
        self.modules_dir.mkdir(parents=True, exist_ok=True)
        self.active_dir.mkdir(parents=True, exist_ok=True)
    
    # ==================== 核心知识库管理 ====================
    
    def init_core_knowledge_base(self, core_rules: List[Dict], metadata: Dict = None):
        """
        初始化核心知识库
        
        Args:
            core_rules: 核心规则列表
            metadata: 元数据
        """
        # 保存核心规则
        core_rules_file = self.core_dir / "core_rules.json"
        with open(core_rules_file, 'w', encoding='utf-8') as f:
            json.dump({
                "version": "1.0.0",
                "product": self.product_name,
                "create_time": datetime.now().isoformat(),
                "rules": core_rules,
                "rules_count": len(core_rules)
            }, f, ensure_ascii=False, indent=2)
        
        # 保存元数据
        core_metadata_file = self.core_dir / "metadata.json"
        default_metadata = {
            "type": "core",
            "name": f"{self.product_name} 核心知识库",
            "description": "内置核心规则，不可删除",
            "version": "1.0.0",
            "editable": False,
            "deletable": False,
            "create_time": datetime.now().isoformat()
        }
        if metadata:
            default_metadata.update(metadata)
        
        with open(core_metadata_file, 'w', encoding='utf-8') as f:
            json.dump(default_metadata, f, ensure_ascii=False, indent=2)
        
        logger.info(f"核心知识库初始化完成: {len(core_rules)} 条规则")
    
    def load_core_rules(self) -> List[Dict]:
        """加载核心规则"""
        core_rules_file = self.core_dir / "core_rules.json"
        if not core_rules_file.exists():
            return []
        
        with open(core_rules_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('rules', [])
    
    def count_core_rules(self) -> int:
        """统计核心规则数量"""
        return len(self.load_core_rules())
    
    # ==================== 模块管理 ====================
    
    def list_modules(self) -> List[Dict]:
        """列出所有已安装的模块"""
        modules = []
        
        for module_dir in self.modules_dir.iterdir():
            if module_dir.is_dir():
                module_json = module_dir / "module.json"
                if module_json.exists():
                    with open(module_json, 'r', encoding='utf-8') as f:
                        module_info = json.load(f)
                        module_info['installed'] = True
                        modules.append(module_info)
        
        return modules
    
    def get_module(self, module_id: str) -> Optional[Dict]:
        """获取模块详情"""
        module_dir = self.modules_dir / module_id
        if not module_dir.exists():
            return None
        
        module_json = module_dir / "module.json"
        if not module_json.exists():
            return None
        
        with open(module_json, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def install_module(self, module_id: str, module_config: Dict, rules: List[Dict], metadata: Dict = None):
        """
        安装知识库模块
        
        Args:
            module_id: 模块ID
            module_config: 模块配置
            rules: 模块规则
            metadata: 模块元数据
        """
        module_dir = self.modules_dir / module_id
        module_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存模块配置
        module_json = module_dir / "module.json"
        with open(module_json, 'w', encoding='utf-8') as f:
            json.dump(module_config, f, ensure_ascii=False, indent=2)
        
        # 保存模块规则
        rules_json = module_dir / "rules.json"
        with open(rules_json, 'w', encoding='utf-8') as f:
            json.dump({
                "module_id": module_id,
                "version": module_config.get("version", "1.0.0"),
                "rules": rules,
                "rules_count": len(rules)
            }, f, ensure_ascii=False, indent=2)
        
        # 保存模块元数据
        metadata_json = module_dir / "metadata.json"
        default_metadata = {
            "module_id": module_id,
            "install_time": datetime.now().isoformat(),
            "active": False
        }
        if metadata:
            default_metadata.update(metadata)
        
        with open(metadata_json, 'w', encoding='utf-8') as f:
            json.dump(default_metadata, f, ensure_ascii=False, indent=2)
        
        logger.info(f"模块安装成功: {module_id}")
    
    def load_module_rules(self, module_id: str) -> List[Dict]:
        """加载模块规则"""
        module_dir = self.modules_dir / module_id
        rules_json = module_dir / "rules.json"
        
        if not rules_json.exists():
            return []
        
        with open(rules_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('rules', [])
    
    def uninstall_module(self, module_id: str) -> bool:
        """卸载模块"""
        # 不能卸载核心模块
        if module_id == "hospital-basic":
            logger.warning(f"不能卸载内置模块: {module_id}")
            return False
        
        module_dir = self.modules_dir / module_id
        if not module_dir.exists():
            return False
        
        # 先停用模块
        self.deactivate_module(module_id)
        
        # 删除模块目录
        shutil.rmtree(module_dir)
        logger.info(f"模块卸载成功: {module_id}")
        return True
    
    # ==================== 激活管理 ====================
    
    def load_manifest(self) -> Dict:
        """加载激活清单"""
        manifest_file = self.active_dir / "manifest.json"
        
        if not manifest_file.exists():
            # 创建默认清单
            default_manifest = {
                "version": "1.0.0",
                "product": self.product_name,
                "active_modules": ["hospital-basic"],  # 默认激活基础模块
                "last_update": datetime.now().isoformat()
            }
            self.save_manifest(default_manifest)
            return default_manifest
        
        with open(manifest_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_manifest(self, manifest: Dict):
        """保存激活清单"""
        manifest['last_update'] = datetime.now().isoformat()
        manifest_file = self.active_dir / "manifest.json"
        
        with open(manifest_file, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    def get_active_modules(self) -> List[str]:
        """获取已激活的模块列表"""
        manifest = self.load_manifest()
        return manifest.get('active_modules', [])
    
    def activate_module(self, module_id: str) -> bool:
        """激活模块"""
        # 检查模块是否存在
        module = self.get_module(module_id)
        if not module:
            logger.warning(f"模块不存在: {module_id}")
            return False
        
        # 更新清单
        manifest = self.load_manifest()
        active_modules = manifest.get('active_modules', [])
        
        if module_id not in active_modules:
            active_modules.append(module_id)
            manifest['active_modules'] = active_modules
            self.save_manifest(manifest)
        
        # 更新模块元数据
        self._update_module_active_status(module_id, True)
        
        # 合并知识库
        self.merge_active_modules()
        
        logger.info(f"模块激活成功: {module_id}")
        return True
    
    def deactivate_module(self, module_id: str) -> bool:
        """停用模块"""
        # 不能停用核心模块
        if module_id == "hospital-basic":
            logger.warning(f"不能停用内置模块: {module_id}")
            return False
        
        # 更新清单
        manifest = self.load_manifest()
        active_modules = manifest.get('active_modules', [])
        
        if module_id in active_modules:
            active_modules.remove(module_id)
            manifest['active_modules'] = active_modules
            self.save_manifest(manifest)
        
        # 更新模块元数据
        self._update_module_active_status(module_id, False)
        
        # 合并知识库
        self.merge_active_modules()
        
        logger.info(f"模块停用成功: {module_id}")
        return True
    
    def _update_module_active_status(self, module_id: str, active: bool):
        """更新模块激活状态"""
        metadata_file = self.modules_dir / module_id / "metadata.json"
        
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            metadata['active'] = active
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    # ==================== 知识库合并 ====================
    
    def merge_active_modules(self) -> Dict:
        """合并所有激活的知识库"""
        # 加载核心规则
        core_rules = self.load_core_rules()
        
        # 加载所有激活的模块规则
        manifest = self.load_manifest()
        active_modules = manifest.get('active_modules', [])
        
        all_rules = list(core_rules)
        module_contributions = {}
        
        for module_id in active_modules:
            module_rules = self.load_module_rules(module_id)
            all_rules.extend(module_rules)
            module_contributions[module_id] = len(module_rules)
        
        # 去重（基于规则ID）
        unique_rules = {}
        for rule in all_rules:
            rule_id = rule.get('rule_id', rule.get('id', str(hash(str(rule)))))
            if rule_id not in unique_rules:
                unique_rules[rule_id] = rule
        
        merged_rules = list(unique_rules.values())
        
        # 保存合并后的规则
        active_rules_file = self.active_dir / "active_rules.json"
        with open(active_rules_file, 'w', encoding='utf-8') as f:
            json.dump({
                "version": "1.0.0",
                "product": self.product_name,
                "merge_time": datetime.now().isoformat(),
                "total_rules": len(merged_rules),
                "core_rules": len(core_rules),
                "active_modules": active_modules,
                "module_contributions": module_contributions,
                "rules": merged_rules
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"知识库合并完成: 核心规则 {len(core_rules)} 条, 总计 {len(merged_rules)} 条规则")
        
        return {
            "total_rules": len(merged_rules),
            "core_rules": len(core_rules),
            "active_modules": active_modules,
            "module_contributions": module_contributions
        }
    
    def load_active_rules(self) -> List[Dict]:
        """加载激活的规则"""
        active_rules_file = self.active_dir / "active_rules.json"
        
        if not active_rules_file.exists():
            # 如果没有合并后的规则，执行合并
            self.merge_active_modules()
        
        with open(active_rules_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('rules', [])
    
    # ==================== 状态查询 ====================
    
    def get_status(self) -> Dict:
        """获取知识库状态"""
        core_rules = self.load_core_rules()
        manifest = self.load_manifest()
        active_modules = manifest.get('active_modules', [])
        
        # 统计总规则数
        total_rules = len(core_rules)
        for module_id in active_modules:
            module_rules = self.load_module_rules(module_id)
            total_rules += len(module_rules)
        
        return {
            "product": self.product_name,
            "core_rules": len(core_rules),
            "active_modules": active_modules,
            "total_modules": len(self.list_modules()),
            "total_rules": total_rules,
            "last_update": manifest.get('last_update', '')
        }


# 导出函数（供其他模块调用）
def create_kb_manager(base_dir: str, product_name: str = "产品") -> KnowledgeBaseManager:
    """创建知识库管理器实例"""
    return KnowledgeBaseManager(base_dir, product_name)
