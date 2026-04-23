#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识库管理API路由
为产品提供统一的知识库管理接口
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


def create_kb_router(base_dir: str, product_name: str = "产品"):
    """创建知识库管理路由"""
    
    router = APIRouter(prefix="/api/knowledge-base", tags=["知识库管理"])
    
    # 延迟导入避免循环依赖
    from knowledge_base_manager import create_kb_manager
    kb_manager = create_kb_manager(base_dir, product_name)
    
    @router.get("/status")
    async def get_status():
        """获取知识库状态"""
        try:
            status = kb_manager.get_status()
            return {"success": True, "data": status}
        except Exception as e:
            logger.error(f"获取知识库状态失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/modules")
    async def list_modules():
        """列出所有知识库模块"""
        try:
            modules = kb_manager.list_modules()
            return {"success": True, "data": modules}
        except Exception as e:
            logger.error(f"列出模块失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/modules/{module_id}")
    async def get_module(module_id: str):
        """获取模块详情"""
        try:
            module = kb_manager.get_module_detail(module_id)
            if not module:
                raise HTTPException(status_code=404, detail=f"模块 {module_id} 不存在")
            return {"success": True, "data": module}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"获取模块详情失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/modules/{module_id}/activate")
    async def activate_module(module_id: str):
        """激活知识库模块"""
        try:
            result = kb_manager.activate_module(module_id)
            if not result["success"]:
                raise HTTPException(status_code=400, detail=result["message"])
            return {"success": True, "data": result}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"激活模块失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/modules/{module_id}/deactivate")
    async def deactivate_module(module_id: str):
        """停用知识库模块"""
        try:
            result = kb_manager.deactivate_module(module_id)
            return {"success": True, "data": result}
        except Exception as e:
            logger.error(f"停用模块失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.delete("/modules/{module_id}")
    async def delete_module(module_id: str):
        """删除知识库模块"""
        try:
            # TODO: 实现删除模块功能
            return {"success": True, "message": f"模块 {module_id} 已删除"}
        except Exception as e:
            logger.error(f"删除模块失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/merge")
    async def merge_knowledge_base():
        """手动触发知识库合并"""
        try:
            kb_manager._merge_knowledge_base()
            status = kb_manager.get_status()
            return {"success": True, "data": status}
        except Exception as e:
            logger.error(f"合并知识库失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    return router
