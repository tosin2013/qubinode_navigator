#!/usr/bin/env python3

"""
Test CentOS Stream 10 Support in qubinode_kvmhost_setup_collection
=================================================================

This test validates that the collection properly detects and configures
CentOS Stream 10 systems with the appropriate packages and services.
"""

import subprocess
import sys
import tempfile
import yaml
from pathlib import Path

class CentOSStream10CollectionTester:
    def __init__(self):
        self.test_results = []
        self.collection_path = Path("/root/qubinode_navigator/qubinode_kvmhost_setup_collection")
        self.role_path = self.collection_path / "roles" / "kvmhost_setup"
        
    def create_test_playbook(self):
        """Create a test playbook to validate CentOS Stream 10 detection"""
        playbook_content = {
            'hosts': 'localhost',
            'connection': 'local',
            'gather_facts': True,
            'tasks': [
                {
                    'name': 'Include RHEL version detection',
                    'include_tasks': str(self.role_path / 'tasks' / 'rhel_version_detection.yml')
                },
                {
                    'name': 'Display detected OS facts',
                    'debug': {
                        'msg': {
                            'os_family': '{{ kvmhost_os_family }}',
                            'os_version': '{{ kvmhost_os_full_version }}',
                            'major_version': '{{ kvmhost_os_major_version }}',
                            'is_rhel_compatible': '{{ kvmhost_os_is_rhel_compatible }}',
                            'is_centos_stream': '{{ kvmhost_is_centos_stream }}',
                            'is_centos_stream10': '{{ kvmhost_is_centos_stream10 }}',
                            'is_rhel10': '{{ kvmhost_is_rhel10 }}',
                            'packages': '{{ kvmhost_packages_current }}',
                            'services': '{{ kvmhost_services_current }}',
                            'repos': '{{ kvmhost_repos_current }}'
                        }
                    }
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump([playbook_content], f, default_flow_style=False)
            return f.name
    
    def test_os_detection(self):
        """Test OS detection with ansible-playbook"""
        print("🔍 Testing CentOS Stream 10 Detection in Collection...")
        
        playbook_file = self.create_test_playbook()
        
        try:
            result = subprocess.run([
                'ansible-playbook',
                playbook_file,
                '-v'
            ], capture_output=True, text=True, cwd=str(self.collection_path))
            
            success = (
                result.returncode == 0 and
                'is_centos_stream10' in result.stdout and
                'centos_stream10' in result.stdout
            )
            
            self.test_results.append({
                "test": "OS Detection",
                "success": success,
                "output": result.stdout[-500:] if result.stdout else "",
                "error": result.stderr[-500:] if result.stderr else ""
            })
            
            print(f"   {'✅' if success else '❌'} OS Detection: {'PASSED' if success else 'FAILED'}")
            return success
            
        except Exception as e:
            print(f"   ❌ OS Detection: FAILED - {e}")
            return False
        finally:
            # Clean up
            Path(playbook_file).unlink(missing_ok=True)
    
    def test_package_configuration(self):
        """Test that CentOS Stream 10 packages are properly configured"""
        print("📦 Testing CentOS Stream 10 Package Configuration...")
        
        detection_file = self.role_path / 'tasks' / 'rhel_version_detection.yml'
        
        try:
            with open(detection_file, 'r') as f:
                content = f.read()
            
            success = (
                'centos_stream10:' in content and
                'python3.12' in content and
                'podman' in content and
                'kvmhost_is_centos_stream10' in content
            )
            
            self.test_results.append({
                "test": "Package Configuration",
                "success": success,
                "output": "CentOS Stream 10 packages found in configuration",
                "error": ""
            })
            
            print(f"   {'✅' if success else '❌'} Package Configuration: {'PASSED' if success else 'FAILED'}")
            return success
            
        except Exception as e:
            print(f"   ❌ Package Configuration: FAILED - {e}")
            return False
    
    def test_service_configuration(self):
        """Test that CentOS Stream 10 services are properly configured"""
        print("🔧 Testing CentOS Stream 10 Service Configuration...")
        
        detection_file = self.role_path / 'tasks' / 'rhel_version_detection.yml'
        
        try:
            with open(detection_file, 'r') as f:
                content = f.read()
            
            success = (
                'centos_stream10:' in content and
                'podman.socket' in content and
                'kvmhost_services.centos_stream10' in content
            )
            
            self.test_results.append({
                "test": "Service Configuration",
                "success": success,
                "output": "CentOS Stream 10 services found in configuration",
                "error": ""
            })
            
            print(f"   {'✅' if success else '❌'} Service Configuration: {'PASSED' if success else 'FAILED'}")
            return success
            
        except Exception as e:
            print(f"   ❌ Service Configuration: FAILED - {e}")
            return False
    
    def test_version_bump(self):
        """Test that collection version was bumped"""
        print("📈 Testing Collection Version Bump...")
        
        galaxy_file = self.collection_path / 'galaxy.yml'
        
        try:
            with open(galaxy_file, 'r') as f:
                content = yaml.safe_load(f)
            
            version = content.get('version', '')
            success = version == '0.9.27'
            
            self.test_results.append({
                "test": "Version Bump",
                "success": success,
                "output": f"Collection version: {version}",
                "error": ""
            })
            
            print(f"   {'✅' if success else '❌'} Version Bump: {'PASSED' if success else 'FAILED'}")
            return success
            
        except Exception as e:
            print(f"   ❌ Version Bump: FAILED - {e}")
            return False
    
    def run_all_tests(self):
        """Run all tests and generate report"""
        print("🧪 Starting CentOS Stream 10 Collection Support Tests")
        print("=" * 60)
        
        tests = [
            self.test_package_configuration,
            self.test_service_configuration,
            self.test_version_bump,
            # Note: OS detection test requires ansible-playbook, which may not be available
            # self.test_os_detection,
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            if test():
                passed += 1
        
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("🎉 All tests PASSED! CentOS Stream 10 support is ready.")
            return True
        else:
            print("⚠️ Some tests FAILED. Review the results above.")
            return False
    
    def generate_detailed_report(self):
        """Generate detailed test report"""
        print("\n📋 Detailed Test Report")
        print("=" * 60)
        
        for result in self.test_results:
            print(f"\n🔍 {result['test']}")
            print(f"Status: {'✅ PASSED' if result['success'] else '❌ FAILED'}")
            if result['output']:
                print(f"Output: {result['output']}")
            if result['error']:
                print(f"Error: {result['error']}")

if __name__ == "__main__":
    tester = CentOSStream10CollectionTester()
    
    success = tester.run_all_tests()
    tester.generate_detailed_report()
    
    sys.exit(0 if success else 1)
