"""
检索质量评估
"""

import numpy as np
from typing import List, Dict, Any, Optional

class RetrievalEvaluator:
    """检索质量评估器"""
    
    def __init__(self):
        """初始化评估器"""
        self.metrics = {
            "precision@k": self.precision_at_k,
            "recall@k": self.recall_at_k,
            "ndcg@k": self.ndcg_at_k,
            "mrr": self.mean_reciprocal_rank,
            "map": self.mean_average_precision,
            "hit_rate": self.hit_rate
        }
    
    def evaluate(self, retrieved_docs: List[Dict], relevant_docs: List[str], 
                k: int = 10) -> Dict[str, float]:
        """
        评估检索质量
        
        Args:
            retrieved_docs: 检索到的文档列表
            relevant_docs: 相关文档ID列表
            k: 评估的top-k位置
            
        Returns:
            Dict[str, float]: 评估指标字典
        """
        results = {}
        
        # 计算各个指标
        for metric_name, metric_func in self.metrics.items():
            try:
                if metric_name.endswith("@k"):
                    results[metric_name] = metric_func(retrieved_docs, relevant_docs, k)
                else:
                    results[metric_name] = metric_func(retrieved_docs, relevant_docs)
            except Exception as e:
                print(f"计算指标 {metric_name} 失败: {e}")
                results[metric_name] = 0.0
        
        # 计算F1分数
        precision = results.get("precision@k", 0.0)
        recall = results.get("recall@k", 0.0)
        if precision + recall > 0:
            results["f1@k"] = 2 * precision * recall / (precision + recall)
        else:
            results["f1@k"] = 0.0
        
        return results
    
    def precision_at_k(self, retrieved: List[Dict], relevant: List[str], k: int) -> float:
        """计算Precision@k"""
        if not retrieved or k <= 0:
            return 0.0
        
        # 获取top-k结果
        top_k_docs = retrieved[:k]
        
        # 计算相关文档数量
        relevant_count = 0
        for doc in top_k_docs:
            doc_id = doc.get("doc_id") or doc.get("metadata", {}).get("doc_id")
            if doc_id in relevant:
                relevant_count += 1
        
        return relevant_count / k
    
    def recall_at_k(self, retrieved: List[Dict], relevant: List[str], k: int) -> float:
        """计算Recall@k"""
        if not relevant or k <= 0:
            return 0.0
        
        # 获取top-k结果
        top_k_docs = retrieved[:k]
        
        # 计算召回的相关文档数量
        relevant_count = 0
        for doc in top_k_docs:
            doc_id = doc.get("doc_id") or doc.get("metadata", {}).get("doc_id")
            if doc_id in relevant:
                relevant_count += 1
        
        return relevant_count / len(relevant)
    
    def ndcg_at_k(self, retrieved: List[Dict], relevant: List[str], k: int) -> float:
        """计算NDCG@k"""
        if not retrieved or not relevant or k <= 0:
            return 0.0
        
        # 获取top-k结果
        top_k_docs = retrieved[:k]
        
        # 计算DCG
        dcg = 0.0
        for i, doc in enumerate(top_k_docs):
            doc_id = doc.get("doc_id") or doc.get("metadata", {}).get("doc_id")
            relevance = 1 if doc_id in relevant else 0
            dcg += relevance / np.log2(i + 2)  # i+2因为log2(1)=0
        
        # 计算IDCG（理想排序）
        ideal_relevance = [1] * min(len(relevant), k) + [0] * max(0, k - len(relevant))
        idcg = sum(rel / np.log2(i + 2) for i, rel in enumerate(ideal_relevance))
        
        # 计算NDCG
        if idcg > 0:
            return dcg / idcg
        else:
            return 0.0
    
    def mean_reciprocal_rank(self, retrieved: List[Dict], relevant: List[str]) -> float:
        """计算MRR（平均倒数排名）"""
        if not retrieved or not relevant:
            return 0.0
        
        # 查找第一个相关文档的位置
        for i, doc in enumerate(retrieved):
            doc_id = doc.get("doc_id") or doc.get("metadata", {}).get("doc_id")
            if doc_id in relevant:
                return 1.0 / (i + 1)
        
        return 0.0
    
    def mean_average_precision(self, retrieved: List[Dict], relevant: List[str]) -> float:
        """计算MAP（平均精度均值）"""
        if not retrieved or not relevant:
            return 0.0
        
        # 计算每个相关文档的精度
        precisions = []
        relevant_count = 0
        
        for i, doc in enumerate(retrieved):
            doc_id = doc.get("doc_id") or doc.get("metadata", {}).get("doc_id")
            if doc_id in relevant:
                relevant_count += 1
                precision = relevant_count / (i + 1)
                precisions.append(precision)
        
        if precisions:
            return np.mean(precisions)
        else:
            return 0.0
    
    def hit_rate(self, retrieved: List[Dict], relevant: List[str]) -> float:
        """计算命中率"""
        if not retrieved or not relevant:
            return 0.0
        
        # 检查是否有任何相关文档被检索到
        for doc in retrieved:
            doc_id = doc.get("doc_id") or doc.get("metadata", {}).get("doc_id")
            if doc_id in relevant:
                return 1.0
        
        return 0.0
    
    def evaluate_batch(self, batch_results: List[Dict[str, List]], 
                      batch_relevant: List[List[str]], k: int = 10) -> Dict[str, float]:
        """
        批量评估
        
        Args:
            batch_results: 批量检索结果
            batch_relevant: 批量相关文档
            k: 评估的top-k位置
            
        Returns:
            Dict[str, float]: 平均评估指标
        """
        all_metrics = []
        
        for retrieved, relevant in zip(batch_results, batch_relevant):
            metrics = self.evaluate(retrieved, relevant, k)
            all_metrics.append(metrics)
        
        # 计算平均指标
        avg_metrics = {}
        for metric_name in all_metrics[0].keys():
            values = [m[metric_name] for m in all_metrics]
            avg_metrics[metric_name] = np.mean(values)
        
        return avg_metrics