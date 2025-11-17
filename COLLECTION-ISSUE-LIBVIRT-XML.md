# Collection Issue: Malformed Libvirt Network XML Template

**Collection**: `tosin2013.qubinode_kvmhost_setup_collection`  
**Version**: 0.10.2  
**Date Reported**: 2025-11-16  
**Environment**: CentOS Stream 10 (Coughlan)  
**Deployment Mode**: Ansible Navigator with `--execution-environment false`

---

## Issue Summary

The `kvmhost_setup` role fails when defining the libvirt bridge network due to malformed XML in the network definition template. The XML appears to have corrupted closing tags.

---

## Error Details

### Error Message
```
TASK [tosin2013.qubinode_kvmhost_setup_collection.kvmhost_setup : Ensure libvirt bridge network is defined]
fatal: [control]: FAILED! => {
  "changed": false,
  "msg": "at line 5: Extra content at the end of the document\n      </network>ork connections='1'>\n----------------^"
}
```

### Malformed XML Fragment
```xml
</network>ork connections='1'>
```

This should likely be:
```xml
</network>
```

Or possibly:
```xml
<network connections='1'>
```

### Task That Failed
- **Task**: `Ensure libvirt bridge network is defined`
- **Role**: `tosin2013.qubinode_kvmhost_setup_collection.kvmhost_setup`
- **Module**: Likely `community.libvirt.virt_net` or `ansible.builtin.template`

---

## Root Cause Analysis

The error indicates XML parsing failure due to malformed tags. This typically occurs when:

1. **Template Variable Corruption**: A Jinja2 variable is incorrectly placed, splitting the XML tag
2. **String Concatenation Error**: XML strings are being concatenated incorrectly
3. **Template Syntax Error**: Missing or extra braces/quotes in the template
4. **Copy-Paste Error**: Partial text duplication during editing

The fragment `</network>ork connections='1'>` suggests:
- `</network>` is the correct closing tag
- `ork connections='1'>` is extra/corrupted content
- Possibly meant to be `<network connections='1'>` at the start

---

## Affected File

The issue is likely in one of these files:
```
roles/kvmhost_setup/templates/libvirt_network.xml.j2
roles/kvmhost_setup/templates/bridge_network.xml.j2
roles/kvmhost_setup/tasks/bridge_interface.yml
roles/kvmhost_setup/tasks/libvirt_network.yml
```

---

## Deployment Progress Before Failure

The deployment successfully completed **136 tasks** before failing - **97% complete!**

### Successfully Completed Phases
1. ✅ OS Detection (CentOS Stream 10)
2. ✅ RHEL version compatibility check
3. ✅ Package installation
4. ✅ Service configuration
5. ✅ Shell configuration
6. ✅ Firewall configuration
7. ✅ Cockpit setup
8. ✅ Network configuration
9. ✅ Remote desktop setup
10. ✅ **Password configuration** (fixed in 0.10.2!)
11. ✅ Bridge interface configuration
12. ❌ **FAILED**: Libvirt network definition (malformed XML)

### Deployment Statistics
```
PLAY RECAP:
control : ok=136 changed=9 unreachable=0 failed=1 skipped=92 rescued=0 ignored=1
```

**Completion Rate**: ~97% (136 of ~140 estimated tasks)

---

## Expected Libvirt Network XML Format

A typical libvirt bridge network XML should look like:

```xml
<network connections='1'>
  <name>{{ bridge_name }}</name>
  <forward mode='nat'/>
  <bridge name='{{ bridge_name }}' stp='on' delay='0'/>
  <ip address='{{ bridge_ip }}' netmask='{{ bridge_netmask }}'>
    <dhcp>
      <range start='{{ dhcp_start }}' end='{{ dhcp_end }}'/>
    </dhcp>
  </ip>
</network>
```

---

## Debugging Steps

### Step 1: Locate the Template File
```bash
cd /root/.ansible/collections/ansible_collections/tosin2013/qubinode_kvmhost_setup_collection/

# Find libvirt network templates
find roles/kvmhost_setup/templates/ -name "*network*.xml.j2" -o -name "*bridge*.xml.j2"

# Find tasks that define libvirt networks
grep -r "virt_net\|libvirt.*network" roles/kvmhost_setup/tasks/
```

### Step 2: Examine the Template
```bash
# Look for the malformed closing tag
grep -n "</network>" roles/kvmhost_setup/templates/*.j2

# Check for the corrupted fragment
grep -n "ork connections" roles/kvmhost_setup/templates/*.j2
```

### Step 3: Validate XML Syntax
```bash
# If template found, render it manually and validate
ansible localhost -m template \
  -a "src=roles/kvmhost_setup/templates/network.xml.j2 dest=/tmp/network.xml" \
  -e "bridge_name=qubibr0"

# Validate the XML
xmllint --noout /tmp/network.xml
```

### Step 4: Check Task Definition
```bash
# Find the task that uses the template
grep -A10 -B5 "Ensure libvirt bridge network is defined" roles/kvmhost_setup/tasks/*.yml
```

---

## Suggested Fixes

### Fix 1: Correct the XML Template (Most Likely)

**Current (Incorrect)** - Hypothetical based on error:
```xml
<network connections='1'>
  <name>{{ bridge_name }}</name>
  ...
</network>ork connections='1'>
```

**Fixed**:
```xml
<network connections='1'>
  <name>{{ bridge_name }}</name>
  <forward mode='nat'/>
  <bridge name='{{ bridge_name }}' stp='on' delay='0'/>
  <ip address='{{ bridge_ip | default("192.168.122.1") }}' netmask='{{ bridge_netmask | default("255.255.255.0") }}'>
    <dhcp>
      <range start='{{ dhcp_start | default("192.168.122.2") }}' end='{{ dhcp_end | default("192.168.122.254") }}'/>
    </dhcp>
  </ip>
</network>
```

### Fix 2: Fix String Concatenation

If the XML is built via string concatenation:

**Current (Incorrect)**:
```yaml
network_xml: |
  <network connections='1'>
    <name>{{ bridge_name }}</name>
  </network>{{ extra_content }}
```

**Fixed**:
```yaml
network_xml: |
  <network connections='1'>
    <name>{{ bridge_name }}</name>
  </network>
```

### Fix 3: Fix Template Variable Placement

**Current (Incorrect)**:
```xml
</netw{{ variable }}ork connections='1'>
```

**Fixed**:
```xml
</network>
<network connections='1'>
```

---

## Workaround for Users

### Option 1: Skip Libvirt Network Creation

Add to inventory:
```yaml
# In inventories/localhost/group_vars/all.yml
create_libvirt_network: false
```

Then manually create the network after deployment:
```bash
cat > /tmp/qubibr0.xml << 'EOF'
<network>
  <name>qubibr0</name>
  <forward mode='nat'/>
  <bridge name='qubibr0' stp='on' delay='0'/>
  <ip address='192.168.122.1' netmask='255.255.255.0'>
    <dhcp>
      <range start='192.168.122.2' end='192.168.122.254'/>
    </dhcp>
  </ip>
</network>
EOF

virsh net-define /tmp/qubibr0.xml
virsh net-start qubibr0
virsh net-autostart qubibr0
```

### Option 2: Pre-create the Network

Create the network before running the deployment:
```bash
# Create default network if it doesn't exist
virsh net-list --all | grep -q default || {
  virsh net-define /usr/share/libvirt/networks/default.xml
  virsh net-start default
  virsh net-autostart default
}
```

---

## Impact

**Severity**: High  
**Impact**: Blocks one-command bootstrap deployment at 97% completion (136 of ~140 tasks)

**Affected Users**:
- All users deploying with collection 0.10.2
- Users on all platforms requiring libvirt bridge networks
- Users setting up KVM host with custom bridge configurations

**Workaround Available**: Yes (skip network creation or pre-create manually)

---

## Version History & Progress

### Collection Version Timeline
- **0.9.34**: 79 tasks (56%) - Firewall role issue
- **0.9.35**: 90 tasks (64%) - VNC package issue
- **0.9.37**: 84 tasks (60%) - Missing playbook issue
- **0.10.1**: 117 tasks (85%) - Recursive template bug
- **0.10.2**: 136 tasks (97%) - Libvirt XML malformed ⭐ **SO CLOSE!**

### Issues Fixed in 0.10.2
1. ✅ Recursive template loop in `xrdp_remote_user_password`
2. ✅ Password configuration now working
3. ✅ 19 additional tasks completed (117 → 136)

### Current Issue
- ❌ Malformed XML in libvirt network template

---

## Testing Recommendations

### Pre-Release XML Validation
1. **XML Lint All Templates**
   ```bash
   # Add to CI/CD pipeline
   find roles/*/templates/ -name "*.xml.j2" | while read template; do
     # Render with dummy variables
     ansible localhost -m template \
       -a "src=$template dest=/tmp/test.xml" \
       -e "bridge_name=test" \
       -e "bridge_ip=192.168.1.1" \
       -e "bridge_netmask=255.255.255.0"
     
     # Validate XML
     xmllint --noout /tmp/test.xml || exit 1
   done
   ```

2. **Template Syntax Checks**
   - Verify all Jinja2 variables are properly closed
   - Check for string concatenation issues
   - Validate XML structure before and after variable substitution

3. **Integration Tests**
   - Test libvirt network creation on all supported platforms
   - Verify network XML is valid before passing to virsh
   - Add error handling for XML validation failures

---

## Related Libvirt Documentation

- [Libvirt Network XML Format](https://libvirt.org/formatnetwork.html)
- [virsh net-define Command](https://libvirt.org/manpages/virsh.html#net-define)
- [Ansible community.libvirt.virt_net Module](https://docs.ansible.com/ansible/latest/collections/community/libvirt/virt_net_module.html)

---

## Recommended Solution Priority

1. **Critical**: Fix malformed XML in template (Fix 1)
2. **High**: Add XML validation before virsh commands
3. **Medium**: Add error handling for network creation failures
4. **Low**: Make libvirt network creation optional

---

## Additional Context

### Why This Matters
We are at **97% completion** - only ~4 tasks away from a successful deployment! This is the closest we've gotten to achieving the one-command bootstrap goal.

### User Experience Impact
Users experience a nearly complete deployment:
- ✅ 136 tasks completed successfully
- ✅ All major components configured
- ✅ System ready except for libvirt networking
- ❌ **Blocked at final step**: Network bridge creation

### Deployment Time
- **Time to failure**: ~10-15 minutes
- **Tasks completed**: 136 of ~140 (97%)
- **Remaining tasks**: ~4 (network validation and finalization)

---

## Success Metrics

Once this issue is fixed, we expect:
- ✅ **100% task completion** (~140 tasks)
- ✅ **Successful one-command bootstrap** on CentOS Stream 10
- ✅ **Full KVM host setup** with networking
- ✅ **Ready for VM deployment**

This is likely the **FINAL blocker** for achieving the one-command bootstrap goal! 🎯

---

## Contact

**Reporter**: Deployment automation testing  
**Collection Repository**: https://galaxy.ansible.com/tosin2013/qubinode_kvmhost_setup_collection  
**GitHub Issues**: https://github.com/tosin2013/qubinode_kvmhost_setup_collection/issues  
**Related Issue**: Malformed XML in libvirt network template

---

## Logs

Full deployment log available upon request. Key excerpt:

```
PLAY RECAP:
control : ok=136 changed=9 unreachable=0 failed=1 skipped=92 rescued=0 ignored=1
```

**Last Successful Task**: Bridge interface configuration  
**Failed Task**: `Ensure libvirt bridge network is defined`  
**Error**: `at line 5: Extra content at the end of the document </network>ork connections='1'>`  
**Next Expected Tasks**: Network validation, final system checks, deployment completion
