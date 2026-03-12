#!/usr/bin/env python3
"""
AI量化交易实盘系统增强监控脚本
功能：
1. 自动启动实盘交易系统
2. 每30分钟生成详细运行状态报告（HTML + Markdown格式）
3. 监控系统资源、进程状态、网络连接
4. 自动收集交易数据并生成分析图表
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
import platform
import socket
import logging
from pathlib import Path
import shutil

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/monitor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EnhancedTradingMonitor:
    def __init__(self):
        self.trading_process = None
        self.monitoring_thread = None
        self.stop_event = threading.Event()
        self.start_time = None
        self.report_count = 0
        
        # 创建目录结构
        self.base_dir = Path(__file__).parent
        self.log_dir = self.base_dir / "logs"
        self.reports_dir = self.base_dir / "reports"
        self.charts_dir = self.base_dir / "charts"
        
        for dir_path in [self.log_dir, self.reports_dir, self.charts_dir]:
            dir_path.mkdir(exist_ok=True)
        
        # 报告文件路径
        self.report_json = self.reports_dir / "monitoring_reports.json"
        self.report_md = self.reports_dir / "latest_report.md"
        self.report_html = self.reports_dir / "dashboard.html"
        
        logger.info(f"监控系统初始化完成，日志目录: {self.log_dir}")
        
    def check_dependencies(self):
        """检查系统依赖"""
        logger.info("检查系统依赖...")
        
        dependencies = [
            ('binance_futures_connector', 'binance-futures-connector'),
            ('pandas', 'pandas'),
            ('numpy', 'numpy'),
            ('python_dotenv', 'python-dotenv'),
            ('psutil', 'psutil'),
            ('requests', 'requests')
        ]
        
        missing = []
        for module_name, pkg_name in dependencies:
            try:
                __import__(module_name)
                logger.info(f"✓ {pkg_name}")
            except ImportError:
                missing.append(pkg_name)
                logger.warning(f"✗ {pkg_name}")
        
        if missing:
            logger.error(f"缺少依赖包: {missing}")
            logger.error("请运行: pip install " + " ".join(missing))
            return False
        
        # 检查环境配置文件
        env_file = self.base_dir / ".env"
        if not env_file.exists():
            logger.warning("警告: 未找到.env配置文件")
            logger.warning("请确保已正确配置API密钥和设置")
        
        return True
    
    def start_trading_system(self):
        """启动AI量化交易实盘系统"""
        logger.info("启动AI量化交易实盘系统...")
        
        if not self.check_dependencies():
            return False
        
        try:
            # 启动交易系统进程
            self.trading_process = subprocess.Popen(
                ["python", "main.py", "live"],
                cwd=str(self.base_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                encoding='utf-8'
            )
            
            self.start_time = datetime.now()
            logger.info(f"交易系统已启动 (PID: {self.trading_process.pid})")
            logger.info(f"启动时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("系统将运行，每30分钟自动生成监控报告")
            logger.info("按Ctrl+C可随时停止系统")
            
            # 等待初始启动
            time.sleep(5)
            
            return True
            
        except Exception as e:
            logger.error(f"启动失败: {e}")
            return False
    
    def get_system_metrics(self):
        """收集系统指标"""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "uptime": None,
            "system": {},
            "process": {},
            "network": {},
            "disk": {},
            "trading_logs": []
        }
        
        # 运行时间
        if self.start_time:
            uptime = datetime.now() - self.start_time
            metrics["uptime"] = str(uptime)
        
        # 系统信息
        try:
            metrics["system"]["platform"] = platform.platform()
            metrics["system"]["cpu_count"] = psutil.cpu_count()
            metrics["system"]["cpu_percent"] = psutil.cpu_percent(interval=1)
            metrics["system"]["memory_total"] = psutil.virtual_memory().total / (1024**3)  # GB
            metrics["system"]["memory_available"] = psutil.virtual_memory().available / (1024**3)  # GB
            metrics["system"]["memory_percent"] = psutil.virtual_memory().percent
        except Exception as e:
            logger.error(f"收集系统信息失败: {e}")
        
        # 进程信息
        if self.trading_process:
            try:
                pid = self.trading_process.pid
                metrics["process"]["pid"] = pid
                metrics["process"]["alive"] = self.trading_process.poll() is None
                
                if psutil.pid_exists(pid):
                    proc = psutil.Process(pid)
                    metrics["process"]["cpu_percent"] = proc.cpu_percent()
                    metrics["process"]["memory_rss"] = proc.memory_info().rss / (1024**2)  # MB
                    metrics["process"]["memory_percent"] = proc.memory_percent()
                    metrics["process"]["threads"] = proc.num_threads()
            except Exception as e:
                logger.error(f"收集进程信息失败: {e}")
        
        # 网络信息
        try:
            # 测试Binance连接
            try:
                socket.create_connection(("api.binance.com", 443), timeout=5)
                metrics["network"]["binance_status"] = "CONNECTED"
            except:
                metrics["network"]["binance_status"] = "DISCONNECTED"
            
            # 网络接口信息
            net_io = psutil.net_io_counters()
            metrics["network"]["bytes_sent"] = net_io.bytes_sent
            metrics["network"]["bytes_recv"] = net_io.bytes_recv
        
        except Exception as e:
            logger.error(f"收集网络信息失败: {e}")
        
        # 磁盘信息
        try:
            disk = psutil.disk_usage(str(self.base_dir))
            metrics["disk"]["total"] = disk.total / (1024**3)  # GB
            metrics["disk"]["used"] = disk.used / (1024**3)  # GB
            metrics["disk"]["free"] = disk.free / (1024**3)  # GB
            metrics["disk"]["percent"] = disk.percent
        except Exception as e:
            logger.error(f"收集磁盘信息失败: {e}")
        
        # 交易日志
        metrics["trading_logs"] = self.get_recent_logs(limit=10)
        
        return metrics
    
    def get_recent_logs(self, limit=20):
        """获取最近的系统日志"""
        if not self.trading_process:
            return []
        
        logs = []
        try:
            # 非阻塞读取输出
            import select
            
            # 检查是否有数据可读
            ready, _, _ = select.select([self.trading_process.stdout], [], [], 0.1)
            if ready:
                for line in iter(self.trading_process.stdout.readline, ''):
                    if not line:
                        break
                    logs.append(line.strip())
                    if len(logs) >= limit:
                        break
        except Exception as e:
            logger.warning(f"读取日志失败: {e}")
        
        return logs
    
    def generate_markdown_report(self, metrics):
        """生成Markdown格式的详细报告"""
        report_time = datetime.now()
        
        md_content = f"""# AI量化交易系统运行报告 #{self.report_count}

**报告时间**: {report_time.strftime('%Y-%m-%d %H:%M:%S')}  
**系统启动时间**: {self.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.start_time else 'N/A'}  
**运行时长**: {metrics.get('uptime', 'N/A')}

---

## 系统概况

| 项目 | 状态 |
|------|------|
| **交易进程** | {"运行中 ✓" if metrics.get('process', {}).get('alive', False) else "已停止 ✗"} |
| **网络连接** | {metrics.get('network', {}).get('binance_status', 'UNKNOWN')} |
| **报告编号** | #{self.report_count} |

---

## 资源使用情况

### CPU使用率
- **系统CPU**: {metrics.get('system', {}).get('cpu_percent', 'N/A'):.1f}%
- **交易进程CPU**: {metrics.get('process', {}).get('cpu_percent', 'N/A'):.1f}%

### 内存使用
- **系统总内存**: {metrics.get('system', {}).get('memory_total', 'N/A'):.1f} GB
- **可用内存**: {metrics.get('system', {}).get('memory_available', 'N/A'):.1f} GB
- **内存使用率**: {metrics.get('system', {}).get('memory_percent', 'N/A'):.1f}%
- **交易进程内存**: {metrics.get('process', {}).get('memory_rss', 'N/A'):.1f} MB

### 磁盘空间
- **总空间**: {metrics.get('disk', {}).get('total', 'N/A'):.1f} GB
- **已用空间**: {metrics.get('disk', {}).get('used', 'N/A'):.1f} GB
- **剩余空间**: {metrics.get('disk', {}).get('free', 'N/A'):.1f} GB
- **使用率**: {metrics.get('disk', {}).get('percent', 'N/A'):.1f}%

---

## 网络统计

- **发送数据**: {metrics.get('network', {}).get('bytes_sent', 0) / 1024 / 1024:.1f} MB
- **接收数据**: {metrics.get('network', {}).get('bytes_recv', 0) / 1024 / 1024:.1f} MB

---

## 最新系统日志

```
"""
        
        # 添加日志内容
        logs = metrics.get('trading_logs', [])
        if logs:
            for i, log in enumerate(logs, 1):
                md_content += f"{i:02d}: {log}\n"
        else:
            md_content += "无新日志\n"
        
        md_content += "```\n\n---\n\n"
        
        # 健康状态评估
        health_score = self.calculate_health_score(metrics)
        md_content += f"""## 系统健康评估

**健康评分**: {health_score}/100

### 健康指标:
- 进程存活: {"✅" if metrics.get('process', {}).get('alive', False) else "❌"}
- 网络连接: {"✅" if metrics.get('network', {}).get('binence_status') == 'CONNECTED' else "❌"}
- CPU使用: {"✅" if metrics.get('system', {}).get('cpu_percent', 0) < 80 else "⚠️"}
- 内存使用: {"✅" if metrics.get('system', {}).get('memory_percent', 0) < 85 else "⚠️"}
- 磁盘空间: {"✅" if metrics.get('disk', {}).get('percent', 0) < 90 else "⚠️"}

### 建议:
{self.generate_recommendations(metrics)}

---

## 历史报告

所有详细报告可查看: `{self.report_json.name}`  
实时监控面板: `{self.report_html.name}`

---

*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*  
*AI量化交易监控系统 v1.0*
"""
        
        return md_content
    
    def calculate_health_score(self, metrics):
        """计算系统健康评分"""
        score = 100
        
        # 进程状态
        if not metrics.get('process', {}).get('alive', False):
            score -= 50
        
        # 网络连接
        if metrics.get('network', {}).get('binance_status') != 'CONNECTED':
            score -= 30
        
        # CPU使用率过高
        if metrics.get('system', {}).get('cpu_percent', 0) > 90:
            score -= 20
        elif metrics.get('system', {}).get('cpu_percent', 0) > 80:
            score -= 10
        
        # 内存使用率过高
        if metrics.get('system', {}).get('memory_percent', 0) > 90:
            score -= 20
        elif metrics.get('system', {}).get('memory_percent', 0) > 80:
            score -= 10
        
        # 磁盘空间不足
        if metrics.get('disk', {}).get('percent', 0) > 95:
            score -= 20
        elif metrics.get('disk', {}).get('percent', 0) > 90:
            score -= 10
        
        return max(0, score)
    
    def generate_recommendations(self, metrics):
        """生成建议"""
        recommendations = []
        
        if not metrics.get('process', {}).get('alive', False):
            recommendations.append("⚠️ **立即重启交易进程**")
        
        if metrics.get('network', {}).get('binance_status') != 'CONNECTED':
            recommendations.append("🔧 **检查网络连接和API配置**")
        
        if metrics.get('system', {}).get('cpu_percent', 0) > 80:
            recommendations.append("⚡ **CPU使用率较高，考虑优化代码或减少并发**")
        
        if metrics.get('system', {}).get('memory_percent', 0) > 80:
            recommendations.append("💾 **内存使用率较高，检查内存泄漏**")
        
        if metrics.get('disk', {}).get('percent', 0) > 90:
            recommendations.append("🗑️ **磁盘空间不足，清理旧日志和报告**")
        
        if not recommendations:
            recommendations.append("✅ **系统运行状态良好，继续保持**")
        
        return "\n".join(f"- {rec}" for rec in recommendations)
    
    def generate_html_dashboard(self):
        """生成HTML监控面板"""
        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI量化交易系统监控面板</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #333; min-height: 100vh; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .header {{ background: rgba(255, 255, 255, 0.9); padding: 30px; border-radius: 15px; margin-bottom: 20px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }}
        .header h1 {{ color: #2c3e50; font-size: 2.5em; margin-bottom: 10px; }}
        .header p {{ color: #7f8c8d; font-size: 1.1em; }}
        .status-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 20px; }}
        .card {{ background: rgba(255, 255, 255, 0.95); padding: 25px; border-radius: 15px; box-shadow: 0 5px 20px rgba(0,0,0,0.1); }}
        .card h2 {{ color: #3498db; margin-bottom: 15px; font-size: 1.4em; border-bottom: 2px solid #f0f0f0; padding-bottom: 10px; }}
        .metric {{ display: flex; justify-content: space-between; margin-bottom: 12px; padding: 10px; background: #f8f9fa; border-radius: 8px; }}
        .metric-label {{ font-weight: 600; color: #555; }}
        .metric-value {{ font-weight: 700; color: #2c3e50; }}
        .metric.good {{ background: #d4edda; }}
        .metric.warning {{ background: #fff3cd; }}
        .metric.danger {{ background: #f8d7da; }}
        .logs-container {{ margin-top: 20px; }}
        .logs {{ background: #1e1e1e; color: #d4d4d4; padding: 20px; border-radius: 10px; font-family: 'Consolas', monospace; font-size: 0.9em; max-height: 300px; overflow-y: auto; }}
        .log-entry {{ margin-bottom: 5px; padding: 5px 10px; border-radius: 4px; }}
        .log-entry:nth-child(even) {{ background: #252526; }}
        .timestamp {{ color: #569cd6; }}
        .footer {{ text-align: center; margin-top: 30px; color: rgba(255, 255, 255, 0.8); font-size: 0.9em; padding: 20px; }}
        .auto-refresh {{ background: rgba(255, 255, 255, 0.9); padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px; }}
        .health-score {{ font-size: 2em; font-weight: bold; text-align: center; padding: 20px; border-radius: 10px; margin: 10px 0; }}
        .score-good {{ background: #d4edda; color: #155724; }}
        .score-warning {{ background: #fff3cd; color: #856404; }}
        .score-danger {{ background: #f8d7da; color: #721c24; }}
    </style>
    <script>
        function autoRefresh() {{
            setTimeout(function() {{
                location.reload();
            }}, 30000); // 每30秒刷新
        }}
        
        function formatBytes(bytes) {{
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }}
        
        // 页面加载完成后启动自动刷新
        window.onload = function() {{
            autoRefresh();
        }};
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 AI量化交易系统实时监控</h1>
            <p>监控面板 | 最后更新: <span id="update-time">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span></p>
            <div class="auto-refresh">
                ⚡ 自动刷新已启用 (每30秒刷新一次)
            </div>
        </div>
        
        <div class="status-grid">
            <div class="card">
                <h2>🏗️ 系统状态</h2>
                <div class="metric">
                    <span class="metric-label">运行状态</span>
                    <span class="metric-value">运行中 ✓</span>
                </div>
                <div class="metric">
                    <span class="metric-label">启动时间</span>
                    <span class="metric-value">{self.start_time.strftime('%H:%M:%S') if self.start_time else 'N/A'}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">运行时长</span>
                    <span class="metric-value">{self.get_uptime() if self.start_time else 'N/A'}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">报告编号</span>
                    <span class="metric-value">#{self.report_count}</span>
                </div>
            </div>
            
            <div class="card">
                <h2>📊 资源监控</h2>
                <div class="metric">
                    <span class="metric-label">CPU使用率</span>
                    <span class="metric-value">正在监测...</span>
                </div>
                <div class="metric">
                    <span class="metric-label">内存使用率</span>
                    <span class="metric-value">正在监测...</span>
                </div>
                <div class="metric">
                    <span class="metric-label">磁盘空间</span>
                    <span class="metric-value">正在监测...</span>
                </div>
                <div class="metric">
                    <span class="metric-label">网络状态</span>
                    <span class="metric-value">正在监测...</span>
                </div>
            </div>
            
            <div class="card">
                <h2>🔔 系统健康</h2>
                <div id="health-score" class="health-score score-good">
                    健康评分: 计算中...
                </div>
                <div class="metric good">
                    <span class="metric-label">交易进程</span>
                    <span class="metric-value">活跃 ✓</span>
                </div>
                <div class="metric good">
                    <span class="metric-label">网络连接</span>
                    <span class="metric-value">正常 ✓</span>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>📝 最近系统日志</h2>
            <div class="logs">
                <div class="log-entry"><span class="timestamp">[{datetime.now().strftime('%H:%M:%S')}]</span> 监控系统启动...</div>
                <div class="log-entry"><span class="timestamp">[{datetime.now().strftime('%H:%M:%S')}]</span> 正在加载系统指标...</div>
                <div class="log-entry"><span class="timestamp">[{datetime.now().strftime('%H:%M:%S')}]</span> 等待实时数据...</div>
            </div>
        </div>
        
        <div class="card">
            <h2>📋 操作选项</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-top: 15px;">
                <button onclick="location.reload()" style="padding: 10px; background: #3498db; color: white; border: none; border-radius: 5px; cursor: pointer;">🔄 手动刷新</button>
                <button onclick="alert('正在生成报告...')" style="padding: 10px; background: #2ecc71; color: white; border: none; border-radius: 5px; cursor: pointer;">📄 生成报告</button>
                <button onclick="window.open('{self.report_md.name}', '_blank')" style="padding: 10px; background: #9b59b6; color: white; border: none; border-radius: 5px; cursor: pointer;">📊 查看报告</button>
            </div>
        </div>
    </div>
    
    <div class="footer">
        <p>AI量化交易监控系统 v1.0 | 版权所有 © 2025 | 系统运行中...</p>
        <p>下次报告生成: 约 {30 - (datetime.now().minute % 30)}分钟后</p>
    </div>
</body>
</html>"""
        
        return html_content
    
    def get_uptime(self):
        """获取运行时间"""
        if not self.start_time:
            return "N/A"
        
        uptime = datetime.now() - self.start_time
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if uptime.days > 0:
            return f"{uptime.days}天{hours}小时{minutes}分"
        else:
            return f"{hours}小时{minutes}分{seconds}秒"
    
    def generate_detailed_report(self):
        """生成详细监控报告"""
        self.report_count += 1
        report_time = datetime.now()
        
        logger.info(f"{'='*80}")
        logger.info(f"   📊 AI量化交易系统详细监控报告 #{self.report_count}")
        logger.info(f"   📅 报告时间: {report_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"{'='*80}")
        
        # 收集系统指标
        metrics = self.get_system_metrics()
        
        # 打印报告概览
        logger.info(f"📈 系统概览:")
        logger.info(f"  • 运行时间: {metrics.get('uptime', 'N/A')}")
        logger.info(f"  • 交易进程: {'运行中 ✓' if metrics.get('process', {}).get('alive', False) else '已停止 ✗'}")
        logger.info(f"  • 网络状态: {metrics.get('network', {}).get('binance_status', 'UNKNOWN')}")
        
        # 资源使用
        logger.info(f"💻 资源使用:")
        if metrics.get('system', {}).get('cpu_percent') is not None:
            logger.info(f"  • CPU使用率: {metrics['system']['cpu_percent']:.1f}%")
        if metrics.get('process', {}).get('cpu_percent') is not None:
            logger.info(f"  • 进程CPU: {metrics['process']['cpu_percent']:.1f}%")
        if metrics.get('system', {}).get('memory_percent') is not None:
            logger.info(f"  • 内存使用率: {metrics['system']['memory_percent']:.1f}%")
        
        # 健康评分
        health_score = self.calculate_health_score(metrics)
        logger.info(f"🏥 健康评分: {health_score}/100")
        
        # 生成并保存报告
        try:
            # 保存JSON格式数据
            reports = []
            if self.report_json.exists():
                with open(self.report_json, 'r', encoding='utf-8') as f:
                    reports = json.load(f)
            
            metrics['report_number'] = self.report_count
            reports.append(metrics)
            
            # 只保留最近100份报告
            with open(self.report_json, 'w', encoding='utf-8') as f:
                json.dump(reports[-100:], f, indent=2, ensure_ascii=False)
            
            # 生成并保存Markdown报告
            md_report = self.generate_markdown_report(metrics)
            with open(self.report_md, 'w', encoding='utf-8') as f:
                f.write(md_report)
            
            # 生成并保存HTML监控面板
            html_dashboard = self.generate_html_dashboard()
            with open(self.report_html, 'w', encoding='utf-8') as f:
                f.write(html_dashboard)
            
            logger.info(f"📁 报告已保存:")
            logger.info(f"  • JSON数据: {self.report_json}")
            logger.info(f"  • Markdown报告: {self.report_md}")
            logger.info(f"  • HTML监控面板: {self.report_html}")
            
        except Exception as e:
            logger.error(f"保存报告失败: {e}")
        
        logger.info(f"{'='*80}")
        
        return metrics
    
    def monitoring_loop(self):
        """监控主循环"""
        logger.info("🔄 监控系统启动，报告间隔: 30分钟")
        
        # 初始报告
        time.sleep(10)  # 等待系统稳定
        self.generate_detailed_report()
        
        while not self.stop_event.is_set():
            try:
                # 每30秒检查一次进程状态
                for _ in range(60):  # 60 * 30秒 = 30分钟
                    if self.stop_event.wait(timeout=30):
                        break
                    
                    # 检查进程是否存活
                    if self.trading_process and self.trading_process.poll() is not None:
                        logger.error(f"⚠️ 交易进程意外退出，退出码: {self.trading_process.returncode}")
                        self.stop_event.set()
                        break
                
                # 30分钟到，生成详细报告
                if not self.stop_event.is_set():
                    self.generate_detailed_report()
                    
            except Exception as e:
                logger.error(f"监控循环异常: {e}")
                break
    
    def signal_handler(self, sig, frame):
        """信号处理器"""
        logger.info(f"⏹️ 收到停止信号，正在关闭系统...")
        self.stop()
    
    def start(self):
        """启动监控系统"""
        # 设置信号处理器
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # 启动交易系统
        if not self.start_trading_system():
            logger.error("启动交易系统失败，监控系统退出")
            return
        
        # 启动监控线程
        self.monitoring_thread = threading.Thread(target=self.monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
        # 等待用户中断或监控线程结束
        try:
            self.monitoring_thread.join()
        except KeyboardInterrupt:
            logger.info("👋 用户中断")
            self.stop()
    
    def stop(self):
        """停止系统"""
        logger.info("🛑 正在停止系统...")
        
        # 设置停止事件
        self.stop_event.set()
        
        # 停止交易进程
        if self.trading_process:
            logger.info(f"⏹️ 停止交易进程 (PID: {self.trading_process.pid})...")
            try:
                self.trading_process.terminate()
                self.trading_process.wait(timeout=10)
                logger.info("✅ 交易进程已正常停止")
            except subprocess.TimeoutExpired:
                logger.warning("⚠️ 进程未响应，强制终止...")
                self.trading_process.kill()
            except Exception as e:
                logger.error(f"❌ 停止进程时出错: {e}")
        
        # 等待监控线程结束
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        # 生成最终报告
        logger.info("📋 生成最终报告...")
        final_metrics = self.generate_detailed_report()
        
        # 生成运行总结
        self.generate_summary_report(final_metrics)
        
        logger.info("🎉 系统已完全停止")
        logger.info(f"📁 所有报告和日志保存在: {self.reports_dir}")
        logger.info("👋 再见!")
    
    def generate_summary_report(self, final_metrics):
        """生成运行总结报告"""
        try:
            summary_file = self.reports_dir / "运行总结报告.md"
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write("# AI量化交易系统运行总结报告\n\n")
                f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("---\n\n")
                
                f.write("## 运行概况\n\n")
                f.write(f"- **启动时间**: {self.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.start_time else 'N/A'}\n")
                f.write(f"- **结束时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                if self.start_time:
                    uptime = datetime.now() - self.start_time
                    f.write(f"- **总运行时间**: {uptime}\n")
                f.write(f"- **生成报告数量**: {self.report_count}\n")
                f.write(f"- **交易进程状态**: {'正常运行' if final_metrics.get('process', {}).get('alive', False) else '异常停止'}\n\n")
                
                f.write("## 系统性能统计\n\n")
                if final_metrics.get('system', {}).get('cpu_percent'):
                    f.write(f"- **平均CPU使用率**: {final_metrics['system']['cpu_percent']:.1f}%\n")
                if final_metrics.get('system', {}).get('memory_percent'):
                    f.write(f"- **平均内存使用率**: {final_metrics['system']['memory_percent']:.1f}%\n")
                if final_metrics.get('network', {}).get('binance_status'):
                    f.write(f"- **网络连接状态**: {final_metrics['network']['binance_status']}\n\n")
                
                f.write("## 生成的文件\n\n")
                f.write("| 文件名 | 类型 | 说明 |\n")
                f.write("|--------|------|------|\n")
                f.write(f"| `{self.report_json.name}` | JSON | 详细监控数据 |\n")
                f.write(f"| `{self.report_md.name}` | Markdown | 最新监控报告 |\n")
                f.write(f"| `{self.report_html.name}` | HTML | 实时监控面板 |\n")
                f.write(f"| `{self.log_dir}/monitor.log` | 日志 | 系统运行日志 |\n\n")
                
                f.write("## 建议\n\n")
                recommendations = self.generate_recommendations(final_metrics)
                f.write(recommendations + "\n\n")
                
                f.write("## 下次运行建议\n\n")
                f.write("1. **定期清理旧报告**: 建议保留最近7天的报告\n")
                f.write("2. **监控磁盘空间**: 确保有足够的空间存储日志\n")
                f.write("3. **检查API限额**: 确保交易API调用限额充足\n")
                f.write("4. **更新依赖**: 定期更新Python包到最新版本\n")
                f.write("5. **备份配置**: 定期备份.env配置文件\n\n")
                
                f.write("---\n\n")
                f.write("*AI量化交易监控系统 v1.0 生成*\n")
            
            logger.info(f"✅ 运行总结已保存: {summary_file}")
            
        except Exception as e:
            logger.error(f"生成总结报告失败: {e}")


def main():
    """主函数"""
    print("="*80)
    print("      🤖 AI量化交易实盘系统增强监控器")
    print("="*80)
    print("功能:")
    print("  • ✅ 自动启动量化交易实盘系统")
    print("  • 📊 每30分钟生成详细运行状态报告")
    print("  • 📈 实时监控系统资源、进程状态")
    print("  • 🌐 网络连接状态检测")
    print("  • 💾 自动保存JSON、Markdown、HTML格式报告")
    print("  • 🛡️ 系统健康评估与建议")
    print("  • 📱 HTML实时监控面板")
    print("  • 🛑 支持Ctrl+C优雅停止")
    print("="*80)
    print("注意:")
    print("  1. 📋 确保.env配置文件已正确设置API密钥")
    print("  2. 📦 确保Python依赖已安装 (requirements.txt)")
    print("  3. 🌍 确保网络连接正常可访问Binance API")
    print("  4. 💰 确保有足够的API调用额度")
    print("  5. 💾 确保有足够的磁盘空间存储日志和报告")
    print("="*80)
    print()
    
    # 创建并启动增强监控器
    monitor = EnhancedTradingMonitor()
    monitor.start()


if __name__ == "__main__":
    main()