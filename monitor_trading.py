"""
实时交易监控系统
持续监控持仓、平仓和收益，直到手动退出
"""

import json
import time
from datetime import datetime
from pathlib import Path

# 配置文件路径
LOG_DIR = Path("f:/Quant-Agent/ai_quant_trader/logs")
MONITOR_LOG = Path("f:/Quant-Agent/trading_activity.log")
SUMMARY_FILE = Path("f:/Quant-Agent/trading_summary.json")

# 监控状态
class TradingMonitor:
    def __init__(self):
        self.positions = []  # 持仓记录
        self.closes = []  # 平仓记录
        self.errors = []  # 错误记录
        self.orders = []  # 订单记录
        self.start_time = datetime.now()
        self.last_position = None
        self.total_profit = 0.0
        
    def parse_log_line(self, line):
        """解析日志行"""
        try:
            # 提取关键信息
            if "[ORDER_FILLED]" in line:
                return self._parse_order_filled(line)
            elif "[POSITION]" in line and "平仓" in line:
                return self._parse_position_close(line)
            elif "ERROR" in line:
                return self._parse_error(line)
            elif "[EXECUTION]" in line:
                return self._parse_execution(line)
            elif "[AI_DECISION]" in line:
                return self._parse_ai_decision(line)
            return None
        except Exception as e:
            return None
    
    def _parse_order_filled(self, line):
        """解析订单成交"""
        try:
            # 提取：symbol, size, price
            parts = line.split()
            info = {"type": "ORDER_FILLED", "time": datetime.now().strftime("%H:%M:%S")}
            
            for part in parts:
                if "symbol=" in part:
                    info["symbol"] = part.split("=")[1]
                elif "size=" in part:
                    info["size"] = float(part.split("=")[1])
                elif "price=" in part:
                    info["price"] = float(part.split("=")[1])
            
            if "size" in info:
                self.orders.append(info)
                self.last_position = info.get("size", 0)
                return info
        except:
            pass
        return None
    
    def _parse_execution(self, line):
        """解析执行状态"""
        try:
            if "action=open_long" in line or "action=open_short" in line:
                info = {"type": "EXECUTION", "time": datetime.now().strftime("%H:%M:%S")}
                if "price=" in line:
                    parts = line.split()
                    for part in parts:
                        if "price=" in part:
                            info["price"] = float(part.split("=")[1])
                        elif "remaining=" in part:
                            info["remaining"] = float(part.split("=")[1])
                return info
        except:
            pass
        return None
    
    def _parse_error(self, line):
        """解析错误"""
        try:
            if "ReduceOnly Order is rejected" in line:
                self.errors.append({
                    "type": "REDUCE_ONLY_ERROR",
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "message": "ReduceOnly Order rejected"
                })
                return self.errors[-1]
        except:
            pass
        return None
    
    def _parse_ai_decision(self, line):
        """解析 AI 决策"""
        try:
            if "action=" in line:
                info = {"type": "AI_DECISION", "time": datetime.now().strftime("%H:%M:%S")}
                if "action=open_long" in line:
                    info["action"] = "open_long"
                elif "action=open_short" in line:
                    info["action"] = "open_short"
                elif "action=hold" in line:
                    info["action"] = "hold"
                elif "action=close" in line:
                    info["action"] = "close"
                
                if "target=" in line:
                    parts = line.split()
                    for part in parts:
                        if "target=" in part:
                            info["target"] = float(part.split("=")[1])
                
                return info
        except:
            pass
        return None
    
    def log_event(self, event):
        """记录事件"""
        if event:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_line = f"{timestamp} | {json.dumps(event, ensure_ascii=False)}\n"
            
            with open(MONITOR_LOG, "a", encoding="utf-8") as f:
                f.write(log_line)
            
            # 打印到控制台
            if event.get("type") == "ORDER_FILLED":
                print(f"✅ 订单成交：{event.get('symbol')} {event.get('action', 'open')} {event.get('size')} @ {event.get('price')}")
            elif event.get("type") == "ERROR":
                print(f"❌ 错误：{event.get('message', '')}")
            elif event.get("type") == "AI_DECISION":
                print(f"🤖 AI 决策：{event.get('action')} 目标={event.get('target')}")
    
    def update_summary(self):
        """更新摘要"""
        summary = {
            "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "running_duration": str(datetime.now() - self.start_time),
            "total_orders": len(self.orders),
            "total_errors": len(self.errors),
            "current_position": self.last_position,
            "total_profit": self.total_profit,
            "recent_orders": self.orders[-10:],
            "recent_errors": self.errors[-10:]
        }
        
        with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
    
    def run(self):
        """运行监控"""
        print("=" * 80)
        print("🔍 交易监控系统已启动")
        print(f"📅 开始时间：{self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("📝 监控内容：持仓、平仓、收益、错误")
        print("⚠️  按 Ctrl+C 停止监控")
        print("=" * 80)
        print()
        
        # 清空旧的监控日志
        with open(MONITOR_LOG, "w", encoding="utf-8") as f:
            f.write(f"# 交易监控日志 - 开始于 {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        try:
            while True:
                # 读取最新日志
                log_files = list(LOG_DIR.glob("*.log"))
                
                for log_file in log_files:
                    try:
                        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                            lines = f.readlines()
                            for line in lines[-100:]:  # 只读取最后 100 行
                                event = self.parse_log_line(line)
                                if event:
                                    self.log_event(event)
                    except Exception as e:
                        pass
                
                # 更新摘要
                self.update_summary()
                
                # 等待 5 秒
                time.sleep(5)
                
        except KeyboardInterrupt:
            print("\n" + "=" * 80)
            print("🛑 监控已停止")
            print(f"📊 运行时长：{datetime.now() - self.start_time}")
            print(f"📈 总订单数：{len(self.orders)}")
            print(f"❌ 总错误数：{len(self.errors)}")
            print(f"💰 当前持仓：{self.last_position}")
            print(f"💵 总收益：{self.total_profit}")
            print("=" * 80)
            print(f"\n详细日志已保存到：{MONITOR_LOG}")
            print(f"摘要文件已保存到：{SUMMARY_FILE}")


if __name__ == "__main__":
    monitor = TradingMonitor()
    monitor.run()
