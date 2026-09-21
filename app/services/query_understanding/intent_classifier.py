"""
意图识别
"""

import re
from typing import List, Dict, Any, Optional

class IntentClassifier:
    """查询意图分类器"""
    
    def __init__(self):
        """初始化意图分类器"""
        self.intent_patterns = {
            "factual": [
                r"什么是", r"是什么", r"谁是", r"哪里", r"什么时候",
                r"多少", r"几个", r"哪个", r"怎么算", r"定义",
                r"what is", r"who is", r"where", r"when", r"how many",
                r"which", r"define", r"definition"
            ],
            "explanatory": [
                r"为什么", r"如何", r"怎样", r"解释", r"说明",
                r"原因", r"原理", r"机制", r"过程",
                r"why", r"how", r"explain", r"reason", r"mechanism",
                r"process", r"principle"
            ],
            "procedural": [
                r"怎么做", r"步骤", r"方法", r"操作", r"使用",
                r"设置", r"配置", r"安装", r"部署",
                r"how to", r"steps", r"method", r"procedure", r"use",
                r"setup", r"configure", r"install", r"deploy"
            ],
            "comparative": [
                r"比较", r"对比", r"区别", r"差异", r"优缺点",
                r"哪个好", r"更好", r"更好", r"选择",
                r"compare", r"comparison", r"difference", r"pros and cons",
                r"which is better", r"better", r"choose"
            ],
            "exploratory": [
                r"关于", r"介绍", r"概述", r"总结", r"有哪些",
                r"包括", r"包含", r"涉及",
                r"about", r"introduction", r"overview", r"summary",
                r"what are", r"include", r"involves"
            ]
        }
        
        # 意图权重
        self.intent_weights = {
            "factual": 1.0,
            "explanatory": 0.9,
            "procedural": 0.8,
            "comparative": 0.7,
            "exploratory": 0.6
        }
    
    async def classify_intent(self, query: str) -> Dict[str, Any]:
        """
        识别查询意图
        
        Args:
            query: 查询文本
            
        Returns:
            Dict[str, Any]: 意图分类结果
        """
        query_lower = query.lower()
        
        # 计算每个意图的匹配分数
        intent_scores = {}
        
        for intent, patterns in self.intent_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    score += 1
            
            # 归一化分数
            if patterns:
                intent_scores[intent] = score / len(patterns)
            else:
                intent_scores[intent] = 0
        
        # 应用意图权重
        for intent in intent_scores:
            intent_scores[intent] *= self.intent_weights.get(intent, 1.0)
        
        # 找到最高分的意图
        if intent_scores:
            primary_intent = max(intent_scores, key=intent_scores.get)
            primary_score = intent_scores[primary_intent]
        else:
            primary_intent = "exploratory"
            primary_score = 0.5
        
        # 找到次要意图（如果存在）
        secondary_intent = None
        secondary_score = 0
        for intent, score in intent_scores.items():
            if intent != primary_intent and score > secondary_score:
                secondary_intent = intent
                secondary_score = score
        
        return {
            "primary_intent": primary_intent,
            "primary_score": primary_score,
            "secondary_intent": secondary_intent,
            "secondary_score": secondary_score,
            "all_scores": intent_scores,
            "confidence": primary_score
        }
    
    def get_intent_description(self, intent: str) -> str:
        """获取意图描述"""
        descriptions = {
            "factual": "事实性查询 - 寻找具体事实或数据",
            "explanatory": "解释性查询 - 寻求解释或理解概念",
            "procedural": "操作性查询 - 寻找操作步骤或方法",
            "comparative": "比较性查询 - 比较不同事物",
            "exploratory": "探索性查询 - 探索某个主题"
        }
        
        return descriptions.get(intent, "未知意图")