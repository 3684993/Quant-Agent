"""
实时监控系统 - 直接运行并监控错误
"""

import subprocess
import time
from datetime import datetime
from pathlib import Path

LOG_FILE = Path("f:/Quant-Agent/system_monitor.log")
ERROR_LOG = Path("f:/Quant-Agent/error_summary.log")

class SystemMonitor:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.order_creations = []
        self.start_time = datetime.now()
        
    def parse_log_line(self, line):
        """解析日志行，提取关键信息"""
        line = line.strip()
        if not line:
            return
        
        # 记录错误
        if "ERROR" in line or "错误" in line:
            self.errors.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "message": line
            })
            print(f"\n❌ 错误 [{self.errors[-1]['time']}]: {line}")
            
        # 记录警告
        elif "WARNING" in line or "警告" in line:
            self.warnings.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "message": line
            })
            if "暴露量" in line or "EXPOSURE" in line:
                print(f"\n⚠️  暴露量警告 [{self.warnings[-1]['time']}]: {line}")
                
        # 记录止盈委托创建
        elif "止盈委托" in line or "create_take_profit" in line:
            self.order_creations.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "message": line
            })
            print(f"\n📋 止盈委托 [{self.order_creations[-1]['time']}]: {line}")
            
        # 记录持仓变化
        elif "持仓" in line and ("LONG" in line or "SHORT" in line):
            print(f"\n💼 持仓信息：{line}")
            
    def run(self):
        """运行系统并监控"""
        print("=" * 80)
        print("🚀 量化交易系统 - 实时监控")
        print(f"📅 启动时间：{self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("📝 监控内容：错误、警告、止盈委托、持仓变化")
        print("⚠️  按 Ctrl+C 停止")
        print("=" * 80)
        print()
        
        # 清空日志
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write(f"# 系统监控日志 - {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        try:
            # 启动系统
            process = subprocess.Popen(
                ["python", "-m", "ai_quant_trader.main"],
                cwd="f:/Quant-Agent",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                encoding="utf-8",
                errors="ignore"
            )
            
            print("✅ 系统已启动，开始监控...\n")
            
            # 实时读取日志
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                    
                if line:
                    # 写入日志文件
                    with open(LOG_FILE, "a", encoding="utf-8") as f:
                        f.write(line)
                    
                    # 解析并显示
                    self.parse_log_line(line)
                    
                    # 每秒刷新一次
                    time.sleep(0.1)
                    
        except KeyboardInterrupt:
            print("\n\n" + "=" * 80)
            print("🛑 监控已停止")
            self.print_summary()
            process.terminate()
            
        except Exception as e:
            print(f"\n❌ 监控失败：{e}")
            self.print_summary()
            
    def print_summary(self):
        """打印摘要"""
        print("\n" + "=" * 80)
        print("📊 监控摘要")
        print("=" * 80)
        print(f"运行时长：{datetime.now() - self.start_time}")
        print(f"错误数量：{len(self.errors)}")
        print(f"警告数量：{len(self.warnings)}")
        print(f"止盈委托：{len(self.order_creations)}")
        
        if self.errors:
            print("\n❌ 最新错误:")
            for err in self.errors[-5:]:
                print(f"  [{err['time']}] {err['message'][:100]}")
                
        if self.warnings:
            print("\n⚠️  暴露量相关警告:")
            for warn in [w for w in self.warnings if "暴露量" in w['message']][-5:]:
                print(f"  [{warn['time']}] {warn['message'][:100]}")
                
        if self.order_creations:
            print("\n📋 止盈委托创建记录:")
            for order in self.order_creations[-5:]:
                print(f"  [{order['time']}] {order['message'][:100]}")
        
        # 保存到文件
        with open(ERROR_LOG, "w", encoding="utf-8") as f:
            f.write(f"# 错误摘要 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"运行时长：{datetime.now() - self.start_time}\n")
            f.write(f"错误数量：{len(self.errors)}\n")
            f.write(f"警告数量：{len(self.warnings)}\n\n")
            
            if self.errors:
                f.write("=" * 80 + "\n")
                f.write("错误列表:\n")
                f.write("=" * 80 + "\n")
                for err in self.errors:
                    f.write(f"[{err['time']}] {err['message']}\n")
                    
            if self.warnings:
                f.write("\n" + "=" * 80 + "\n")
                f.write("警告列表:\n")
                f.write("=" * 80 + "\n")
                for warn in self.warnings:
                    f.write(f"[{warn['time']}] {warn['message']}\n")
        
        print(f"\n详细日志：{LOG_FILE}")
        print(f"错误摘要：{ERROR_LOG}")
        print("=" * 80)


if __name__ == "__main__":
    monitor = SystemMonitor()
    monitor.run()
