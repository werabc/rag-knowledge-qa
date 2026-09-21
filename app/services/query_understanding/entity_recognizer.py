"""
实体识别
"""

import re
from typing import List, Dict, Any, Optional

class EntityRecognizer:
    """实体识别器"""
    
    def __init__(self):
        """初始化实体识别器"""
        # 实体类型正则表达式
        self.entity_patterns = {
            "person": [
                r"[\u4e00-\u9fff]{2,4}",  # 中文人名
                r"[A-Z][a-z]+ [A-Z][a-z]+",  # 英文人名
            ],
            "organization": [
                r"[\u4e00-\u9fff]+(?:公司|集团|大学|学院|机构|组织)",
                r"[A-Z][a-z]+ (?:Inc|Corp|Ltd|LLC|Co|University)",
            ],
            "location": [
                r"[\u4e00-\u9fff]+(?:市|省|区|县|镇|路|街)",
                r"[A-Z][a-z]+ (?:City|State|Country|Street|Road)",
            ],
            "time": [
                r"\d{4}年\d{1,2}月\d{1,2}日",
                r"\d{4}-\d{2}-\d{2}",
                r"\d{4}/\d{2}/\d{2}",
                r"\d{1,2}月\d{1,2}日",
            ],
            "number": [
                r"\d+(?:\.\d+)?(?:%|％|元|美元|人民币|个|件|条|项)",
                r"\d+(?:\.\d+)?(?:GB|MB|KB|TB|Hz|MHz|GHz)",
            ],
            "technology": [
                r"[\u4e00-\u9fff]+(?:技术|算法|模型|系统|平台|框架)",
                r"[A-Z][a-zA-Z]+(?:API|SDK|Framework|Library|Tool)",
            ],
            "concept": [
                r"[\u4e00-\u9fff]+(?:概念|原理|理论|方法|策略|机制)",
                r"[A-Z][a-zA-Z]+(?:Theory|Concept|Method|Strategy|Mechanism)",
            ]
        }
        
        # 实体重要性权重
        self.entity_importance = {
            "technology": 0.9,
            "concept": 0.8,
            "organization": 0.7,
            "person": 0.6,
            "location": 0.5,
            "time": 0.4,
            "number": 0.3
        }
    
    async def recognize_entities(self, query: str) -> List[Dict[str, Any]]:
        """
        识别查询中的实体
        
        Args:
            query: 查询文本
            
        Returns:
            List[Dict[str, Any]]: 识别到的实体列表
        """
        entities = []
        
        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, query)
                
                for match in matches:
                    entity_text = match.group()
                    
                    # 检查是否已存在相同实体
                    if not self._entity_exists(entities, entity_text):
                        entity = {
                            "text": entity_text,
                            "type": entity_type,
                            "start_pos": match.start(),
                            "end_pos": match.end(),
                            "importance": self.entity_importance.get(entity_type, 0.5),
                            "confidence": 0.8  # 默认置信度
                        }
                        entities.append(entity)
        
        # 按重要性排序
        entities.sort(key=lambda x: x["importance"], reverse=True)
        
        return entities
    
    def _entity_exists(self, entities: List[Dict], entity_text: str) -> bool:
        """检查实体是否已存在"""
        for entity in entities:
            if entity["text"] == entity_text:
                return True
        return False
    
    async def link_entities_to_knowledge_base(self, entities: List[Dict],
                                             knowledge_base=None) -> List[Dict]:
        """
        实体链接到知识库
        
        Args:
            entities: 实体列表
            knowledge_base: 知识库
            
        Returns:
            List[Dict]: 链接后的实体列表
        """
        if not knowledge_base:
            return entities
        
        linked_entities = []
        
        for entity in entities:
            linked_entity = entity.copy()
            
            # 在知识库中搜索相似实体
            try:
                candidates = await knowledge_base.search(
                    entity["text"],
                    top_k=3,
                    similarity_threshold=0.8
                )
                
                if candidates:
                    best_match = candidates[0]
                    linked_entity["kb_id"] = best_match.get("id")
                    linked_entity["kb_name"] = best_match.get("name")
                    linked_entity["linking_confidence"] = best_match.get("similarity", 0)
                    linked_entity["linked"] = True
                else:
                    linked_entity["linked"] = False
                    
            except Exception as e:
                print(f"实体链接失败: {e}")
                linked_entity["linked"] = False
            
            linked_entities.append(linked_entity)
        
        return linked_entities
    
    def get_entity_types(self) -> List[str]:
        """获取支持的实体类型"""
        return list(self.entity_patterns.keys())