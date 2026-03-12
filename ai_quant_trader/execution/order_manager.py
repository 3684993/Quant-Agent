"""
独立的委托订单管理模块
负责巡查委托订单的存在性、合理性、趋势分析、成交可能性等
"""

import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta

logger = logging.getLogger("ai_quant_trader")


class OrderManager:
    """委托订单管理模块"""
    
    def __init__(self, order_executor, market_analyzer=None):
        """
        初始化委托管理模块
        
        Args:
            order_executor: 委托执行器
            market_analyzer: 市场分析器（可选）
        """
        self.order_executor = order_executor
        self.market_analyzer = market_analyzer
        
        # 委托巡查配置
        self.config = {
            "min_price_spacing": 100.0,  # 最小价格间距
            "max_orders_per_symbol": 4,  # 每个交易对最大委托数量
            "price_distance_threshold": 0.02,  # 价格距离阈值（2%）
            "trend_consistency_threshold": 0.7,  # 趋势一致性阈值
            "execution_probability_threshold": 0.3,  # 成交可能性阈值
        }
        
        # 委托巡查记录
        self.inspection_records = {}
    
    def inspect_all_orders(self, symbol: str) -> Dict:
        """
        全面巡查指定交易对的所有委托订单
        
        Args:
            symbol: 交易对
            
        Returns:
            巡查结果
        """
        try:
            # 获取所有活跃委托
            existing_orders = self.order_executor.get_existing_orders(symbol)
            
            if not existing_orders:
                return {
                    "success": True,
                    "symbol": symbol,
                    "total_orders": 0,
                    "inspections": {},
                    "recommendations": ["无活跃委托"]
                }
            
            # 执行各项巡查
            inspections = {
                "existence_check": self._inspect_existence(symbol, existing_orders),
                "spacing_check": self._inspect_price_spacing(symbol, existing_orders),
                "trend_check": self._inspect_trend_consistency(symbol, existing_orders),
                "distance_check": self._inspect_price_distance(symbol, existing_orders),
                "execution_probability": self._analyze_execution_probability(symbol, existing_orders),
                "time_check": self._inspect_order_time(symbol, existing_orders),
            }
            
            # 生成综合建议
            recommendations = self._generate_recommendations(inspections, existing_orders)
            
            # 记录巡查结果
            self.inspection_records[symbol] = {
                "timestamp": datetime.now(),
                "inspections": inspections,
                "recommendations": recommendations
            }
            
            return {
                "success": True,
                "symbol": symbol,
                "total_orders": len(existing_orders),
                "inspections": inspections,
                "recommendations": recommendations
            }
            
        except Exception as e:
            logger.error(f"委托巡查失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "symbol": symbol
            }
    
    def _inspect_existence(self, symbol: str, orders: List[Dict]) -> Dict:
        """巡查委托订单的存在性"""
        try:
            # 检查委托数量是否合理
            max_orders = self.config["max_orders_per_symbol"]
            order_count = len(orders)
            
            return {
                "order_count": order_count,
                "max_allowed": max_orders,
                "within_limit": order_count <= max_orders,
                "status": "正常" if order_count <= max_orders else "过多",
                "message": f"委托数量: {order_count}/{max_orders}"
            }
            
        except Exception as e:
            logger.error(f"存在性巡查失败: {e}")
            return {"status": "错误", "message": str(e)}
    
    def _inspect_price_spacing(self, symbol: str, orders: List[Dict]) -> Dict:
        """巡查价格间距合理性"""
        try:
            if len(orders) <= 1:
                return {
                    "status": "正常",
                    "message": "单笔委托，无需检查间距",
                    "min_spacing": 0.0
                }
            
            # 提取价格并排序
            prices = sorted([order.get("price", 0) for order in orders])
            
            # 计算最小间距
            min_spacing = min([abs(prices[i+1] - prices[i]) for i in range(len(prices)-1)])
            required_spacing = self.config["min_price_spacing"]
            
            return {
                "min_spacing": min_spacing,
                "required_spacing": required_spacing,
                "meets_requirement": min_spacing >= required_spacing,
                "status": "正常" if min_spacing >= required_spacing else "间距过小",
                "message": f"最小间距: {min_spacing:.2f} / 要求: {required_spacing:.2f}"
            }
            
        except Exception as e:
            logger.error(f"价格间距巡查失败: {e}")
            return {"status": "错误", "message": str(e)}
    
    def _inspect_trend_consistency(self, symbol: str, orders: List[Dict]) -> Dict:
        """巡查趋势与委托方向的一致性"""
        try:
            if not self.market_analyzer:
                return {
                    "status": "跳过",
                    "message": "未配置市场分析器"
                }
            
            # 获取市场趋势
            market_data = self.market_analyzer.get_market_summary(symbol)
            current_trend = market_data.get("trend", "neutral")
            
            # 分析委托方向与趋势的一致性
            buy_orders = [order for order in orders if order.get("side") == "BUY"]
            sell_orders = [order for order in orders if order.get("side") == "SELL"]
            
            trend_consistent = True
            inconsistency_reasons = []
            
            if current_trend == "bullish" and len(sell_orders) > len(buy_orders):
                trend_consistent = False
                inconsistency_reasons.append("牛市趋势下卖单多于买单")
            elif current_trend == "bearish" and len(buy_orders) > len(sell_orders):
                trend_consistent = False
                inconsistency_reasons.append("熊市趋势下买单多于卖单")
            
            return {
                "current_trend": current_trend,
                "buy_orders": len(buy_orders),
                "sell_orders": len(sell_orders),
                "trend_consistent": trend_consistent,
                "status": "一致" if trend_consistent else "不一致",
                "message": ", ".join(inconsistency_reasons) if inconsistency_reasons else "趋势与委托方向一致"
            }
            
        except Exception as e:
            logger.error(f"趋势一致性巡查失败: {e}")
            return {"status": "错误", "message": str(e)}
    
    def _inspect_price_distance(self, symbol: str, orders: List[Dict]) -> Dict:
        """巡查当前价与委托价的距离"""
        try:
            # 获取当前价格
            current_price = self.order_executor.get_current_price(symbol)
            if not current_price:
                return {
                    "status": "跳过",
                    "message": "无法获取当前价格"
                }
            
            # 计算每个委托的价格距离
            distance_analysis = []
            too_far_orders = []
            
            for order in orders:
                order_price = order.get("price", 0)
                price_diff_pct = abs(order_price - current_price) / current_price
                
                distance_analysis.append({
                    "order_id": order.get("order_id", "unknown"),
                    "order_price": order_price,
                    "current_price": current_price,
                    "distance_pct": price_diff_pct,
                    "too_far": price_diff_pct > self.config["price_distance_threshold"]
                })
                
                if price_diff_pct > self.config["price_distance_threshold"]:
                    too_far_orders.append(order.get("order_id", "unknown"))
            
            return {
                "current_price": current_price,
                "distance_threshold": self.config["price_distance_threshold"],
                "distance_analysis": distance_analysis,
                "too_far_orders": too_far_orders,
                "status": "正常" if not too_far_orders else "距离过远",
                "message": f"{len(too_far_orders)}个委托距离过远" if too_far_orders else "所有委托价格距离合理"
            }
            
        except Exception as e:
            logger.error(f"价格距离巡查失败: {e}")
            return {"status": "错误", "message": str(e)}
    
    def _analyze_execution_probability(self, symbol: str, orders: List[Dict]) -> Dict:
        """分析委托成交可能性"""
        try:
            # 获取当前价格和市场数据
            current_price = self.order_executor.get_current_price(symbol)
            if not current_price:
                return {
                    "status": "跳过",
                    "message": "无法获取当前价格"
                }
            
            probability_analysis = []
            low_probability_orders = []
            
            for order in orders:
                order_price = order.get("price", 0)
                side = order.get("side", "BUY")
                
                # 简单的成交可能性计算
                if side == "BUY":
                    # 买单：价格低于当前价的可能性高
                    probability = max(0, 1 - (order_price - current_price) / current_price)
                else:
                    # 卖单：价格高于当前价的可能性高
                    probability = max(0, 1 - (current_price - order_price) / current_price)
                
                probability_analysis.append({
                    "order_id": order.get("order_id", "unknown"),
                    "side": side,
                    "order_price": order_price,
                    "current_price": current_price,
                    "probability": probability,
                    "low_probability": probability < self.config["execution_probability_threshold"]
                })
                
                if probability < self.config["execution_probability_threshold"]:
                    low_probability_orders.append(order.get("order_id", "unknown"))
            
            return {
                "probability_threshold": self.config["execution_probability_threshold"],
                "probability_analysis": probability_analysis,
                "low_probability_orders": low_probability_orders,
                "status": "正常" if not low_probability_orders else "成交可能性低",
                "message": f"{len(low_probability_orders)}个委托成交可能性低" if low_probability_orders else "所有委托成交可能性合理"
            }
            
        except Exception as e:
            logger.error(f"成交可能性分析失败: {e}")
            return {"status": "错误", "message": str(e)}
    
    def _inspect_order_time(self, symbol: str, orders: List[Dict]) -> Dict:
        """巡查委托时间合理性"""
        try:
            current_time = datetime.now()
            stale_orders = []
            
            for order in orders:
                order_time = order.get("time", 0)
                
                # 交易所返回的时间是毫秒时间戳（整数）
                if isinstance(order_time, int) and order_time > 0:
                    # 将毫秒时间戳转换为 datetime
                    order_time = datetime.fromtimestamp(order_time / 1000)
                elif isinstance(order_time, str):
                    # 尝试解析时间字符串
                    try:
                        order_time = datetime.fromisoformat(order_time.replace('Z', '+00:00'))
                    except:
                        order_time = current_time
                else:
                    # 如果没有有效时间，使用当前时间
                    order_time = current_time
                
                # 检查委托是否超时（超过 1 小时）
                time_diff = current_time - order_time
                if time_diff > timedelta(hours=1):
                    stale_orders.append(order.get("order_id", "unknown"))
            
            return {
                "stale_orders": stale_orders,
                "status": "正常" if not stale_orders else "存在超时委托",
                "message": f"{len(stale_orders)}个委托超时" if stale_orders else "所有委托时间合理"
            }
            
        except Exception as e:
            logger.error(f"委托时间巡查失败: {e}")
            return {"status": "错误", "message": str(e)}
    
    def _generate_recommendations(self, inspections: Dict, orders: List[Dict]) -> List[str]:
        """生成综合建议"""
        recommendations = []
        
        # 委托数量建议
        existence_check = inspections.get("existence_check", {})
        if not existence_check.get("within_limit", True):
            recommendations.append("委托数量过多，建议清理部分委托")
        
        # 价格间距建议
        spacing_check = inspections.get("spacing_check", {})
        if not spacing_check.get("meets_requirement", True):
            recommendations.append("委托价格间距过小，建议优化价格分布")
        
        # 趋势一致性建议
        trend_check = inspections.get("trend_check", {})
        if not trend_check.get("trend_consistent", True):
            recommendations.append("委托方向与市场趋势不一致，建议调整")
        
        # 价格距离建议
        distance_check = inspections.get("distance_check", {})
        too_far_orders = distance_check.get("too_far_orders", [])
        if too_far_orders:
            recommendations.append(f"{len(too_far_orders)}个委托价格距离过远，建议调整或取消")
        
        # 成交可能性建议
        probability_check = inspections.get("execution_probability", {})
        low_prob_orders = probability_check.get("low_probability_orders", [])
        if low_prob_orders:
            recommendations.append(f"{len(low_prob_orders)}个委托成交可能性低，建议重新评估")
        
        # 委托时间建议
        time_check = inspections.get("time_check", {})
        stale_orders = time_check.get("stale_orders", [])
        if stale_orders:
            recommendations.append(f"{len(stale_orders)}个委托超时，建议取消")
        
        if not recommendations:
            recommendations.append("所有委托状态正常")
        
        return recommendations
    
    def auto_cleanup_orders(self, symbol: str) -> Dict:
        """自动清理不合理的委托"""
        try:
            inspection_result = self.inspect_all_orders(symbol)
            
            if not inspection_result.get("success"):
                return {
                    "success": False,
                    "error": "巡查失败",
                    "symbol": symbol
                }
            
            recommendations = inspection_result.get("recommendations", [])
            cleanup_actions = []
            
            # 根据巡查结果执行清理
            inspections = inspection_result.get("inspections", {})
            
            # 清理超时委托
            time_check = inspections.get("time_check", {})
            stale_orders = time_check.get("stale_orders", [])
            if stale_orders:
                result = self.order_executor.cancel_orders(symbol, stale_orders)
                cleanup_actions.append(f"清理{len(stale_orders)}个超时委托")
            
            # 清理距离过远的委托
            distance_check = inspections.get("distance_check", {})
            too_far_orders = distance_check.get("too_far_orders", [])
            if too_far_orders:
                result = self.order_executor.cancel_orders(symbol, too_far_orders)
                cleanup_actions.append(f"清理{len(too_far_orders)}个距离过远委托")
            
            return {
                "success": True,
                "symbol": symbol,
                "cleanup_actions": cleanup_actions,
                "recommendations": recommendations
            }
            
        except Exception as e:
            logger.error(f"自动清理失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "symbol": symbol
            }
    
    def get_inspection_history(self, symbol: str, limit: int = 10) -> List[Dict]:
        """获取巡查历史记录"""
        if symbol in self.inspection_records:
            # 返回最近的记录
            return [self.inspection_records[symbol]]
        return []
    
    def update_config(self, new_config: Dict):
        """更新配置"""
        self.config.update(new_config)
        logger.info(f"委托管理配置已更新: {new_config}")