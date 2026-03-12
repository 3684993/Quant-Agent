#!/usr/bin/env python3
"""
实盘交易系统监控脚本
每30分钟生成一次系统运行报告
"""

import subprocess
import time
import signal
import sys
import os
import threading
from datetime import datetime, timedelta
import psutil
import json

class TradingSystemMonitor:
    def __init__(self):
        self.trading_process = None
        self.monitoring_thread = None
        self.stop_event = threading.Event()
        self.start_time = None
        self.report_count = 0
        
        # 日志文件路径
        self.log_dir = "logs"
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 报告文件
        self.report_file = os.path.join(self.log_dir, "monitoring_reports.json")
        
    def start_trading_system(self):
        """启动实盘交易系统"""
        print(f"[{datetime.now()}] 启动AI量化交易实盘系统...")
        
        # 检查依赖
        try:
            import binance_futures_connector
            import pandas
            print("✓ 核心依赖检查通过")
        except ImportError as e:
            print(f"✗ 缺少依赖: {e}")
            print("请运行: pip install -r requirements.txt")
            return False
        
        # 启动交易系统
        try:
            self.trading_process = subprocess.Popen(
                ["python", "main.py", "live"],
                cwd=os.path.dirname(os.path.abspath(__file__)),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            self.start_time = datetime.now()
            print(f"[{datetime.now()}] 实盘交易系统已启动 (PID: {self.trading_process.pid})")
            print(f"[{datetime.now()}] 系统将运行，每30分钟自动生成监控报告")
            print(f"[{datetime.now()}] 按Ctrl+C可随时停止系统")
            return True
        except Exception as e:
            print(f"[{datetime.now()}] 启动失败: {e}")
            return False
    
    def read_logs(self):
        """读取交易系统的输出日志"""
        if not self.trading_process:
            return []
            
        logs = []
        try:
            # 非阻塞读取
            import select
            import fcntl
            import os
            
            # 设置非阻塞
            fd = self.trading_process.stdout.fileno()
            fl = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            
            # 读取可用数据
            while True:
                try:
                    line = self.trading_process.stdout.readline()
                    if not line:
                        break
                    logs.append(line.strip())
                except (IOError, OSError):
                    break
                    
        except Exception:
            pass
            
        return logs[-20:]  # 返回最近20行日志
    
    def check_system_health(self):
        """检查系统健康状态"""
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "uptime": None,
            "cpu_usage": None,
            "memory_usage": None,
            "trading_process": None,
            "network_status": "UNKNOWN",
            "log_activity": False
        }
        
        # 计算运行时间
        if self.start_time:
            uptime = datetime.now() - self.start_time
            health_status["uptime"] = str(uptime)
        
        # 检查交易进程状态
        if self.trading_process:
            try:
                pid = self.trading_process.pid
                health_status["trading_process"] = {
                    "pid": pid,
                    "alive": self.trading_process.poll() is None
                }
                
                # 获取进程资源使用情况
                if psutil.pid_exists(pid):
                    process = psutil.Process(pid)
                    health_status["cpu_usage"] = process.cpu_percent(interval=0.1)
                    health_status["memory_usage"] = process.memory_info().rss / 1024 / 1024  # MB
            except Exception as e:
                health_status["trading_process"] = {"error": str(e)}
        
        # 检查网络连接
        try:
            import socket
            socket.create_connection(("api.binance.com", 443), timeout=5)
            health_status["network_status"] = "CONNECTED"
        except Exception:
            health_status["network_status"] = "DISCONNECTED"
        
        # 检查日志活动
        logs = self.read_logs()
        health_status["log_activity"] = len(logs) > 0
        health_status["recent_logs"] = logs
        
        return health_status
    
    def generate_report(self):
        """生成监控报告"""
        self.report_count += 1
        report_time = datetime.now()
        
        print(f"\n{'='*80}")
        print(f"   AI量化交易系统监控报告 #{self.report_count}")
        print(f"   报告时间: {report_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")
        
        # 获取系统健康状态
        health = self.check_system_health()
        
        # 打印报告
        print(f"运行状态:")
        print(f"  • 运行时间: {health.get('uptime', 'N/A')}")
        print(f"  • 报告计数: {self.report_count}")
        
        if health.get('trading_process'):
            proc = health['trading_process']
            if isinstance(proc, dict) and 'alive' in proc:
                status = "运行中 ✓" if proc['alive'] else "已停止 ✗"
                print(f"  • 交易进程: PID {proc.get('pid', 'N/A')} - {status}")
            else:
                print(f"  • 交易进程: {proc}")
        
        print(f"\n系统资源:")
        if health.get('cpu_usage') is not None:
            print(f"  • CPU使用率: {health['cpu_usage']:.1f}%")
        if health.get('memory_usage') is not None:
            print(f"  • 内存使用: {health['memory_usage']:.1f} MB")
        
        print(f"\n网络状态:")
        print(f"  • Binance连接: {health.get('network_status', 'N/A')}")
        print(f"  • 日志活动: {'活跃 ✓' if health.get('log_activity') else '无活动 ✗'}")
        
        # 显示最近的日志
        recent_logs = health.get('recent_logs', [])
        if recent_logs:
            print(f"\n最近系统日志 ({len(recent_logs)}行):")
            for i, log in enumerate(recent_logs[-5:]):  # 显示最后5行
                print(f"  [{i+1}] {log}")
        else:
            print(f"\n系统日志: 无新日志")
        
        print(f"{'='*80}\n")
        
        # 保存报告到文件
        self.save_report(health)
        
        return health
    
    def save_report(self, health_data):
        """保存报告到JSON文件"""
        try:
            reports = []
            if os.path.exists(self.report_file):
                with open(self.report_file, 'r', encoding='utf-8') as f:
                    reports = json.load(f)
            
            reports.append(health_data)
            
            with open(self.report_file, 'w', encoding='utf-8') as f:
                json.dump(reports[-50:], f, indent=2, ensure_ascii=False)  # 保存最近50份报告
            
            # 也保存为文本格式便于查看
            text_report_file = os.path.join(self.log_dir, "monitoring_reports.txt")
            with open(text_report_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"报告时间: {health_data['timestamp']}\n")
                f.write(f"运行时间: {health_data.get('uptime', 'N/A')}\n")
                f.write(f"{'='*80}\n\n")
            
        except Exception as e:
            print(f"[{datetime.now()}] 保存报告失败: {e}")
    
    def monitoring_loop(self):
        """监控循环"""
        print(f"[{datetime.now()}] 监控系统启动，报告间隔: 30分钟")
        
        while not self.stop_event.is_set():
            try:
                # 每30秒检查一次进程状态
                for _ in range(60):  # 60 * 30秒 = 30分钟
                    if self.stop_event.wait(timeout=30):
                        break
                    
                    # 检查进程是否存活
                    if self.trading_process and self.trading_process.poll() is not None:
                        print(f"[{datetime.now()}] 交易进程意外退出，退出码: {self.trading_process.returncode}")
                        self.stop_event.set()
                        break
                
                # 30分钟到，生成报告
                if not self.stop_event.is_set():
                    self.generate_report()
                    
            except Exception as e:
                print(f"[{datetime.now()}] 监控循环异常: {e}")
                break
    
    def signal_handler(self, sig, frame):
        """信号处理器"""
        print(f"\n[{datetime.now()}] 收到停止信号，正在关闭系统...")
        self.stop()
    
    def start(self):
        """启动监控系统"""
        # 设置信号处理器
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # 启动交易系统
        if not self.start_trading_system():
            return
        
        # 启动监控线程
        self.monitoring_thread = threading.Thread(target=self.monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
        # 等待用户中断
        try:
            # 等待监控线程结束
            self.monitoring_thread.join()
        except KeyboardInterrupt:
            print(f"\n[{datetime.now()}] 用户中断")
            self.stop()
    
    def stop(self):
        """停止系统"""
        print(f"\n[{datetime.now()}] 正在停止系统...")
        
        # 设置停止事件
        self.stop_event.set()
        
        # 停止交易进程
        if self.trading_process:
            print(f"[{datetime.now()}] 停止交易进程 (PID: {self.trading_process.pid})...")
            try:
                self.trading_process.terminate()
                self.trading_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                print(f"[{datetime.now()}] 强制终止进程...")
                self.trading_process.kill()
            except Exception as e:
                print(f"[{datetime.now()}] 停止进程时出错: {e}")
        
        # 等待监控线程结束
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        # 生成最终报告
        print(f"\n[{datetime.now()}] 生成最终报告...")
        final_report = self.generate_report()
        
        # 保存汇总报告
        try:
            summary_file = os.path.join(self.log_dir, "system_summary.txt")
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write("AI量化交易系统运行总结\n")
                f.write("="*50 + "\n")
                f.write(f"启动时间: {self.start_time}\n")
                f.write(f"结束时间: {datetime.now()}\n")
                if self.start_time:
                    uptime = datetime.now() - self.start_time
                    f.write(f"总运行时间: {uptime}\n")
                f.write(f"生成报告数量: {self.report_count}\n")
                f.write(f"交易进程状态: {final_report.get('trading_process', 'N/A')}\n")
                f.write(f"网络状态: {final_report.get('network_status', 'N/A')}\n")
                f.write("="*50 + "\n")
            
            print(f"[{datetime.now()}] 运行总结已保存到: {summary_file}")
        except Exception as e:
            print(f"[{datetime.now()}] 保存总结失败: {e}")
        
        print(f"[{datetime.now()}] 系统已完全停止")
        print(f"[{datetime.now()}] 监控报告保存在: {self.log_dir}/ 目录下")

def main():
    """主函数"""
    print("="*80)
    print("      AI量化交易实盘系统监控器")
    print("="*80)
    print("功能:")
    print("  • 自动启动量化交易实盘系统")
    print("  • 每30分钟生成系统运行状态报告")
    print("  • 实时监控进程状态和系统资源")
    print("  • 自动保存运行日志和报告")
    print("  • 支持Ctrl+C优雅停止")
    print("="*80)
    print("注意:")
    print("  1. 确保.env配置文件已正确设置")
    print("  2. 确保Python依赖已安装 (requirements.txt)")
    print("  3. 确保网络连接正常")
    print("  4. 确保有足够的API调用额度")
    print("="*80)
    print()
    
    # 创建并启动监控器
    monitor = TradingSystemMonitor()
    monitor.start()

if __name__ == "__main__":
    main()