______________________________________________________________________

## description: Delete a virtual machine (destructive - requires confirmation) allowed-tools: Bash(kcli:\*) argument-hint: \[vm-name\]

# Delete Virtual Machine: $1

You are helping delete a Qubinode Navigator virtual machine.

CRITICAL: This is a DESTRUCTIVE operation. Before proceeding:

1. Verify the VM exists:
   !`kcli info vm $1 2>/dev/null || echo "VM not found"`

1. Check if VM is currently in use:
   !`kcli list vm | grep $1`

1. Check for associated DNS records that should be cleaned up

1. Verify no dependent services rely on this VM

WARNING: Confirm with the user before executing deletion!

To delete:

```bash
kcli delete vm $1 -y
```

After deletion:

1. Clean up DNS records if needed: qubinode-dns remove <hostname>
1. Revoke any certificates: qubinode-cert revoke <hostname>
1. Update inventory if manually managed
