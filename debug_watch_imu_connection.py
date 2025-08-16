#!/usr/bin/env python3
"""
Watch IMU Connection Debugger

This tool systematically tests the watch IMU connection and data flow
to identify where the communication is breaking down.
"""

import requests
import json
import time
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WatchIMUDebugger:
    """Comprehensive debugger for Watch IMU connections."""
    
    def __init__(self, watch_ips: List[str]):
        self.watch_ips = watch_ips
        self.discovered_watches = {}
        self.test_results = {}
        
    def run_full_diagnostic(self) -> Dict:
        """Run complete diagnostic suite."""
        logger.info("🔍 Starting comprehensive Watch IMU diagnostic...")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'discovery': self.test_discovery(),
            'connectivity': self.test_connectivity(),
            'endpoints': self.test_all_endpoints(),
            'recording_flow': self.test_recording_flow(),
            'data_retrieval': self.test_data_retrieval(),
            'file_operations': self.test_file_operations()
        }
        
        self.print_diagnostic_summary(results)
        return results
    
    def test_discovery(self) -> Dict:
        """Test watch discovery across multiple ports."""
        logger.info("🔍 Testing watch discovery...")
        
        discovery_results = {}
        ports_to_try = [8080, 8081, 8082, 8083, 9090]
        
        for ip in self.watch_ips:
            logger.info(f"Testing IP: {ip}")
            ip_results = {
                'ip': ip,
                'reachable_ports': [],
                'ping_responses': {},
                'errors': []
            }
            
            for port in ports_to_try:
                try:
                    url = f"http://{ip}:{port}/ping"
                    logger.debug(f"Testing: {url}")
                    
                    response = requests.get(url, timeout=3.0)
                    
                    ip_results['ping_responses'][port] = {
                        'status_code': response.status_code,
                        'response_text': response.text.strip(),
                        'response_time': response.elapsed.total_seconds()
                    }
                    
                    if response.status_code == 200 and response.text.strip() == "pong":
                        ip_results['reachable_ports'].append(port)
                        self.discovered_watches[ip] = port
                        logger.info(f"✅ Found active watch at {ip}:{port}")
                    else:
                        logger.warning(f"⚠️  Unexpected response from {ip}:{port}: {response.status_code} - {response.text}")
                        
                except requests.RequestException as e:
                    ip_results['errors'].append(f"Port {port}: {str(e)}")
                    logger.debug(f"❌ Connection failed to {ip}:{port}: {e}")
            
            discovery_results[ip] = ip_results
            
            if not ip_results['reachable_ports']:
                logger.error(f"❌ No reachable ports found for {ip}")
            else:
                logger.info(f"✅ Found {len(ip_results['reachable_ports'])} reachable ports for {ip}")
        
        return discovery_results
    
    def test_connectivity(self) -> Dict:
        """Test basic connectivity to discovered watches."""
        logger.info("🔗 Testing basic connectivity...")
        
        connectivity_results = {}
        
        for ip, port in self.discovered_watches.items():
            logger.info(f"Testing connectivity to {ip}:{port}")
            
            conn_result = {
                'ip': ip,
                'port': port,
                'ping_success': False,
                'ping_time': None,
                'ping_error': None
            }
            
            try:
                start_time = time.time()
                url = f"http://{ip}:{port}/ping"
                response = requests.get(url, timeout=5.0)
                ping_time = time.time() - start_time
                
                if response.status_code == 200 and response.text.strip() == "pong":
                    conn_result['ping_success'] = True
                    conn_result['ping_time'] = ping_time
                    logger.info(f"✅ Ping successful to {ip}:{port} ({ping_time:.3f}s)")
                else:
                    conn_result['ping_error'] = f"Unexpected response: {response.status_code} - {response.text}"
                    logger.error(f"❌ Ping failed to {ip}:{port}: {conn_result['ping_error']}")
                    
            except requests.RequestException as e:
                conn_result['ping_error'] = str(e)
                logger.error(f"❌ Ping error to {ip}:{port}: {e}")
            
            connectivity_results[f"{ip}:{port}"] = conn_result
        
        return connectivity_results
    
    def test_all_endpoints(self) -> Dict:
        """Test all available endpoints on discovered watches."""
        logger.info("🔍 Testing all endpoints...")
        
        endpoints_to_test = ['ping', 'status', 'start', 'stop', 'data']
        endpoint_results = {}
        
        for ip, port in self.discovered_watches.items():
            logger.info(f"Testing endpoints on {ip}:{port}")
            
            watch_endpoints = {
                'ip': ip,
                'port': port,
                'endpoints': {}
            }
            
            for endpoint in endpoints_to_test:
                try:
                    url = f"http://{ip}:{port}/{endpoint}"
                    logger.debug(f"Testing endpoint: {url}")
                    
                    response = requests.get(url, timeout=5.0)
                    
                    endpoint_result = {
                        'status_code': response.status_code,
                        'response_text': response.text[:200],  # Truncate long responses
                        'response_time': response.elapsed.total_seconds(),
                        'content_type': response.headers.get('content-type', 'unknown')
                    }
                    
                    # Try to parse JSON if it looks like JSON
                    if response.headers.get('content-type', '').startswith('application/json'):
                        try:
                            endpoint_result['json_data'] = response.json()
                        except json.JSONDecodeError:
                            endpoint_result['json_parse_error'] = True
                    
                    watch_endpoints['endpoints'][endpoint] = endpoint_result
                    
                    if response.status_code == 200:
                        logger.info(f"✅ {endpoint}: {response.status_code}")
                    else:
                        logger.warning(f"⚠️  {endpoint}: {response.status_code} - {response.text[:50]}")
                        
                except requests.RequestException as e:
                    watch_endpoints['endpoints'][endpoint] = {
                        'error': str(e),
                        'status_code': None
                    }
                    logger.error(f"❌ {endpoint}: {e}")
            
            endpoint_results[f"{ip}:{port}"] = watch_endpoints
        
        return endpoint_results
    
    def test_recording_flow(self) -> Dict:
        """Test the complete recording flow."""
        logger.info("🎬 Testing recording flow...")
        
        recording_results = {}
        
        for ip, port in self.discovered_watches.items():
            logger.info(f"Testing recording flow on {ip}:{port}")
            
            flow_result = {
                'ip': ip,
                'port': port,
                'steps': {}
            }
            
            # Step 1: Check initial status
            try:
                url = f"http://{ip}:{port}/status"
                response = requests.get(url, timeout=5.0)
                
                if response.status_code == 200:
                    try:
                        status_data = response.json()
                        flow_result['steps']['initial_status'] = {
                            'success': True,
                            'data': status_data
                        }
                        logger.info(f"✅ Initial status: {status_data.get('recording_state', 'unknown')}")
                    except json.JSONDecodeError:
                        flow_result['steps']['initial_status'] = {
                            'success': False,
                            'error': 'JSON parse error',
                            'raw_response': response.text
                        }
                else:
                    flow_result['steps']['initial_status'] = {
                        'success': False,
                        'error': f"HTTP {response.status_code}: {response.text}"
                    }
            except requests.RequestException as e:
                flow_result['steps']['initial_status'] = {
                    'success': False,
                    'error': str(e)
                }
            
            # Step 2: Start recording
            try:
                url = f"http://{ip}:{port}/start"
                response = requests.get(url, timeout=5.0)
                
                flow_result['steps']['start_recording'] = {
                    'success': response.status_code == 200,
                    'status_code': response.status_code,
                    'response': response.text
                }
                
                if response.status_code == 200:
                    logger.info(f"✅ Start recording: {response.text}")
                else:
                    logger.error(f"❌ Start recording failed: {response.status_code} - {response.text}")
                    
            except requests.RequestException as e:
                flow_result['steps']['start_recording'] = {
                    'success': False,
                    'error': str(e)
                }
            
            # Step 3: Check recording status
            time.sleep(1.0)  # Give it a moment to start
            
            try:
                url = f"http://{ip}:{port}/status"
                response = requests.get(url, timeout=5.0)
                
                if response.status_code == 200:
                    try:
                        status_data = response.json()
                        flow_result['steps']['recording_status'] = {
                            'success': True,
                            'data': status_data
                        }
                        logger.info(f"✅ Recording status: {status_data.get('recording_state', 'unknown')}")
                    except json.JSONDecodeError:
                        flow_result['steps']['recording_status'] = {
                            'success': False,
                            'error': 'JSON parse error',
                            'raw_response': response.text
                        }
                else:
                    flow_result['steps']['recording_status'] = {
                        'success': False,
                        'error': f"HTTP {response.status_code}: {response.text}"
                    }
            except requests.RequestException as e:
                flow_result['steps']['recording_status'] = {
                    'success': False,
                    'error': str(e)
                }
            
            # Step 4: Record for a short time
            logger.info("Recording for 3 seconds...")
            time.sleep(3.0)
            
            # Step 5: Stop recording
            try:
                url = f"http://{ip}:{port}/stop"
                response = requests.get(url, timeout=5.0)
                
                flow_result['steps']['stop_recording'] = {
                    'success': response.status_code == 200,
                    'status_code': response.status_code,
                    'response': response.text
                }
                
                if response.status_code == 200:
                    logger.info(f"✅ Stop recording: {response.text}")
                else:
                    logger.error(f"❌ Stop recording failed: {response.status_code} - {response.text}")
                    
            except requests.RequestException as e:
                flow_result['steps']['stop_recording'] = {
                    'success': False,
                    'error': str(e)
                }
            
            # Step 6: Check final status
            time.sleep(1.0)  # Give it a moment to stop
            
            try:
                url = f"http://{ip}:{port}/status"
                response = requests.get(url, timeout=5.0)
                
                if response.status_code == 200:
                    try:
                        status_data = response.json()
                        flow_result['steps']['final_status'] = {
                            'success': True,
                            'data': status_data
                        }
                        logger.info(f"✅ Final status: {status_data.get('recording_state', 'unknown')}")
                    except json.JSONDecodeError:
                        flow_result['steps']['final_status'] = {
                            'success': False,
                            'error': 'JSON parse error',
                            'raw_response': response.text
                        }
                else:
                    flow_result['steps']['final_status'] = {
                        'success': False,
                        'error': f"HTTP {response.status_code}: {response.text}"
                    }
            except requests.RequestException as e:
                flow_result['steps']['final_status'] = {
                    'success': False,
                    'error': str(e)
                }
            
            recording_results[f"{ip}:{port}"] = flow_result
        
        return recording_results
    
    def test_data_retrieval(self) -> Dict:
        """Test data retrieval from watches."""
        logger.info("📥 Testing data retrieval...")
        
        data_results = {}
        
        for ip, port in self.discovered_watches.items():
            logger.info(f"Testing data retrieval from {ip}:{port}")
            
            data_result = {
                'ip': ip,
                'port': port,
                'data_available': False,
                'data_size': 0,
                'data_format': 'unknown',
                'sample_count': 0,
                'error': None
            }
            
            try:
                url = f"http://{ip}:{port}/data"
                logger.debug(f"Requesting data from: {url}")
                
                response = requests.get(url, timeout=10.0)  # Longer timeout for data
                
                data_result['status_code'] = response.status_code
                data_result['response_time'] = response.elapsed.total_seconds()
                
                if response.status_code == 200:
                    data_result['data_available'] = True
                    data_result['data_size'] = len(response.content)
                    
                    # Try to parse as JSON
                    try:
                        json_data = response.json()
                        data_result['data_format'] = 'json'
                        
                        if isinstance(json_data, list):
                            data_result['sample_count'] = len(json_data)
                            if json_data:
                                data_result['sample_data'] = json_data[0]  # First sample
                        elif isinstance(json_data, dict):
                            data_result['sample_count'] = json_data.get('sample_count', 0)
                            data_result['sample_data'] = json_data
                        
                        logger.info(f"✅ Retrieved {data_result['sample_count']} samples from {ip}:{port}")
                        
                    except json.JSONDecodeError:
                        data_result['data_format'] = 'text'
                        data_result['raw_data'] = response.text[:200]  # First 200 chars
                        logger.warning(f"⚠️  Data from {ip}:{port} is not valid JSON")
                        
                else:
                    data_result['error'] = f"HTTP {response.status_code}: {response.text}"
                    logger.error(f"❌ Data retrieval failed from {ip}:{port}: {data_result['error']}")
                    
            except requests.RequestException as e:
                data_result['error'] = str(e)
                logger.error(f"❌ Data retrieval error from {ip}:{port}: {e}")
            
            data_results[f"{ip}:{port}"] = data_result
        
        return data_results
    
    def test_file_operations(self) -> Dict:
        """Test file system operations for IMU data storage."""
        logger.info("📁 Testing file operations...")
        
        test_dir = "test_imu_debug"
        file_results = {
            'test_directory': test_dir,
            'directory_creation': False,
            'file_writing': False,
            'csv_writing': False,
            'cleanup': False,
            'errors': []
        }
        
        try:
            # Test directory creation
            os.makedirs(test_dir, exist_ok=True)
            file_results['directory_creation'] = os.path.exists(test_dir)
            logger.info(f"✅ Directory creation: {file_results['directory_creation']}")
            
            # Test basic file writing
            test_file = os.path.join(test_dir, "test.txt")
            with open(test_file, 'w') as f:
                f.write("Test data")
            file_results['file_writing'] = os.path.exists(test_file)
            logger.info(f"✅ File writing: {file_results['file_writing']}")
            
            # Test CSV writing
            import csv
            csv_file = os.path.join(test_dir, "test.csv")
            with open(csv_file, 'w', newline='') as csvfile:
                fieldnames = ['timestamp', 'accel_x', 'accel_y', 'accel_z', 'gyro_x', 'gyro_y', 'gyro_z']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow({
                    'timestamp': time.time(),
                    'accel_x': 1.0, 'accel_y': 2.0, 'accel_z': 3.0,
                    'gyro_x': 0.1, 'gyro_y': 0.2, 'gyro_z': 0.3
                })
            file_results['csv_writing'] = os.path.exists(csv_file)
            logger.info(f"✅ CSV writing: {file_results['csv_writing']}")
            
            # Cleanup
            import shutil
            shutil.rmtree(test_dir)
            file_results['cleanup'] = not os.path.exists(test_dir)
            logger.info(f"✅ Cleanup: {file_results['cleanup']}")
            
        except Exception as e:
            file_results['errors'].append(str(e))
            logger.error(f"❌ File operations error: {e}")
        
        return file_results
    
    def print_diagnostic_summary(self, results: Dict):
        """Print a comprehensive diagnostic summary."""
        print("\n" + "="*80)
        print("🔍 WATCH IMU DIAGNOSTIC SUMMARY")
        print("="*80)
        
        # Discovery Summary
        discovery = results['discovery']
        total_ips = len(discovery)
        reachable_ips = sum(1 for ip_data in discovery.values() if ip_data['reachable_ports'])
        
        print(f"\n📡 DISCOVERY RESULTS:")
        print(f"   Total IPs tested: {total_ips}")
        print(f"   Reachable IPs: {reachable_ips}")
        
        for ip, ip_data in discovery.items():
            if ip_data['reachable_ports']:
                print(f"   ✅ {ip}: Ports {ip_data['reachable_ports']}")
            else:
                print(f"   ❌ {ip}: No reachable ports")
        
        # Connectivity Summary
        connectivity = results['connectivity']
        successful_pings = sum(1 for conn in connectivity.values() if conn['ping_success'])
        
        print(f"\n🔗 CONNECTIVITY RESULTS:")
        print(f"   Successful pings: {successful_pings}/{len(connectivity)}")
        
        for watch_id, conn in connectivity.items():
            if conn['ping_success']:
                print(f"   ✅ {watch_id}: {conn['ping_time']:.3f}s")
            else:
                print(f"   ❌ {watch_id}: {conn['ping_error']}")
        
        # Endpoints Summary
        endpoints = results['endpoints']
        print(f"\n🔍 ENDPOINT TESTING:")
        
        for watch_id, watch_data in endpoints.items():
            print(f"   {watch_id}:")
            for endpoint, endpoint_data in watch_data['endpoints'].items():
                if 'error' in endpoint_data:
                    print(f"     ❌ {endpoint}: {endpoint_data['error']}")
                elif endpoint_data['status_code'] == 200:
                    print(f"     ✅ {endpoint}: OK")
                else:
                    print(f"     ⚠️  {endpoint}: HTTP {endpoint_data['status_code']}")
        
        # Recording Flow Summary
        recording = results['recording_flow']
        print(f"\n🎬 RECORDING FLOW:")
        
        for watch_id, flow_data in recording.items():
            print(f"   {watch_id}:")
            for step, step_data in flow_data['steps'].items():
                if step_data.get('success', False):
                    print(f"     ✅ {step}")
                else:
                    error = step_data.get('error', 'Unknown error')
                    print(f"     ❌ {step}: {error}")
        
        # Data Retrieval Summary
        data_retrieval = results['data_retrieval']
        print(f"\n📥 DATA RETRIEVAL:")
        
        for watch_id, data_result in data_retrieval.items():
            if data_result['data_available']:
                print(f"   ✅ {watch_id}: {data_result['sample_count']} samples ({data_result['data_size']} bytes)")
            else:
                error = data_result.get('error', 'No data available')
                print(f"   ❌ {watch_id}: {error}")
        
        # File Operations Summary
        file_ops = results['file_operations']
        print(f"\n📁 FILE OPERATIONS:")
        
        operations = ['directory_creation', 'file_writing', 'csv_writing', 'cleanup']
        for op in operations:
            status = "✅" if file_ops[op] else "❌"
            print(f"   {status} {op.replace('_', ' ').title()}")
        
        if file_ops['errors']:
            print(f"   Errors: {', '.join(file_ops['errors'])}")
        
        print("\n" + "="*80)


def main():
    """Main diagnostic function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Debug Watch IMU connections")
    parser.add_argument('--watch-ips', nargs='+', default=['192.168.1.101', '192.168.1.102'],
                       help='Watch IP addresses to test')
    parser.add_argument('--output-file', type=str, default=None,
                       help='Save results to JSON file')
    
    args = parser.parse_args()
    
    debugger = WatchIMUDebugger(args.watch_ips)
    results = debugger.run_full_diagnostic()
    
    if args.output_file:
        with open(args.output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n💾 Results saved to: {args.output_file}")


if __name__ == "__main__":
    main()