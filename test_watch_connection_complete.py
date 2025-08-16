#!/usr/bin/env python3
"""
Complete Watch IMU Connection Test

This script tests the exact failure scenario and validates the fix.
Run this BEFORE and AFTER applying the watch-side fix.
"""

import requests
import json
import time
import sys
from datetime import datetime

def test_watch_endpoints(ip, port=8080):
    """Test all watch endpoints systematically."""
    print(f"🔍 Testing Watch at {ip}:{port}")
    print("=" * 50)
    
    results = {
        'ip': ip,
        'port': port,
        'timestamp': datetime.now().isoformat(),
        'tests': {}
    }
    
    # Test 1: Ping
    print("1. Testing /ping endpoint...")
    try:
        response = requests.get(f"http://{ip}:{port}/ping", timeout=3)
        if response.status_code == 200 and response.text.strip() == "pong":
            print("   ✅ Ping successful")
            results['tests']['ping'] = {'success': True, 'response': response.text}
        else:
            print(f"   ❌ Ping failed: {response.status_code} - {response.text}")
            results['tests']['ping'] = {'success': False, 'error': f"{response.status_code}: {response.text}"}
            return results
    except Exception as e:
        print(f"   ❌ Ping error: {e}")
        results['tests']['ping'] = {'success': False, 'error': str(e)}
        return results
    
    # Test 2: Status
    print("2. Testing /status endpoint...")
    try:
        response = requests.get(f"http://{ip}:{port}/status", timeout=5)
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            try:
                status = response.json()
                print(f"   ✅ Status JSON: {json.dumps(status, indent=2)}")
                results['tests']['status'] = {'success': True, 'data': status}
            except json.JSONDecodeError:
                print(f"   ⚠️  Status not JSON: {response.text}")
                results['tests']['status'] = {'success': False, 'error': 'Invalid JSON', 'raw': response.text}
        else:
            print(f"   ❌ Status failed: {response.status_code}")
            results['tests']['status'] = {'success': False, 'error': f"HTTP {response.status_code}"}
    except Exception as e:
        print(f"   ❌ Status error: {e}")
        results['tests']['status'] = {'success': False, 'error': str(e)}
    
    # Test 3: Start Recording
    print("3. Testing /start endpoint...")
    try:
        response = requests.get(f"http://{ip}:{port}/start", timeout=5)
        print(f"   Start Code: {response.status_code}")
        print(f"   Start Response: {response.text}")
        results['tests']['start'] = {
            'success': response.status_code == 200,
            'status_code': response.status_code,
            'response': response.text
        }
    except Exception as e:
        print(f"   ❌ Start error: {e}")
        results['tests']['start'] = {'success': False, 'error': str(e)}
    
    # Test 4: Wait and check recording status
    print("4. Recording for 3 seconds...")
    time.sleep(3)
    
    try:
        response = requests.get(f"http://{ip}:{port}/status", timeout=5)
        if response.status_code == 200:
            try:
                status = response.json()
                state = status.get('recording_state', 'unknown')
                samples = status.get('sample_count', 0)
                print(f"   📊 Recording State: {state}")
                print(f"   📊 Sample Count: {samples}")
                results['tests']['recording_status'] = {
                    'success': True,
                    'state': state,
                    'samples': samples
                }
            except json.JSONDecodeError:
                print(f"   ⚠️  Status not JSON during recording")
                results['tests']['recording_status'] = {'success': False, 'error': 'Invalid JSON'}
    except Exception as e:
        print(f"   ❌ Recording status error: {e}")
        results['tests']['recording_status'] = {'success': False, 'error': str(e)}
    
    # Test 5: Stop Recording
    print("5. Testing /stop endpoint...")
    try:
        response = requests.get(f"http://{ip}:{port}/stop", timeout=5)
        print(f"   Stop Code: {response.status_code}")
        print(f"   Stop Response: {response.text}")
        results['tests']['stop'] = {
            'success': response.status_code == 200,
            'status_code': response.status_code,
            'response': response.text
        }
    except Exception as e:
        print(f"   ❌ Stop error: {e}")
        results['tests']['stop'] = {'success': False, 'error': str(e)}
    
    # Test 6: CRITICAL - Data Endpoint (This is the failing one!)
    print("6. 🚨 CRITICAL TEST: /data endpoint...")
    time.sleep(1)  # Give it a moment to finalize
    
    try:
        response = requests.get(f"http://{ip}:{port}/data", timeout=10)
        print(f"   Data Code: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('content-type', 'unknown')}")
        print(f"   Content-Length: {len(response.content)} bytes")
        
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, list):
                    print(f"   ✅ SUCCESS: Got {len(data)} IMU samples!")
                    if data:
                        print(f"   📊 Sample data: {data[0]}")
                    results['tests']['data'] = {
                        'success': True,
                        'sample_count': len(data),
                        'sample_data': data[0] if data else None
                    }
                else:
                    print(f"   ✅ SUCCESS: Got data object: {type(data)}")
                    results['tests']['data'] = {'success': True, 'data': data}
            except json.JSONDecodeError:
                print(f"   ❌ PROBLEM: Data not valid JSON")
                print(f"   Raw data: {response.text[:200]}...")
                results['tests']['data'] = {
                    'success': False,
                    'error': 'Invalid JSON',
                    'raw_data': response.text[:200]
                }
        elif response.status_code == 404:
            print(f"   ❌ PROBLEM CONFIRMED: /data endpoint missing!")
            print(f"   This is why IMU folders are empty!")
            results['tests']['data'] = {
                'success': False,
                'error': 'Endpoint not found - THIS IS THE PROBLEM!',
                'status_code': 404
            }
        else:
            print(f"   ❌ PROBLEM: Data endpoint error {response.status_code}")
            print(f"   Response: {response.text}")
            results['tests']['data'] = {
                'success': False,
                'error': f"HTTP {response.status_code}",
                'response': response.text
            }
            
    except Exception as e:
        print(f"   ❌ PROBLEM: Data endpoint exception: {e}")
        results['tests']['data'] = {'success': False, 'error': str(e)}
    
    return results

def print_diagnosis(results):
    """Print diagnosis based on test results."""
    print("\n" + "🔍 DIAGNOSIS" + "=" * 40)
    
    tests = results['tests']
    
    # Check basic connectivity
    if not tests.get('ping', {}).get('success', False):
        print("❌ BASIC CONNECTIVITY FAILED")
        print("   - Watch is not reachable")
        print("   - Check IP address and network connection")
        return
    
    print("✅ Basic connectivity works")
    
    # Check recording functionality
    start_ok = tests.get('start', {}).get('success', False)
    stop_ok = tests.get('stop', {}).get('success', False)
    
    if start_ok and stop_ok:
        print("✅ Recording start/stop works")
        
        # Check if samples were collected
        recording_status = tests.get('recording_status', {})
        if recording_status.get('success') and recording_status.get('samples', 0) > 0:
            print(f"✅ IMU data collection works ({recording_status['samples']} samples)")
        else:
            print("⚠️  IMU data collection may have issues")
    else:
        print("❌ Recording start/stop has issues")
    
    # Check the critical data endpoint
    data_test = tests.get('data', {})
    if data_test.get('success', False):
        print("✅ DATA ENDPOINT WORKS - Problem is elsewhere!")
        sample_count = data_test.get('sample_count', 0)
        print(f"   Retrieved {sample_count} samples successfully")
    elif data_test.get('status_code') == 404:
        print("❌ DATA ENDPOINT MISSING - THIS IS THE ROOT CAUSE!")
        print("   The watch HTTP server doesn't have a /data endpoint")
        print("   This is why PC gets empty IMU folders")
        print("\n🔧 SOLUTION:")
        print("   1. Apply the fix in fix_watch_data_endpoint.kt")
        print("   2. Rebuild and reinstall the watch app")
        print("   3. Run this test again to verify the fix")
    else:
        print("❌ DATA ENDPOINT HAS ISSUES")
        print(f"   Error: {data_test.get('error', 'Unknown')}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_watch_connection_complete.py <watch_ip> [port]")
        print("Example: python test_watch_connection_complete.py 192.168.1.101")
        print("Example: python test_watch_connection_complete.py 192.168.1.101 8080")
        sys.exit(1)
    
    ip = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
    
    print("🔍 COMPLETE WATCH IMU CONNECTION TEST")
    print("=" * 60)
    print(f"Target: {ip}:{port}")
    print(f"Time: {datetime.now().isoformat()}")
    print()
    
    results = test_watch_endpoints(ip, port)
    print_diagnosis(results)
    
    # Save results
    filename = f"watch_test_{ip.replace('.', '_')}_{int(time.time())}.json"
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: {filename}")
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()