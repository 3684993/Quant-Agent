import json
from typing import Dict, Optional
from core.logger import logger
from ai.llm_client import LLMClient
from agents.orderbook_agent import OrderBookAgent
from agents.liquidity_agent import LiquidityAgent
from agents.profit_optimizer import ProfitOptimizer
from agents.advanced_take_profit import advanced_take_profit
from agents.intelligent_close_decision import intelligent_close_decision


class DecisionEngine:
    def __init__(self, llm_client: LLMClient = None):
        self.llm_client = llm_client or LLMClient()
        
        self._last_decision: Dict = {}
        self._decision_history: list = []
        
        logger.info("DecisionEngine initialized")
    
    def generate_trade_decision(self, context: Dict) -> Dict:
        try:
            prompt = self._build_prompt(context)
            
            messages = [
                {
                    "role": "system",
                    "content": self._get_system_prompt()
                },
                {
                    "role": "user",
                    "content": prompt + " /no_think"
                }
            ]
            
            response = self.llm_client.chat_json(messages, temperature=0.3, max_tokens=2000)
            
            if response:
                validated = self._validate_decision(response, context.get("position", {}))
                self._last_decision = validated.copy()
                self._decision_history.append({
                    "decision": validated.copy(),
                    "context": {
                        "price": context.get("price", 0),
                        "has_position": context.get("position", {}).get("has_position", False)
                    }
                })
                if len(self._decision_history) > 100:
                    self._decision_history = self._decision_history[-100:]
                return validated
            else:
                logger.warning("LLM returned no response, using default decision")
                return self._get_default_decision()
                
        except Exception as e:
            logger.error(f"Decision generation failed: {e}")
            return self._get_default_decision()
    
    def _get_system_prompt(self) -> str:
        return """You are a trading signal generator. Output ONLY valid JSON. No explanations.

RULES:
1. trend=macd_signal → trade that direction
2. trend≠macd_signal → hold
3. add_position: only when position is profitable (pnl>0)
4. close_position: MUST close when hold_minutes >= expected_hold_minutes
5. close_position: also when trend reverses or SL hit
6. Never reverse direction quickly - require 3 confirmations
7. Always set stop_loss and take_profit
8. Respect minimum hold time (30min)
9. FORCE CLOSE: If hold_minutes >= expected_hold_minutes, action MUST be "close_position"
10. BATCH ORDER STRATEGY: When opening position, use 2-4 split orders with min 100 points spacing
11. RE-ENTRY ALLOWED: If no position and no pending orders, can open new position
12. FILL_OR_REENTER: If orders not filled after 5 minutes, can cancel and re-enter at better price

OUTPUT FORMAT:
{"action":"open_long|open_short|add_position|close_position|hold","entry_range":[low,high],"size":[0.01,0.02],"stop_loss":price,"take_profit":price,"expected_hold_minutes":60,"confidence":0.8}"""
    
    def _build_prompt(self, context: Dict) -> str:
        price = context.get("price", 0)
        indicators = context.get("indicators", {})
        market_summary = context.get("market_summary", {})
        profit_optimizer = context.get("profit_optimizer", {})
        position = context.get("position", {})
        
        has_position = position.get("has_position", False)
        pnl_pct = position.get("current_pnl_pct", 0) if has_position else 0
        hold_minutes = position.get("hold_minutes", 0) if has_position else 0
        expected_hold = position.get("expected_hold_minutes", 60) if has_position else 60
        position_side = position.get("side", "none") if has_position else "none"
        
        bb_upper = indicators.get('bollinger', {}).get('upper', 0)
        bb_lower = indicators.get('bollinger', {}).get('lower', 0)
        atr = indicators.get('atr', 0)
        
        trend = market_summary.get('trend', 'neutral')
        macd_signal = market_summary.get('macd_signal', 'neutral')
        
        return f"""Price:{price:.2f}|Trend:{trend}|MACD:{macd_signal}|BB:[{bb_lower:.0f},{bb_upper:.0f}]|ATR:{atr:.1f}|Pos:{'Y' if has_position else 'N'}|Side:{position_side}|PnL:{pnl_pct:.2f}%|Hold:{hold_minutes}min/{expected_hold}min|Entry:{profit_optimizer.get('optimal_entry',[0,0])}|SL:{profit_optimizer.get('stop_loss',0):.0f}|TP:{profit_optimizer.get('take_profit',0):.0f}

JSON:"""
    
    def _validate_decision(self, decision: Dict, position: Dict) -> Dict:
        valid_actions_no_position = ["open_long", "open_short", "hold"]
        valid_actions_with_position = ["add_position", "close_position", "reverse_position", "hold"]
        
        has_position = position.get("has_position", False)
        
        action = decision.get("action", "hold")
        
        # 检查目标仓位是否已达成
        if has_position:
            position_size = position.get("position_size", 0)
            target_size = position.get("target_size", position_size)
            progress_pct = (position_size / target_size * 100) if target_size > 0 else 100
            
            # 如果目标仓位已达成，使用智能平仓决策
            if progress_pct >= 100:
                hold_minutes = position.get("hold_minutes", 0)
                
                # 检查持仓时间是否有效（避免系统重启后时间重置问题）
                if hold_minutes == 0:
                    # 如果持仓时间为0，可能是系统重启，使用保守策略
                    logger.info("TARGET_REACHED_RESTART: 目标仓位已达成但持仓时间未知（可能系统重启），建议平仓")
                    if action == "add_position":
                        action = "close_position"
                else:
                    # 使用智能平仓决策系统
                    close_recommendation = intelligent_close_decision.get_close_recommendation(
                        position, indicators, market_summary, False
                    )
                    
                    should_close = close_recommendation.get("should_close", False)
                    reason = close_recommendation.get("reason", "未知")
                    priority = close_recommendation.get("priority", 0.5)
                    
                    logger.info(f"智能平仓决策: 持仓{hold_minutes}分钟, 收益{position.get('current_pnl_pct', 0):.2f}%, "
                               f"建议{'平仓' if should_close else '持仓'}, 原因: {reason}, 优先级: {priority:.2f}")
                    
                    if should_close and priority >= 0.6:  # 优先级较高的平仓建议
                        logger.info(f"TARGET_REACHED_SMART_CLOSE: 智能平仓决策 - {reason}")
                        action = "close_position"
                    elif action == "add_position":
                        # 未达到平仓条件，阻止加仓
                        logger.info("TARGET_REACHED_BLOCK_ADD: 目标仓位已达成但未达平仓条件，阻止加仓")
                        action = "hold"
        
        if has_position:
            if action not in valid_actions_with_position:
                action = "hold"
        else:
            if action not in valid_actions_no_position:
                action = "hold"
        
        entry_range = decision.get("entry_range", [0, 0])
        if not isinstance(entry_range, list) or len(entry_range) != 2:
            entry_range = [0, 0]
        
        size = decision.get("size", [0.01, 0.02])
        if not isinstance(size, list) or len(size) != 2:
            size = [0.01, 0.02]
        
        stop_loss = decision.get("stop_loss", 0)
        if not isinstance(stop_loss, (int, float)):
            stop_loss = 0
        
        take_profit = decision.get("take_profit", 0)
        if not isinstance(take_profit, (int, float)):
            take_profit = 0
        
        hold_minutes = decision.get("expected_hold_minutes", 60)
        if not isinstance(hold_minutes, (int, float)):
            hold_minutes = 60
        hold_minutes = max(30, min(120, int(hold_minutes)))
        
        confidence = decision.get("confidence", 0.5)
        if not isinstance(confidence, (int, float)):
            confidence = 0.5
        confidence = max(0, min(1, float(confidence)))
        
        if action in ["open_long", "open_short"]:
            if stop_loss == 0 or take_profit == 0:
                logger.warning(f"Missing SL/TP for {action}, using ProfitOptimizer values")
        
        return {
            "action": action,
            "entry_range": entry_range,
            "size": size,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "expected_hold_minutes": hold_minutes,
            "confidence": confidence
        }
    
    def _get_default_decision(self) -> Dict:
        return {
            "action": "hold",
            "entry_range": [0, 0],
            "size": [0.01, 0.02],
            "stop_loss": 0,
            "take_profit": 0,
            "expected_hold_minutes": 60,
            "confidence": 0.5
        }
    
    def format_decision_log(self, decision: Dict, symbol: str) -> str:
        try:
            return (
                f"[{symbol}] AI Decision: "
                f"action={decision.get('action', 'hold')} | "
                f"entry_range={decision.get('entry_range', [0, 0])} | "
                f"size={decision.get('size', [0.01, 0.02])} | "
                f"SL={decision.get('stop_loss', 0):.2f} | "
                f"TP={decision.get('take_profit', 0):.2f} | "
                f"hold={decision.get('expected_hold_minutes', 60)}min | "
                f"conf={decision.get('confidence', 0.5):.2f}"
            )
        except Exception:
            return f"[{symbol}] AI Decision generated"
    
    def get_last_decision(self) -> Dict:
        return self._last_decision.copy() if self._last_decision else {}
    
    def get_decision_history(self, limit: int = 10) -> list:
        return self._decision_history[-limit:] if self._decision_history else []
