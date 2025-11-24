#!/usr/bin/env python3
"""
RHEL 10/CentOS Stream 10 Compatibility Checker

Validates system compatibility with RHEL 10/CentOS Stream 10 requirements
as identified in ADR-0026 and the PRD analysis.
"""

import subprocess
import sys
import platform
from typing import Dict, List, Tuple, Any


class RHEL10CompatibilityChecker:
    """Check system compatibility with RHEL 10/CentOS Stream 10"""
    
    def __init__(self):
        self.results = {}
        
    def check_all(self) -> Dict[str, Any]:
        """Run all compatibility checks"""
        print("🔍 RHEL 10/CentOS Stream 10 Compatibility Check")
        print("=" * 60)
        
        self.check_os_version()
        self.check_microarchitecture()
        self.check_python_version()
        self.check_kernel_version()
        self.check_removed_packages()
        
        self.print_summary()
        return self.results
        
    def check_os_version(self):
        """Check current OS version"""
        print("\n📋 Operating System Check")
        print("-" * 30)
        
        try:
            with open('/etc/redhat-release', 'r') as f:
                os_release = f.read().strip()
                
            print(f"Current OS: {os_release}")
            
            # Check if it's CentOS Stream 10 or RHEL 10
            is_compatible = False
            if 'CentOS Stream release 10' in os_release:
                is_compatible = True
                print("✅ CentOS Stream 10 detected - Compatible!")
            elif 'Red Hat Enterprise Linux release 10' in os_release:
                is_compatible = True
                print("✅ RHEL 10 detected - Compatible!")
            else:
                print("⚠️  Not RHEL 10 or CentOS Stream 10")
                
            self.results['os_compatible'] = is_compatible
            self.results['os_version'] = os_release
            
        except FileNotFoundError:
            print("❌ Could not determine OS version")
            self.results['os_compatible'] = False
            
    def check_microarchitecture(self):
        """Check x86_64-v3 microarchitecture compatibility"""
        print("\n🏗️  Microarchitecture Check (x86_64-v3)")
        print("-" * 40)
        
        required_flags = [
            'avx', 'avx2', 'bmi1', 'bmi2', 'f16c', 
            'fma', 'lzcnt', 'movbe', 'xsave'
        ]
        
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
                
            # Find CPU flags
            flags_line = None
            for line in cpuinfo.split('\n'):
                if line.startswith('flags'):
                    flags_line = line
                    break
                    
            if not flags_line:
                print("❌ Could not read CPU flags")
                self.results['microarch_compatible'] = False
                return
                
            cpu_flags = flags_line.lower().split()
            missing_flags = [flag for flag in required_flags if flag not in cpu_flags]
            
            print(f"Required x86_64-v3 flags: {', '.join(required_flags)}")
            
            if not missing_flags:
                print("✅ All x86_64-v3 CPU flags present - Compatible!")
                self.results['microarch_compatible'] = True
            else:
                print(f"❌ Missing CPU flags: {', '.join(missing_flags)}")
                print("⚠️  This system does NOT meet x86_64-v3 requirements")
                print("   RHEL 10/CentOS 10 will NOT run on this hardware")
                self.results['microarch_compatible'] = False
                
            self.results['missing_cpu_flags'] = missing_flags
            
        except Exception as e:
            print(f"❌ Error checking microarchitecture: {e}")
            self.results['microarch_compatible'] = False
            
    def check_python_version(self):
        """Check Python version (should be 3.12+ for RHEL 10)"""
        print("\n🐍 Python Version Check")
        print("-" * 25)
        
        try:
            result = subprocess.run(
                ['python3', '--version'],
                capture_output=True, text=True, check=True
            )
            version_str = result.stdout.strip()
            print(f"Current Python: {version_str}")
            
            # Parse version
            version_parts = version_str.split()[1].split('.')
            major, minor = int(version_parts[0]), int(version_parts[1])
            
            if (major, minor) >= (3, 12):
                print("✅ Python 3.12+ detected - Compatible!")
                self.results['python_compatible'] = True
            else:
                print("⚠️  Python 3.12+ recommended for RHEL 10")
                self.results['python_compatible'] = False
                
            self.results['python_version'] = (major, minor)
            
        except Exception as e:
            print(f"❌ Error checking Python version: {e}")
            self.results['python_compatible'] = False
            
    def check_kernel_version(self):
        """Check kernel version (should be 6.x+ for RHEL 10)"""
        print("\n🔧 Kernel Version Check")
        print("-" * 25)
        
        try:
            kernel_version = platform.release()
            print(f"Current Kernel: {kernel_version}")
            
            # Parse version
            version_parts = kernel_version.split('.')
            major = int(version_parts[0])
            
            if major >= 6:
                print("✅ Kernel 6.x+ detected - Compatible!")
                self.results['kernel_compatible'] = True
            else:
                print("⚠️  Kernel 6.x+ expected for RHEL 10")
                self.results['kernel_compatible'] = False
                
            self.results['kernel_version'] = kernel_version
            
        except Exception as e:
            print(f"❌ Error checking kernel version: {e}")
            self.results['kernel_compatible'] = False
            
    def check_removed_packages(self):
        """Check for packages removed in RHEL 10"""
        print("\n📦 Removed Packages Check")
        print("-" * 28)
        
        removed_packages = [
            'xorg-x11-server-Xorg',  # Xorg server
            'libreoffice-core',      # LibreOffice
            'gimp',                  # GIMP
            'redis',                 # Redis
            'oscap-anaconda-addon'   # OpenSCAP Anaconda addon
        ]
        
        print("Packages removed in RHEL 10/CentOS Stream 10:")
        for package in removed_packages:
            print(f"  ❌ {package}")
            
        print("\n💡 Note: These packages are no longer available in RHEL 10")
        print("   Update your deployment scripts to use alternatives")
        
        self.results['removed_packages'] = removed_packages
        
    def print_summary(self):
        """Print compatibility summary"""
        print("\n" + "=" * 60)
        print("🎯 COMPATIBILITY SUMMARY")
        print("=" * 60)
        
        checks = [
            ('OS Version', self.results.get('os_compatible', False)),
            ('x86_64-v3 Architecture', self.results.get('microarch_compatible', False)),
            ('Python 3.12+', self.results.get('python_compatible', False)),
            ('Kernel 6.x+', self.results.get('kernel_compatible', False))
        ]
        
        all_compatible = True
        for check_name, compatible in checks:
            status = "✅ PASS" if compatible else "❌ FAIL"
            print(f"{check_name:.<25} {status}")
            if not compatible:
                all_compatible = False
                
        print("-" * 60)
        
        if all_compatible:
            print("🎉 SYSTEM IS COMPATIBLE with RHEL 10/CentOS Stream 10!")
            print("   You can proceed with Qubinode Navigator deployment.")
        else:
            print("⚠️  SYSTEM HAS COMPATIBILITY ISSUES")
            print("   Some features may not work correctly.")
            
            # Specific recommendations
            if not self.results.get('microarch_compatible', False):
                print("\n🚨 CRITICAL: x86_64-v3 microarchitecture required!")
                print("   This system cannot run RHEL 10/CentOS Stream 10.")
                print("   Consider upgrading hardware or using RHEL 9 instead.")
                
        self.results['overall_compatible'] = all_compatible


def main():
    """Main entry point"""
    checker = RHEL10CompatibilityChecker()
    results = checker.check_all()
    
    # Exit with appropriate code
    if results.get('overall_compatible', False):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
