#!/usr/bin/env python3
# zomode/anomaly_detection.py
"""
Real-Time Anomaly Detection Engine for AISH Z-Omode
Monitors network traffic for suspicious activity and provides alerts
"""

import os
import sys
import json
import time
import threading
import socket
import subprocess
import platform
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Dict, List, Set, Optional, Any
import ipaddress

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:
    class Fore:
        RED = GREEN = YELLOW = CYAN = MAGENTA = LIGHTRED_EX = LIGHTCYAN_EX = ''
    class Style:
        RESET_ALL = ''

# Optional dependencies with graceful degradation
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print(f"{Fore.YELLOW}⚠ psutil not available. Limited system monitoring.{Style.RESET_ALL}")

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# Constants
GEOIP_API = "http://ip-api.com/json/"
MONITOR_INTERVAL = 5  # seconds
MAX_HISTORY = 1000
ANOMALY_THRESHOLD = {
    'new_country': True,
    'port_scan_threshold': 10,  # ports scanned in 60 seconds
    'traffic_spike_multiplier': 3.0,  # 3x normal traffic
    'suspicious_ports': [23, 135, 139, 445, 1433, 3389, 5900]
}

class NetworkMonitor:
    """Real-time network anomaly detection"""
    
    def __init__(self):
        self.is_monitoring = False
        self.monitor_thread = None
        self.anomalies = deque(maxlen=MAX_HISTORY)
        self.baseline_traffic = defaultdict(float)
        self.known_countries = set()
        self.connection_history = deque(maxlen=500)
        self.port_scan_tracker = defaultdict(list)
        self.load_known_countries()
        
    def load_known_countries(self):
        """Load previously seen countries from file"""
        try:
            config_path = os.path.expanduser("~/.aish_known_countries.json")
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    self.known_countries = set(json.load(f))
        except Exception:
            pass
    
    def save_known_countries(self):
        """Save known countries to file"""
        try:
            config_path = os.path.expanduser("~/.aish_known_countries.json")
            with open(config_path, 'w') as f:
                json.dump(list(self.known_countries), f, indent=2)
        except Exception:
            pass
    
    def get_country_for_ip(self, ip: str) -> Optional[str]:
        """Get country for IP address using GeoIP API"""
        if not HAS_REQUESTS:
            return None
        try:
            if ipaddress.ip_address(ip).is_private:
                return "Local"
            
            response = requests.get(f"{GEOIP_API}{ip}", timeout=2)
            if response.status_code == 200:
                data = response.json()
                return data.get('country', 'Unknown')
        except Exception:
            pass
        return None
    
    def get_active_connections(self) -> List[Dict]:
        """Get active network connections"""
        if not HAS_PSUTIL:
            return []
        
        connections = []
        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.status == 'ESTABLISHED' and conn.raddr:
                    connections.append({
                        'local': f"{conn.laddr.ip}:{conn.laddr.port}",
                        'remote': f"{conn.raddr.ip}:{conn.raddr.port}",
                        'pid': conn.pid,
                        'status': conn.status,
                        'timestamp': time.time()
                    })
        except Exception:
            pass
        return connections
    
    def detect_port_scan(self, connections: List[Dict]) -> List[Dict]:
        """Detect potential port scanning activity"""
        anomalies = []
        current_time = time.time()
        
        # Group connections by remote IP
        ip_connections = defaultdict(list)
        for conn in connections:
            remote_ip = conn['remote'].split(':')[0]
            ip_connections[remote_ip].append(conn)
        
        # Check for rapid connections to multiple ports from same IP
        for ip, conns in ip_connections.items():
            recent_ports = set()
            for conn in conns:
                if current_time - conn['timestamp'] < 60:  # Last minute
                    port = conn['remote'].split(':')[1]
                    recent_ports.add(port)
            
            if len(recent_ports) >= ANOMALY_THRESHOLD['port_scan_threshold']:
                anomalies.append({
                    'type': 'port_scan',
                    'severity': 'high',
                    'source_ip': ip,
                    'ports_scanned': len(recent_ports),
                    'timestamp': current_time,
                    'description': f"Potential port scan from {ip} - {len(recent_ports)} ports in 60s"
                })
        
        return anomalies
    
    def detect_foreign_connections(self, connections: List[Dict]) -> List[Dict]:
        """Detect connections to new countries"""
        anomalies = []
        
        for conn in connections:
            remote_ip = conn['remote'].split(':')[0]
            
            # Skip local/private IPs
            try:
                if ipaddress.ip_address(remote_ip).is_private:
                    continue
            except ValueError:
                continue
            
            country = self.get_country_for_ip(remote_ip)
            if country and country not in ['Local', 'Unknown']:
                if country not in self.known_countries:
                    self.known_countries.add(country)
                    self.save_known_countries()
                    
                    anomalies.append({
                        'type': 'new_country',
                        'severity': 'medium',
                        'country': country,
                        'remote_ip': remote_ip,
                        'timestamp': time.time(),
                        'description': f"First connection to {country} ({remote_ip})"
                    })
        
        return anomalies
    
    def detect_suspicious_ports(self, connections: List[Dict]) -> List[Dict]:
        """Detect connections to commonly exploited ports"""
        anomalies = []
        
        for conn in connections:
            remote_port = int(conn['remote'].split(':')[1])
            if remote_port in ANOMALY_THRESHOLD['suspicious_ports']:
                anomalies.append({
                    'type': 'suspicious_port',
                    'severity': 'high',
                    'port': remote_port,
                    'remote_ip': conn['remote'].split(':')[0],
                    'timestamp': time.time(),
                    'description': f"Connection to suspicious port {remote_port}"
                })
        
        return anomalies
    
    def monitor_loop(self):
        """Main monitoring loop running in background thread"""
        print(f"{Fore.GREEN}🛡️ Anomaly detection started{Style.RESET_ALL}")
        
        while self.is_monitoring:
            try:
                # Get current connections
                connections = self.get_active_connections()
                self.connection_history.extend(connections)
                
                # Run detection algorithms
                anomalies = []
                anomalies.extend(self.detect_port_scan(connections))
                anomalies.extend(self.detect_foreign_connections(connections))
                anomalies.extend(self.detect_suspicious_ports(connections))
                
                # Process any detected anomalies
                for anomaly in anomalies:
                    self.handle_anomaly(anomaly)
                
                time.sleep(MONITOR_INTERVAL)
                
            except Exception as e:
                print(f"{Fore.RED}Monitor error: {e}{Style.RESET_ALL}")
                time.sleep(MONITOR_INTERVAL)
    
    def handle_anomaly(self, anomaly: Dict):
        """Handle detected anomaly with alert and logging"""
        self.anomalies.append(anomaly)
        
        # Visual alert based on severity
        if anomaly['severity'] == 'high':
            self.critical_alert(anomaly)
        elif anomaly['severity'] == 'medium':
            self.warning_alert(anomaly)
        else:
            self.info_alert(anomaly)
        
        # Log to file
        self.log_anomaly(anomaly)
    
    def critical_alert(self, anomaly: Dict):
        """Display critical security alert"""
        print(f"\n{Fore.RED}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.RED}🚨 CRITICAL SECURITY ALERT 🚨{Style.RESET_ALL}")
        print(f"{Fore.RED}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Type: {anomaly['type'].upper()}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Time: {datetime.fromtimestamp(anomaly['timestamp']).strftime('%H:%M:%S')}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Details: {anomaly['description']}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}💡 Run 'onist investigate {len(self.anomalies)}' for details{Style.RESET_ALL}")
        print(f"{Fore.RED}{'='*60}{Style.RESET_ALL}\n")
    
    def warning_alert(self, anomaly: Dict):
        """Display warning alert"""
        print(f"\n{Fore.YELLOW}⚠️  SECURITY WARNING{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{anomaly['description']}{Style.RESET_ALL}")
        print(f"{Fore.LIGHTBLACK_EX}[{datetime.fromtimestamp(anomaly['timestamp']).strftime('%H:%M:%S')}] ID: {len(self.anomalies)}{Style.RESET_ALL}\n")
    
    def info_alert(self, anomaly: Dict):
        """Display info alert"""
        print(f"{Fore.LIGHTBLUE_EX}ℹ️  {anomaly['description']}{Style.RESET_ALL}")
    
    def log_anomaly(self, anomaly: Dict):
        """Log anomaly to file"""
        try:
            log_path = os.path.expanduser("~/.aish_anomaly_log.json")
            logs = []
            
            if os.path.exists(log_path):
                with open(log_path, 'r') as f:
                    logs = json.load(f)
            
            logs.append(anomaly)
            
            # Keep only last 500 entries
            if len(logs) > 500:
                logs = logs[-500:]
            
            with open(log_path, 'w') as f:
                json.dump(logs, f, indent=2)
                
        except Exception:
            pass
    
    def start_monitoring(self):
        """Start monitoring in background thread"""
        if self.is_monitoring:
            print(f"{Fore.YELLOW}Monitoring already active{Style.RESET_ALL}")
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop monitoring"""
        if not self.is_monitoring:
            print(f"{Fore.YELLOW}Monitoring not active{Style.RESET_ALL}")
            return
        
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        print(f"{Fore.GREEN}🛡️ Monitoring stopped{Style.RESET_ALL}")
    
    def get_status(self) -> Dict:
        """Get current monitoring status"""
        return {
            'active': self.is_monitoring,
            'anomalies_detected': len(self.anomalies),
            'countries_known': len(self.known_countries),
            'connections_tracked': len(self.connection_history)
        }

# Global monitor instance
network_monitor = NetworkMonitor()

# -------------------------
# ONIST Commands
# -------------------------

def onist_monitor_start(args: List[str] = None):
    """Start real-time network anomaly monitoring"""
    if not HAS_PSUTIL:
        print(f"{Fore.RED}❌ psutil required for network monitoring{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Install with: pip install psutil{Style.RESET_ALL}")
        return
    
    network_monitor.start_monitoring()

def onist_monitor_stop(args: List[str] = None):
    """Stop network anomaly monitoring"""
    network_monitor.stop_monitoring()

def onist_monitor_status(args: List[str] = None):
    """Show monitoring status and statistics"""
    status = network_monitor.get_status()
    
    print(f"{Fore.CYAN}🛡️ Network Monitor Status{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*40}{Style.RESET_ALL}")
    
    status_color = Fore.GREEN if status['active'] else Fore.RED
    status_text = "ACTIVE" if status['active'] else "INACTIVE"
    print(f"Status: {status_color}{status_text}{Style.RESET_ALL}")
    print(f"Anomalies detected: {status['anomalies_detected']}")
    print(f"Known countries: {status['countries_known']}")
    print(f"Connections tracked: {status['connections_tracked']}")
    
    if status['active']:
        print(f"\n{Fore.YELLOW}💡 Monitoring every {MONITOR_INTERVAL} seconds{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Run 'onist alerts' to see recent anomalies{Style.RESET_ALL}")

def onist_alerts(args: List[str] = None):
    """Show recent anomaly alerts"""
    if not network_monitor.anomalies:
        print(f"{Fore.GREEN}✅ No anomalies detected yet{Style.RESET_ALL}")
        return
    
    print(f"{Fore.CYAN}🚨 Recent Anomalies (last 10){Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    
    recent = list(network_monitor.anomalies)[-10:]
    for i, anomaly in enumerate(recent, 1):
        severity_color = {
            'high': Fore.RED,
            'medium': Fore.YELLOW,
            'low': Fore.LIGHTBLUE_EX
        }.get(anomaly['severity'], Fore.WHITE)
        
        timestamp = datetime.fromtimestamp(anomaly['timestamp']).strftime('%m-%d %H:%M:%S')
        print(f"{i:2}. {severity_color}[{anomaly['severity'].upper()}]{Style.RESET_ALL} "
              f"{timestamp} - {anomaly['description']}")

def onist_investigate(args: List[str] = None):
    """Investigate specific anomaly by ID"""
    if not args:
        print(f"{Fore.YELLOW}Usage: onist investigate <anomaly_id>{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Use 'onist alerts' to see anomaly IDs{Style.RESET_ALL}")
        return
    
    try:
        anomaly_id = int(args[0])
        if 1 <= anomaly_id <= len(network_monitor.anomalies):
            anomaly = list(network_monitor.anomalies)[anomaly_id - 1]
            
            print(f"{Fore.CYAN}🔍 Anomaly Investigation #{anomaly_id}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
            
            for key, value in anomaly.items():
                if key == 'timestamp':
                    value = datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')
                print(f"{key.capitalize()}: {value}")
            
            # Additional investigation based on type
            if anomaly['type'] == 'new_country':
                print(f"\n{Fore.YELLOW}🌍 Geographic Analysis:{Style.RESET_ALL}")
                print(f"Known countries: {', '.join(sorted(network_monitor.known_countries))}")
            
            elif anomaly['type'] == 'port_scan':
                print(f"\n{Fore.YELLOW}🔌 Port Scan Analysis:{Style.RESET_ALL}")
                recent_scans = [a for a in network_monitor.anomalies 
                              if a['type'] == 'port_scan' and a['source_ip'] == anomaly['source_ip']]
                print(f"Total scans from this IP: {len(recent_scans)}")
                
        else:
            print(f"{Fore.RED}❌ Invalid anomaly ID: {anomaly_id}{Style.RESET_ALL}")
            print(f"Valid range: 1-{len(network_monitor.anomalies)}")
            
    except ValueError:
        print(f"{Fore.RED}❌ Invalid ID. Must be a number.{Style.RESET_ALL}")

def onist_baseline(args: List[str] = None):
    """Establish baseline network behavior"""
    if not HAS_PSUTIL:
        print(f"{Fore.RED}❌ psutil required{Style.RESET_ALL}")
        return
    
    print(f"{Fore.CYAN}📊 Establishing network baseline...{Style.RESET_ALL}")
    
    # Collect network stats for 30 seconds
    samples = []
    for i in range(6):  # 6 samples over 30 seconds
        net_io = psutil.net_io_counters()
        samples.append({
            'bytes_sent': net_io.bytes_sent,
            'bytes_recv': net_io.bytes_recv,
            'timestamp': time.time()
        })
        if i < 5:  # Don't sleep after last sample
            print(f"Sampling... {(i+1)*5}s", end='\r')
            time.sleep(5)
    
    # Calculate baseline
    if len(samples) >= 2:
        avg_send_rate = sum(s['bytes_sent'] for s in samples[1:]) / len(samples[1:])
        avg_recv_rate = sum(s['bytes_recv'] for s in samples[1:]) / len(samples[1:])
        
        network_monitor.baseline_traffic['send'] = avg_send_rate
        network_monitor.baseline_traffic['recv'] = avg_recv_rate
        
        print(f"\n{Fore.GREEN}✅ Baseline established:{Style.RESET_ALL}")
        print(f"Average send rate: {avg_send_rate/1024:.1f} KB/s")
        print(f"Average recv rate: {avg_recv_rate/1024:.1f} KB/s")

def onist_connections(args: List[str] = None):
    """Show current network connections"""
    connections = network_monitor.get_active_connections()
    
    if not connections:
        print(f"{Fore.YELLOW}No active connections found{Style.RESET_ALL}")
        return
    
    print(f"{Fore.CYAN}🌐 Active Network Connections{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{'Local':<22} {'Remote':<22} {'PID':<8} {'Country'}")
    print(f"{'-'*22} {'-'*22} {'-'*8} {'-'*15}")
    
    for conn in connections[:20]:  # Show first 20
        remote_ip = conn['remote'].split(':')[0]
        country = network_monitor.get_country_for_ip(remote_ip) or "Unknown"
        pid_str = str(conn.get('pid', 'N/A'))
        
        print(f"{conn['local']:<22} {conn['remote']:<22} {pid_str:<8} {country}")

def onist_config(args: List[str] = None):
    """Configure anomaly detection settings"""
    if not args:
        print(f"{Fore.CYAN}🔧 Current Configuration:{Style.RESET_ALL}")
        for key, value in ANOMALY_THRESHOLD.items():
            print(f"  {key}: {value}")
        print(f"\n{Fore.YELLOW}Usage: onist config <setting> <value>{Style.RESET_ALL}")
        return
    
    if len(args) >= 2:
        setting = args[0]
        try:
            if setting in ANOMALY_THRESHOLD:
                if isinstance(ANOMALY_THRESHOLD[setting], bool):
                    value = args[1].lower() in ['true', '1', 'yes', 'on']
                elif isinstance(ANOMALY_THRESHOLD[setting], int):
                    value = int(args[1])
                elif isinstance(ANOMALY_THRESHOLD[setting], float):
                    value = float(args[1])
                else:
                    value = args[1]
                
                ANOMALY_THRESHOLD[setting] = value
                print(f"{Fore.GREEN}✅ {setting} set to {value}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}❌ Unknown setting: {setting}{Style.RESET_ALL}")
        except ValueError:
            print(f"{Fore.RED}❌ Invalid value for {setting}{Style.RESET_ALL}")

# -------------------------
# Menu Functions
# -------------------------

def typewriter(text, delay=0.01, color=Fore.LIGHTWHITE_EX):
    for ch in text:
        sys.stdout.write(f"{color}{ch}")
        sys.stdout.flush()
        time.sleep(delay)
    print()

def print_colored_menu(options):
    for idx, opt in enumerate(options, 1):
        print(f"{Fore.LIGHTRED_EX}{idx}) {Fore.LIGHTWHITE_EX}{opt}")
    print(f"{Fore.LIGHTRED_EX}0) {Fore.LIGHTWHITE_EX}Back")

def loading_dots(message="Loading", duration=1.0):
    dots = ["   ", ".  ", ".. ", "..."]
    end_time = time.time() + duration
    idx = 0
    while time.time() < end_time:
        sys.stdout.write(f"\r{Fore.LIGHTGREEN_EX}{message}{dots[idx % len(dots)]}{Style.RESET_ALL}")
        sys.stdout.flush()
        time.sleep(0.3)
        idx += 1
    print("\r" + " "*50 + "\r", end="")

def anomaly_detection_menu():
    """Main menu for anomaly detection"""
    typewriter("Initializing Real-Time Anomaly Detection...", color=Fore.LIGHTCYAN_EX)
    loading_dots("Starting security engine", duration=1.5)
    
    while True:
        typewriter("\n=== 🛡️ Real-Time Anomaly Detection ===", color=Fore.LIGHTRED_EX)
        
        # Show current status
        status = network_monitor.get_status()
        status_indicator = f"{Fore.GREEN}🟢 ACTIVE" if status['active'] else f"{Fore.RED}🔴 INACTIVE"
        print(f"Status: {status_indicator}{Style.RESET_ALL}")
        
        options = [
            "Start Monitoring",
            "Stop Monitoring", 
            "View Alerts",
            "Investigate Anomaly",
            "Current Connections",
            "Establish Baseline",
            "Configure Settings",
            "Export Logs"
        ]
        print_colored_menu(options)
        
        choice = input(Fore.LIGHTCYAN_EX + "Select an option: " + Style.RESET_ALL).strip()
        
        if choice == "0":
            if network_monitor.is_monitoring:
                typewriter("Stopping monitor before exit...", color=Fore.YELLOW)
                network_monitor.stop_monitoring()
            break
            
        elif choice == "1":
            loading_dots("Starting monitor", 1.0)
            onist_monitor_start()
            
        elif choice == "2":
            loading_dots("Stopping monitor", 1.0)
            onist_monitor_stop()
            
        elif choice == "3":
            onist_alerts()
            
        elif choice == "4":
            investigate_id = input(f"{Fore.CYAN}Enter anomaly ID to investigate: {Style.RESET_ALL}").strip()
            if investigate_id:
                onist_investigate([investigate_id])
                
        elif choice == "5":
            loading_dots("Scanning connections", 1.0)
            onist_connections()
            
        elif choice == "6":
            onist_baseline()
            
        elif choice == "7":
            setting = input(f"{Fore.CYAN}Setting name (or empty to view all): {Style.RESET_ALL}").strip()
            if setting:
                value = input(f"{Fore.CYAN}New value: {Style.RESET_ALL}").strip()
                onist_config([setting, value])
            else:
                onist_config()
                
        elif choice == "8":
            export_anomaly_logs()
            
        else:
            typewriter("❌ Invalid option", color=Fore.LIGHTRED_EX)

def export_anomaly_logs():
    """Export anomaly logs to readable format"""
    try:
        log_path = os.path.expanduser("~/.aish_anomaly_log.json")
        if not os.path.exists(log_path):
            print(f"{Fore.YELLOW}No logs found yet{Style.RESET_ALL}")
            return
        
        with open(log_path, 'r') as f:
            logs = json.load(f)
        
        export_path = os.path.expanduser("~/aish_security_report.txt")
        with open(export_path, 'w') as f:
            f.write("AISH Security Anomaly Report\n")
            f.write("="*50 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total anomalies: {len(logs)}\n\n")
            
            for i, log in enumerate(logs, 1):
                timestamp = datetime.fromtimestamp(log['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"{i}. [{log['severity'].upper()}] {timestamp}\n")
                f.write(f"   Type: {log['type']}\n")
                f.write(f"   Description: {log['description']}\n")
                f.write("\n")
        
        print(f"{Fore.GREEN}✅ Report exported to: {export_path}{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"{Fore.RED}❌ Export failed: {e}{Style.RESET_ALL}")

# -------------------------
# Command Registry for Integration
# -------------------------
ONIST_COMMANDS = {
    "onist_monitor": onist_monitor_start,
    "onist_stop": onist_monitor_stop,
    "onist_status": onist_monitor_status,
    "onist_alerts": onist_alerts,
    "onist_investigate": onist_investigate,
    "onist_connections": onist_connections,
    "onist_baseline": onist_baseline,
    "onist_config": onist_config
}

# Main entry point for the menu
if __name__ == "__main__":
    anomaly_detection_menu()