#!/usr/bin/env python3
"""
AI量化交易系统简单监控器
直接运行 main.py live 并监控状态
每30分钟生成运行报告
"""

import subprocess
import time
import signal
import sys
import os
import json
from datetime import datetime, timedelta
import threading
import psutil
import platform
import socket

class SimpleTradingMonitor:
    def __init__(self):
        self.trading_process = None
        self.start_time = None
        self.report_count = 0
        self.stop_flag = False
        
        # 创建报告目录
        os.makedirs("reports", exist_ok=True)
        os.makedirs("logs", exist_ok=True)
        
        print("="*70)
        print("     AI量化交易系统监控器")
        print("="*70)
        print("功能:")
        print("  • 运行 main.py live 命令")
        print("  • 每30分钟生成系统状态报告")
        print("  • 监控进程状态和资源使用")
        print("  • 支持Ctrl+C优雅停止")
        print("="*70)
        
    def start_trading(self):
        """启动交易系统"""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 启动交易系统...")
        
        try:
            # 检查Python和依赖
            import pandas
            import numpy
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Python依赖检查通过")
        except ImportError as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ 缺少依赖: {e}")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 请先运行: pip install pandas numpy")
            return False
        
        try:
            # 启动交易进程
            self.trading_process = subprocess.Popen(
                [sys.executable, "main.py", "live"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                encoding='utf-8'
            )
            
            self.start_time = datetime.now()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 交易系统已启动 (PID: {self.trading_process.pid})")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏰ 系统将每30分钟生成一次运行报告")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️  按Ctrl+C可停止系统")
            
            # 等待5秒让系统初始化
            time.sleep(5)
            return True
            
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ 启动失败: {e}")
            return False
    
    def get_system_info(self):
        """获取系统信息"""
        info = {
            "report_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "report_number": self.report_count,
            "uptime": None,
            "process_status": "UNKNOWN",
            "system": {},
            "recent_logs": []
        }
        
        # 运行时间
        if self.start_time:
            uptime = datetime.now() - self.start_time
            info["uptime"] = str(uptime)
        
        # 进程状态
        if self.trading_process:
            if self.trading_process.poll() is None:
                info["process_status"] = "RUNNING"
                try:
                    proc = psutil.Process(self.trading_process.pid)
                    info["process_cpu"] = proc.cpu_percent()
                    info["process_memory_mb"] = proc.memory_info().rss / (1024**2)
                except:
                    pass
            else:
                info["process_status"] = "STOPPED"
                info["exit_code"] = self.trading_process.returncode
        
        # 系统信息
        try:
            info["system"]["platform"] = platform.platform()
            info["system"]["cpu_usage"] = psutil.cpu_percent(interval=1)
            info["system"]["memory_usage_percent"] = psutil.virtual_memory().percent
            info["system"]["memory_total_gb"] = psutil.virtual_memory().total / (1024**3)
            info["system"]["memory_available_gb"] = psutil.virtual_memory().available / (1024**3)
        except Exception as e:
            info["system"]["error"] = str(e)
        
        # 读取最新的日志
        info["recent_logs"] = self.read_recent_logs(10)
        
        return info
    
    def read_recent_logs(self, max_lines=20):
        """读取最近的日志"""
        logs = []
        if not self.trading_process:
            return logs
            
        try:
            # 尝试读取输出
            import select
            ready, _, _ = select.select([self.trading_process.stdout], [], [], 0.1)
            if ready:
                for line in iter(self.trading_process.stdout.readline, ''):
                    if not line:
                        break
                    logs.append(line.strip())
                    if len(logs) >= max_lines:
                        break
        except:
            pass
            
        return logs
    
    def generate_report(self):
        """生成运行报告"""
        self.report_count += 1
        report_time = datetime.now()
        
        print(f"\n{'='*70}")
        print(f"   运行报告 #{self.report_count}")
        print(f"   报告时间: {report_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}")
        
        # 获取系统信息
        info = self.get_system_info()
        
        # 打印报告
        print(f"📊 系统状态:")
        print(f"  运行时间: {info.get('uptime', 'N/A')}")
        print(f"  进程状态: {info['process_status']}")
        
        if info.get('process_cpu') is not None:
            print(f"  进程CPU: {info['process_cpu']:.1f}%")
        if info.get('process_memory_mb') is not None:
            print(f"  进程内存: {info['process_memory_mb']:.1f} MB")
        
        print(f"\n💻 系统资源:")
        print(f"  CPU使用率: {info['system'].get('cpu_usage', 'N/A'):.1f}%")
        print(f"  内存使用率: {info['system'].get('memory_usage_percent', 'N/A'):.1f}%")
        
        # 最近日志
        logs = info['recent_logs']
        if logs:
            print(f"\n📝 最近系统日志 ({len(logs)}条):")
            for i, log in enumerate(logs[-5:], 1):
                print(f"  {i:2d}. {log}")
        
        print(f"\n📁 报告详情已保存到 reports/ 目录")
        print(f"{'='*70}")
        
        # 保存报告到文件
        self.save_report_to_file(info)
        
        return info
    
    def save_report_to_file(self, info):
        """保存报告到文件"""
        try:
            # 保存JSON格式
            json_file = f"reports/report_{self.report_count:03d}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(info, f, indent=2, ensure_ascii=False)
            
            # 保存文本格式
            txt_file = f"reports/report_{self.report_count:03d}.txt"
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write(f"{'='*70}\n")
                f.write(f"AI量化交易系统运行报告 #{self.report_count}\n")
                f.write(f"生成时间: {info['report_time']}\n")
                f.write(f"{'='*70}\n\n")
                
                f.write("系统状态:\n")
                f.write(f"  运行时间: {info.get('uptime', 'N/A')}\n")
                f.write(f"  进程状态: {info['process_status']}\n\n")
                
                f.write("资源使用:\n")
                f.write(f"  CPU使用率: {info['system'].get('cpu_usage', 'N/A'):.1f}%\n")
                f.write(f"  内存使用率: {info['system'].get('memory_usage_percent', 'N/A'):.1f}%\n\n")
                
                f.write("最近日志:\n")
                for log in info['recent_logs'][-10:]:
                    f.write(f"  {log}\n")
            
            # 更新最新报告
            latest_file = "reports/latest_report.md"
            with open(latest_file, 'w', encoding='utf-8') as f:
                f.write(f"# 最新运行报告 #{self.report_count}\n\n")
                f.write(f"**报告时间**: {info['report_time']}\n\n")
                f.write(f"**运行时间**: {info.get('uptime', 'N/A')}\n\n")
                f.write(f"**进程状态**: {info['process_status']}\n\n")
                f.write("## 系统资源\n\n")
                f.write(f"- CPU使用率: {info['system'].get('cpu_usage', 'N/A'):.1f}%\n")
                f.write(f"- 内存使用率: {info['system'].get('memory_usage_percent', 'N/A'):.1f}%\n\n")
                f.write("## 详细日志\n\n")
                for log in info['recent_logs'][-15:]:
                    f.write(f"- {log}\n")
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 报告已保存: {json_file}")
            
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ 保存报告失败: {e}")
    
    def signal_handler(self, sig, frame):
        """信号处理"""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ⏹️ 收到停止信号...")
        self.stop_flag = True
    
    def run(self):
        """运行监控器"""
        # 设置信号处理
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # 启动交易系统
        if not self.start_trading():
            return
        
        # 首次报告
        time.sleep(10)
        self.generate_report()
        
        # 主循环
        report_interval = 30 * 60  # 30分钟
        check_interval = 30  # 30秒检查一次
        
        try:
            while not self.stop_flag:
                # 每30秒检查一次进程状态
                for _ in range(int(report_interval / check_interval)):
                    if self.stop_flag:
                        break
                    
                    # 检查进程是否存活
                    if self.trading_process.poll() is not None:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️  交易进程已停止")
                        self.stop_flag = True
                        break
                    
                    time.sleep(check_interval)
                
                # 生成报告
                if not self.stop_flag:
                    self.generate_report()
                    
        except KeyboardInterrupt:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 👋 用户中断")
            self.stop_flag = True
        except Exception as e:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ❌ 监控错误: {e}")
        
        # 停止系统
        self.shutdown()
    
    def shutdown(self):
        """关闭系统"""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🛑 正在关闭系统...")
        
        # 停止交易进程
        if self.trading_process and self.trading_process.poll() is None:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏹️ 停止交易进程...")
            try:
                self.trading_process.terminate()
                self.trading_process.wait(timeout=5)
            except:
                try:
                    self.trading_process.kill()
                except:
                    pass
        
        # 生成最终报告
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 📋 生成最终总结...")
        self.generate_report()
        
        # 保存运行总结
        self.save_summary()
        
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ✅ 系统已完全停止")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📁 报告保存在 reports/ 目录")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 👋 再见!")
    
    def save_summary(self):
        """保存运行总结"""
        try:
            summary_file = "reports/运行总结.md"
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write("# AI量化交易系统运行总结\n\n")
                f.write(f"**启动时间**: {self.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.start_time else 'N/A'}\n")
                f.write(f"**结束时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                if self.start_time:
                    uptime = datetime.now() - self.start_time
                    f.write(f"**总运行时间**: {uptime}\n")
                f.write(f"**生成报告数量**: {self.report_count}\n\n")
                f.write("## 生成的文件\n\n")
                f.write("- reports/*.json - JSON格式详细报告\n")
                f.write("- reports/*.txt - 文本格式报告\n")
                f.write("- reports/latest_report.md - 最新报告\n")
                f.write("- reports/运行总结.md - 本总结文件\n\n")
                f.write("## 使用说明\n\n")
                f.write("1. 运行 `python simple_monitor.py` 启动系统\n")
                f.write("2. 系统每30分钟自动生成运行报告\n")
                f.write("3. 按 Ctrl+C 可停止系统\n")
                f.write("4. 报告保存在 reports/ 目录下\n")
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 运行总结已保存: {summary_file}")
            
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ 保存总结失败: {e}")


def main():
    """主函数"""
    monitor = SimpleTradingMonitor()
    monitor.run()


if __name__ == "__main__":
    main()