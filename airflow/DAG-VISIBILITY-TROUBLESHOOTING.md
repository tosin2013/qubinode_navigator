# DAG Visibility Troubleshooting

## 🎯 Issue: "I don't see any active DAGs"

### ✅ Quick Fix Checklist

1. **Refresh Browser** (Most Common Fix)
   ```
   Hard refresh: Ctrl + Shift + R (Windows) or Cmd + Shift + R (Mac)
   ```

2. **Check DAG Toggle**
   - Look at the left side of each DAG row
   - Toggle should be **ON** (blue/active)
   - If OFF, click it to activate

3. **Check Filters**
   - Top of DAGs page has filter options
   - Make sure "Show Active" is selected
   - Clear any tag filters

4. **Navigate Directly**
   ```
   http://localhost:8888/dags
   ```

### 🔍 Verify DAGs Are Loaded

From command line:

```bash
# Check DAG list
podman exec airflow_airflow-scheduler_1 airflow dags list

# Should show:
# example_kcli_vm_provisioning  | False  ← Not paused
# example_kcli_virsh_combined   | False  ← Not paused
```

### 🔧 If DAGs Are Paused

```bash
# Unpause DAGs
podman exec airflow_airflow-scheduler_1 airflow dags unpause example_kcli_vm_provisioning
podman exec airflow_airflow-scheduler_1 airflow dags unpause example_kcli_virsh_combined
```

### 📊 Check for Import Errors

```bash
# Check for DAG import errors
podman exec airflow_airflow-scheduler_1 airflow dags list-import-errors

# Should show: "No data found"
```

### 🔄 Restart Services (If Needed)

```bash
cd /root/qubinode_navigator/airflow
podman-compose restart airflow-webserver airflow-scheduler

# Wait 30 seconds
sleep 30

# Check health
curl http://localhost:8888/health
```

### 🎨 UI Navigation Guide

```
┌─────────────────────────────────────────────┐
│ Airflow UI: http://localhost:8888          │
└─────────────────────────────────────────────┘
                    ↓
        ┌───────────────────────┐
        │   Login Page          │
        │   User: admin         │
        │   Pass: admin         │
        └───────────────────────┘
                    ↓
        ┌───────────────────────┐
        │   DAGs Page           │
        │   (Should see 2 DAGs) │
        └───────────────────────┘
```

### ✅ What You Should See

**DAGs Page:**
```
Toggle | DAG ID                       | Owner    | Runs | Last Run
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🔵   example_kcli_vm_provisioning  qubinode   0      -
  🔵   example_kcli_virsh_combined   qubinode   0      -
```

**Each DAG Row Has:**
- 🔵 Blue toggle (active)
- ▶️ Play button (trigger)
- 📋 DAG name (clickable)
- ℹ️ Info icons

### 🚫 Common Issues

#### Issue 1: Toggle is OFF (Gray)
**Fix:** Click the toggle to turn it ON (blue)

#### Issue 2: Blank Page
**Fix:** Hard refresh browser (Ctrl + Shift + R)

#### Issue 3: "No DAGs found"
**Fix:** 
```bash
# Check if DAG files exist
ls -la /root/qubinode_navigator/airflow/dags/example_*.py

# Should show:
# example_kcli_vm_provisioning.py
# example_kcli_virsh_combined.py
```

#### Issue 4: Red Error Message
**Check logs:**
```bash
podman logs airflow_airflow-scheduler_1 --tail 50 | grep -i error
```

### 📱 Browser Compatibility

**Tested Browsers:**
- ✅ Chrome/Chromium
- ✅ Firefox
- ✅ Edge
- ✅ Safari

**Clear Browser Cache:**
```
Chrome: Settings → Privacy → Clear browsing data
Firefox: Preferences → Privacy & Security → Clear Data
```

### 🔍 Debug Mode

Enable verbose logging:

```bash
# Check scheduler status
podman exec airflow_airflow-scheduler_1 airflow dags report

# Check DAG details
podman exec airflow_airflow-scheduler_1 airflow dags show example_kcli_vm_provisioning

# Check task list
podman exec airflow_airflow-scheduler_1 airflow tasks list example_kcli_vm_provisioning
```

### 📞 Still Having Issues?

1. **Check Services:**
   ```bash
   podman ps | grep airflow
   # All should be "Up" and "healthy"
   ```

2. **Check Logs:**
   ```bash
   podman logs airflow_airflow-webserver_1 --tail 50
   podman logs airflow_airflow-scheduler_1 --tail 50
   ```

3. **Restart Everything:**
   ```bash
   cd /root/qubinode_navigator/airflow
   ./deploy-airflow.sh restart
   ```

4. **Access URL Directly:**
   ```
   http://localhost:8888/dags
   Login: admin / admin
   ```

### ✅ Success Indicators

You know it's working when:

- ✅ See 2 DAGs in the list
- ✅ Toggles are blue/active
- ✅ Can click DAG names
- ✅ See play button ▶️ on each DAG
- ✅ Can access Graph view
- ✅ Can see task details

### 🎯 Quick Test

After fixing:

1. Go to: http://localhost:8888/dags
2. Click on `example_kcli_vm_provisioning`
3. Click "Graph" view
4. You should see: 7 tasks connected in sequence
5. Click play button ▶️ to trigger

If you see all this, everything is working! ✅

## 📝 Current Status

As of now (after unpausing):

```bash
$ airflow dags list
dag_id                       | is_paused
=============================+==========
example_kcli_vm_provisioning | False     ← Active!
example_kcli_virsh_combined  | False     ← Active!
```

✅ Both DAGs are active and ready to use!
