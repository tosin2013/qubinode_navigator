"""
Qubinode Navigator Automated Update Detection and Management System

This module provides comprehensive update detection, validation, and management
for OS packages, software components, and Ansible collections.

Based on ADR-0030: Software and OS Update Strategy
"""

import asyncio
import json
import logging
import subprocess
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import requests
import yaml
from packaging import version
import hashlib


@dataclass
class UpdateInfo:
    """Information about an available update"""
    component_type: str  # os_package, software, collection, container
    component_name: str
    current_version: str
    available_version: str
    severity: str  # critical, security, important, moderate, low
    description: str
    release_date: str
    changelog_url: Optional[str] = None
    security_advisories: List[str] = None
    compatibility_status: str = "unknown"  # compatible, incompatible, needs_testing
    update_size: Optional[int] = None  # bytes
    dependencies: List[str] = None
    
    def __post_init__(self):
        """Initialize default values"""
        if self.security_advisories is None:
            self.security_advisories = []
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class UpdateBatch:
    """A batch of related updates"""
    batch_id: str
    batch_type: str  # security, feature, maintenance
    updates: List[UpdateInfo]
    total_size: int
    estimated_duration: str
    risk_level: str  # low, medium, high, critical
    requires_reboot: bool
    rollback_plan: str
    created_at: datetime
    
    def __post_init__(self):
        """Calculate batch metrics"""
        if not hasattr(self, 'total_size') or self.total_size == 0:
            self.total_size = sum(u.update_size or 0 for u in self.updates)


@dataclass
class CompatibilityMatrix:
    """Compatibility information for components"""
    component_name: str
    supported_versions: Dict[str, List[str]]  # os_version -> [compatible_versions]
    known_issues: List[Dict[str, Any]]
    test_results: Dict[str, str]  # version -> test_status
    last_updated: datetime


class UpdateDetector:
    """
    Automated Update Detection System
    
    Provides comprehensive update detection for OS packages, software,
    and Ansible collections with AI-powered compatibility analysis.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.check_interval = self.config.get('check_interval', 3600)  # 1 hour
        self.ai_assistant_url = self.config.get('ai_assistant_url', 'http://localhost:8080')
        self.cache_directory = Path(self.config.get('cache_directory', '/tmp/update_cache'))
        self.compatibility_file = self.config.get('compatibility_file', 'config/compatibility_matrix.yml')
        self.enable_ai_compatibility = self.config.get('enable_ai_compatibility', True)
        
        # State
        self.last_check_time: Optional[datetime] = None
        self.available_updates: List[UpdateInfo] = []
        self.compatibility_matrix: Dict[str, CompatibilityMatrix] = {}
        self.update_history: List[Dict[str, Any]] = []
        
        # Ensure cache directory exists
        self.cache_directory.mkdir(parents=True, exist_ok=True)
        
        # Load compatibility matrix
        self._load_compatibility_matrix()
    
    def _load_compatibility_matrix(self):
        """Load compatibility matrix from configuration"""
        try:
            matrix_file = Path(self.compatibility_file)
            if matrix_file.exists():
                with open(matrix_file, 'r') as f:
                    matrix_data = yaml.safe_load(f)
                
                for component, data in matrix_data.items():
                    self.compatibility_matrix[component] = CompatibilityMatrix(
                        component_name=component,
                        supported_versions=data.get('supported_versions', {}),
                        known_issues=data.get('known_issues', []),
                        test_results=data.get('test_results', {}),
                        last_updated=datetime.fromisoformat(data.get('last_updated', datetime.now().isoformat()))
                    )
                    
                self.logger.info(f"Loaded compatibility matrix for {len(self.compatibility_matrix)} components")
            else:
                self.logger.warning(f"Compatibility matrix file not found: {matrix_file}")
                
        except Exception as e:
            self.logger.error(f"Failed to load compatibility matrix: {e}")
    
    async def detect_os_updates(self) -> List[UpdateInfo]:
        """Detect available OS package updates"""
        updates = []
        
        try:
            # Detect OS type
            os_info = await self._get_os_info()
            
            if os_info['id'] in ['rhel', 'centos', 'rocky', 'almalinux']:
                updates.extend(await self._detect_rpm_updates())
            elif os_info['id'] in ['ubuntu', 'debian']:
                updates.extend(await self._detect_apt_updates())
            else:
                self.logger.warning(f"Unsupported OS for update detection: {os_info['id']}")
            
            self.logger.info(f"Detected {len(updates)} OS package updates")
            return updates
            
        except Exception as e:
            self.logger.error(f"Failed to detect OS updates: {e}")
            return []
    
    async def _get_os_info(self) -> Dict[str, str]:
        """Get OS information"""
        try:
            result = subprocess.run(['cat', '/etc/os-release'], capture_output=True, text=True)
            if result.returncode == 0:
                os_info = {}
                for line in result.stdout.strip().split('\n'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        os_info[key.lower()] = value.strip('"')
                return os_info
            else:
                return {'id': 'unknown', 'version_id': 'unknown'}
        except Exception as e:
            self.logger.error(f"Failed to get OS info: {e}")
            return {'id': 'unknown', 'version_id': 'unknown'}
    
    async def _detect_rpm_updates(self) -> List[UpdateInfo]:
        """Detect RPM package updates"""
        updates = []
        
        try:
            # Check for available updates using dnf/yum
            result = subprocess.run(
                ['dnf', 'check-update', '--quiet'],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # dnf check-update returns 100 if updates are available
            if result.returncode == 100:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line and not line.startswith('Last metadata'):
                        parts = line.split()
                        if len(parts) >= 2:
                            package_name = parts[0].split('.')[0]  # Remove architecture
                            available_version = parts[1]
                            
                            # Get current version
                            current_version = await self._get_rpm_current_version(package_name)
                            
                            # Determine severity
                            severity = await self._determine_update_severity(package_name, available_version)
                            
                            update = UpdateInfo(
                                component_type='os_package',
                                component_name=package_name,
                                current_version=current_version,
                                available_version=available_version,
                                severity=severity,
                                description=f"RPM package update for {package_name}",
                                release_date=datetime.now().isoformat()
                            )
                            
                            updates.append(update)
            
            return updates
            
        except subprocess.TimeoutExpired:
            self.logger.error("RPM update check timed out")
            return []
        except Exception as e:
            self.logger.error(f"Failed to detect RPM updates: {e}")
            return []
    
    async def _detect_apt_updates(self) -> List[UpdateInfo]:
        """Detect APT package updates"""
        updates = []
        
        try:
            # Update package list
            subprocess.run(['apt', 'update'], capture_output=True, timeout=300)
            
            # Check for upgradeable packages
            result = subprocess.run(
                ['apt', 'list', '--upgradable'],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                for line in lines:
                    if '/' in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            package_name = parts[0].split('/')[0]
                            available_version = parts[1]
                            
                            # Get current version
                            current_version = await self._get_apt_current_version(package_name)
                            
                            # Determine severity
                            severity = await self._determine_update_severity(package_name, available_version)
                            
                            update = UpdateInfo(
                                component_type='os_package',
                                component_name=package_name,
                                current_version=current_version,
                                available_version=available_version,
                                severity=severity,
                                description=f"APT package update for {package_name}",
                                release_date=datetime.now().isoformat()
                            )
                            
                            updates.append(update)
            
            return updates
            
        except subprocess.TimeoutExpired:
            self.logger.error("APT update check timed out")
            return []
        except Exception as e:
            self.logger.error(f"Failed to detect APT updates: {e}")
            return []
    
    async def _get_rpm_current_version(self, package_name: str) -> str:
        """Get current version of RPM package"""
        try:
            result = subprocess.run(
                ['rpm', '-q', '--queryformat', '%{VERSION}-%{RELEASE}', package_name],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return "not_installed"
        except Exception:
            return "unknown"
    
    async def _get_apt_current_version(self, package_name: str) -> str:
        """Get current version of APT package"""
        try:
            result = subprocess.run(
                ['dpkg-query', '-W', '-f=${Version}', package_name],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return "not_installed"
        except Exception:
            return "unknown"
    
    async def detect_software_updates(self) -> List[UpdateInfo]:
        """Detect updates for installed software components"""
        updates = []
        
        # Check common software components
        software_checks = [
            ('podman', self._check_podman_updates),
            ('ansible', self._check_ansible_updates),
            ('python', self._check_python_updates),
            ('git', self._check_git_updates),
            ('docker', self._check_docker_updates),
        ]
        
        for software, check_func in software_checks:
            try:
                software_updates = await check_func()
                updates.extend(software_updates)
            except Exception as e:
                self.logger.error(f"Failed to check {software} updates: {e}")
        
        self.logger.info(f"Detected {len(updates)} software updates")
        return updates
    
    async def _check_podman_updates(self) -> List[UpdateInfo]:
        """Check for Podman updates"""
        try:
            # Get current version
            result = subprocess.run(['podman', '--version'], capture_output=True, text=True)
            if result.returncode != 0:
                return []
            
            current_version = result.stdout.split()[-1]
            
            # Check latest version from GitHub API
            latest_version = await self._get_github_latest_release('containers/podman')
            
            if latest_version and version.parse(latest_version) > version.parse(current_version):
                return [UpdateInfo(
                    component_type='software',
                    component_name='podman',
                    current_version=current_version,
                    available_version=latest_version,
                    severity='moderate',
                    description='Container management tool update',
                    release_date=datetime.now().isoformat(),
                    changelog_url=f'https://github.com/containers/podman/releases/tag/v{latest_version}'
                )]
            
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to check Podman updates: {e}")
            return []
    
    async def _check_ansible_updates(self) -> List[UpdateInfo]:
        """Check for Ansible updates"""
        try:
            # Get current version
            result = subprocess.run(['ansible', '--version'], capture_output=True, text=True)
            if result.returncode != 0:
                return []
            
            # Parse version more carefully - ansible [core 2.16.14]
            version_line = result.stdout.split('\n')[0]
            if '[core' in version_line:
                # Extract version from [core X.Y.Z] format
                current_version = version_line.split('[core')[1].split(']')[0].strip()
            else:
                # Fallback to last word
                current_version = version_line.split()[-1].strip('[]')
            
            # Check PyPI for latest version - use ansible-core instead of ansible
            latest_version = await self._get_pypi_latest_version('ansible-core')
            
            if latest_version and version.parse(latest_version) > version.parse(current_version):
                return [UpdateInfo(
                    component_type='software',
                    component_name='ansible',
                    current_version=current_version,
                    available_version=latest_version,
                    severity='important',
                    description='Automation platform update',
                    release_date=datetime.now().isoformat(),
                    changelog_url=f'https://pypi.org/project/ansible-core/{latest_version}/'
                )]
            
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to check Ansible updates: {e}")
            return []
    
    async def _check_python_updates(self) -> List[UpdateInfo]:
        """Check for Python updates"""
        try:
            # Get current version
            result = subprocess.run(['python3', '--version'], capture_output=True, text=True)
            if result.returncode != 0:
                return []
            
            current_version = result.stdout.split()[-1]
            
            # For Python, we mainly care about security updates within the same minor version
            # Check for patch updates (e.g., 3.12.0 -> 3.12.1)
            major_minor = '.'.join(current_version.split('.')[:2])
            
            # This would need to be enhanced with actual Python release checking
            # For now, we'll return empty as Python updates are typically handled by OS packages
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to check Python updates: {e}")
            return []
    
    async def _check_git_updates(self) -> List[UpdateInfo]:
        """Check for Git updates"""
        try:
            # Get current version
            result = subprocess.run(['git', '--version'], capture_output=True, text=True)
            if result.returncode != 0:
                return []
            
            current_version = result.stdout.split()[-1]
            
            # Check latest version from GitHub API
            latest_version = await self._get_github_latest_release('git/git')
            
            if latest_version and version.parse(latest_version.lstrip('v')) > version.parse(current_version):
                return [UpdateInfo(
                    component_type='software',
                    component_name='git',
                    current_version=current_version,
                    available_version=latest_version.lstrip('v'),
                    severity='low',
                    description='Version control system update',
                    release_date=datetime.now().isoformat(),
                    changelog_url=f'https://github.com/git/git/releases/tag/{latest_version}'
                )]
            
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to check Git updates: {e}")
            return []
    
    async def _check_docker_updates(self) -> List[UpdateInfo]:
        """Check for Docker updates"""
        try:
            # Get current version
            result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
            if result.returncode != 0:
                return []  # Docker not installed
            
            current_version = result.stdout.split()[2].rstrip(',')
            
            # Check latest version from GitHub API
            latest_version = await self._get_github_latest_release('docker/cli')
            
            if latest_version and version.parse(latest_version.lstrip('v')) > version.parse(current_version):
                return [UpdateInfo(
                    component_type='software',
                    component_name='docker',
                    current_version=current_version,
                    available_version=latest_version.lstrip('v'),
                    severity='moderate',
                    description='Container platform update',
                    release_date=datetime.now().isoformat(),
                    changelog_url=f'https://github.com/docker/cli/releases/tag/{latest_version}'
                )]
            
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to check Docker updates: {e}")
            return []
    
    async def detect_collection_updates(self) -> List[UpdateInfo]:
        """Detect updates for Ansible collections"""
        updates = []
        
        try:
            # Get installed collections
            result = subprocess.run(
                ['ansible-galaxy', 'collection', 'list', '--format', 'json'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                collections_data = json.loads(result.stdout)
                
                for namespace_path, collections in collections_data.items():
                    for collection_name, collection_info in collections.items():
                        current_version = collection_info.get('version', 'unknown')
                        
                        # Check for updates on Ansible Galaxy
                        latest_version = await self._get_galaxy_latest_version(collection_name)
                        
                        if latest_version and version.parse(latest_version) > version.parse(current_version):
                            update = UpdateInfo(
                                component_type='collection',
                                component_name=collection_name,
                                current_version=current_version,
                                available_version=latest_version,
                                severity='moderate',
                                description=f'Ansible collection update for {collection_name}',
                                release_date=datetime.now().isoformat(),
                                changelog_url=f'https://galaxy.ansible.com/{collection_name}'
                            )
                            updates.append(update)
            
            self.logger.info(f"Detected {len(updates)} collection updates")
            return updates
            
        except Exception as e:
            self.logger.error(f"Failed to detect collection updates: {e}")
            return []
    
    async def _get_github_latest_release(self, repo: str) -> Optional[str]:
        """Get latest release version from GitHub API"""
        try:
            url = f"https://api.github.com/repos/{repo}/releases/latest"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('tag_name', '').lstrip('v')
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get GitHub release for {repo}: {e}")
            return None
    
    async def _get_pypi_latest_version(self, package: str) -> Optional[str]:
        """Get latest version from PyPI"""
        try:
            url = f"https://pypi.org/pypi/{package}/json"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data['info']['version']
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get PyPI version for {package}: {e}")
            return None
    
    async def _get_galaxy_latest_version(self, collection: str) -> Optional[str]:
        """Get latest version from Ansible Galaxy"""
        try:
            # Parse collection name (namespace.collection)
            if '.' not in collection:
                return None
            
            namespace, name = collection.split('.', 1)
            url = f"https://galaxy.ansible.com/api/v2/collections/{namespace}/{name}/"
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('latest_version', {}).get('version')
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get Galaxy version for {collection}: {e}")
            return None
    
    async def _determine_update_severity(self, component: str, version: str) -> str:
        """Determine update severity based on component and version"""
        # Security-related packages get higher severity
        security_packages = [
            'kernel', 'openssl', 'gnutls', 'openssh', 'sudo', 'systemd',
            'glibc', 'bash', 'curl', 'wget', 'nginx', 'httpd'
        ]
        
        if any(pkg in component.lower() for pkg in security_packages):
            return 'security'
        
        # System packages get moderate severity
        system_packages = [
            'dnf', 'yum', 'rpm', 'systemd', 'dbus', 'NetworkManager'
        ]
        
        if any(pkg in component.lower() for pkg in system_packages):
            return 'important'
        
        # Default to moderate
        return 'moderate'
    
    async def check_compatibility(self, update: UpdateInfo) -> str:
        """Check compatibility of an update with current system"""
        try:
            # Check compatibility matrix
            if update.component_name in self.compatibility_matrix:
                matrix = self.compatibility_matrix[update.component_name]
                
                # Get current OS version
                os_info = await self._get_os_info()
                os_version = os_info.get('version_id', 'unknown')
                
                # Check if version is in supported list
                supported_versions = matrix.supported_versions.get(os_version, [])
                if update.available_version in supported_versions:
                    return 'compatible'
                
                # Check test results
                test_status = matrix.test_results.get(update.available_version, 'unknown')
                if test_status in ['passed', 'compatible']:
                    return 'compatible'
                elif test_status in ['failed', 'incompatible']:
                    return 'incompatible'
            
            # Use AI Assistant for compatibility analysis (if enabled)
            if self.enable_ai_compatibility and self.ai_assistant_url:
                ai_result = await self._ai_compatibility_check(update)
                if ai_result:
                    return ai_result
            
            return 'needs_testing'
            
        except Exception as e:
            self.logger.error(f"Failed to check compatibility for {update.component_name}: {e}")
            return 'unknown'
    
    async def _ai_compatibility_check(self, update: UpdateInfo) -> Optional[str]:
        """Use AI Assistant to check update compatibility"""
        try:
            prompt = f"""
            Analyze the compatibility of this update for Qubinode Navigator:
            
            Component: {update.component_name}
            Type: {update.component_type}
            Current Version: {update.current_version}
            Available Version: {update.available_version}
            Severity: {update.severity}
            
            Consider:
            1. Known compatibility issues with RHEL/CentOS systems
            2. Breaking changes in the new version
            3. Dependencies and system requirements
            4. Impact on containerized environments (Podman/Docker)
            5. Ansible automation compatibility
            
            Respond with one of: compatible, incompatible, needs_testing
            Include a brief explanation.
            """
            
            response = requests.post(
                f"{self.ai_assistant_url}/chat",
                json={"message": prompt},
                timeout=10  # Reduced timeout
            )
            
            if response.status_code == 200:
                ai_response = response.json()
                text = ai_response.get('text', '').lower()
                
                if 'compatible' in text and 'incompatible' not in text:
                    return 'compatible'
                elif 'incompatible' in text:
                    return 'incompatible'
                elif 'needs_testing' in text or 'testing' in text:
                    return 'needs_testing'
            
            return None
            
        except requests.exceptions.Timeout:
            self.logger.warning(f"AI compatibility check timed out for {update.component_name}")
            return None
        except Exception as e:
            self.logger.error(f"AI compatibility check failed: {e}")
            return None
    
    async def create_update_batches(self, updates: List[UpdateInfo]) -> List[UpdateBatch]:
        """Create logical batches of updates"""
        batches = []
        
        # Group by severity and type
        security_updates = [u for u in updates if u.severity == 'security']
        critical_updates = [u for u in updates if u.severity == 'critical']
        important_updates = [u for u in updates if u.severity == 'important']
        moderate_updates = [u for u in updates if u.severity == 'moderate']
        low_updates = [u for u in updates if u.severity == 'low']
        
        # Create security batch (highest priority)
        if security_updates:
            batch_id = f"security_{int(time.time())}"
            batches.append(UpdateBatch(
                batch_id=batch_id,
                batch_type='security',
                updates=security_updates,
                total_size=sum(u.update_size or 0 for u in security_updates),
                estimated_duration='15-30 minutes',
                risk_level='medium',
                requires_reboot=any('kernel' in u.component_name for u in security_updates),
                rollback_plan='Automated snapshot rollback available',
                created_at=datetime.now()
            ))
        
        # Create critical batch
        if critical_updates:
            batch_id = f"critical_{int(time.time())}"
            batches.append(UpdateBatch(
                batch_id=batch_id,
                batch_type='critical',
                updates=critical_updates,
                total_size=sum(u.update_size or 0 for u in critical_updates),
                estimated_duration='10-20 minutes',
                risk_level='high',
                requires_reboot=False,
                rollback_plan='Package rollback available',
                created_at=datetime.now()
            ))
        
        # Create maintenance batch (important + moderate + low)
        maintenance_updates = important_updates + moderate_updates + low_updates
        if maintenance_updates:
            batch_id = f"maintenance_{int(time.time())}"
            batches.append(UpdateBatch(
                batch_id=batch_id,
                batch_type='maintenance',
                updates=maintenance_updates,
                total_size=sum(u.update_size or 0 for u in maintenance_updates),
                estimated_duration='30-60 minutes',
                risk_level='low',
                requires_reboot=False,
                rollback_plan='Individual package rollback',
                created_at=datetime.now()
            ))
        
        return batches
    
    async def run_full_update_check(self) -> Dict[str, Any]:
        """Run comprehensive update detection"""
        self.logger.info("Starting comprehensive update detection")
        start_time = time.time()
        
        # Detect all types of updates
        os_updates = await self.detect_os_updates()
        software_updates = await self.detect_software_updates()
        collection_updates = await self.detect_collection_updates()
        
        # Combine all updates
        all_updates = os_updates + software_updates + collection_updates
        
        # Check compatibility for each update
        for update in all_updates:
            update.compatibility_status = await self.check_compatibility(update)
        
        # Create update batches
        update_batches = await self.create_update_batches(all_updates)
        
        # Store results
        self.available_updates = all_updates
        self.last_check_time = datetime.now()
        
        # Generate summary
        summary = {
            'check_timestamp': self.last_check_time.isoformat(),
            'check_duration': time.time() - start_time,
            'total_updates': len(all_updates),
            'updates_by_type': {
                'os_packages': len(os_updates),
                'software': len(software_updates),
                'collections': len(collection_updates)
            },
            'updates_by_severity': {
                'security': len([u for u in all_updates if u.severity == 'security']),
                'critical': len([u for u in all_updates if u.severity == 'critical']),
                'important': len([u for u in all_updates if u.severity == 'important']),
                'moderate': len([u for u in all_updates if u.severity == 'moderate']),
                'low': len([u for u in all_updates if u.severity == 'low'])
            },
            'compatibility_status': {
                'compatible': len([u for u in all_updates if u.compatibility_status == 'compatible']),
                'incompatible': len([u for u in all_updates if u.compatibility_status == 'incompatible']),
                'needs_testing': len([u for u in all_updates if u.compatibility_status == 'needs_testing']),
                'unknown': len([u for u in all_updates if u.compatibility_status == 'unknown'])
            },
            'update_batches': len(update_batches),
            'updates': [asdict(update) for update in all_updates],
            'batches': [asdict(batch) for batch in update_batches]
        }
        
        self.logger.info(f"Update detection completed: {len(all_updates)} updates found in {summary['check_duration']:.2f}s")
        return summary
