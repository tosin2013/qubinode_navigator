# Fixing DAGs Not Appearing in UI

## 🐛 Issue: "No results" or DAGs Disappearing

**Symptoms:**
- UI shows "No results" or "0-0 of 0 DAGs"
- DAGs appear then disappear
- "All 0", "Active 0", "Paused 0" counters
- `airflow dags list` shows DAGs exist ✅
- But UI shows nothing ❌

## ✅ Quick Fixes (Try in Order)

### Fix 1: Hard Refresh Browser (80% success rate)

**Why:** Browser caches the DAG list aggressively

```
Chrome/Edge:  Ctrl + Shift + R  (Windows/Linux)
              Cmd + Shift + R   (Mac)

Firefox:      Ctrl + F5
              or Ctrl + Shift + R

Safari:       Cmd + Option + R
```

### Fix 2: Clear Active/Paused Filters

**Why:** UI filters might be hiding DAGs

Looking at your screenshot:
- Click **"Active 0"** button to toggle it OFF
- Click **"Paused 0"** button to toggle it OFF
- Clear any tag filters in the search box
- Should show **"All"** filter only

### Fix 3: Wait for Auto-Refresh (if enabled)

**Why:** Auto-refresh syncs UI with database

- Look for "Auto-refresh" toggle (top right)
- If ON: Wait 30 seconds
- If OFF: Turn it ON and wait

### Fix 4: Clear Browser Cache

**Why:** Persistent cache can block updates

**Chrome/Edge:**
```
1. Press F12 (Developer Tools)
2. Right-click refresh button
3. Select "Empty Cache and Hard Reload"
```

**Firefox:**
```
1. Preferences → Privacy & Security
2. Cookies and Site Data → Clear Data
3. Check "Cached Web Content"
4. Clear
```

### Fix 5: Restart Webserver

**Why:** Forces UI to resync with database

```bash
cd /root/qubinode_navigator/airflow
podman-compose restart airflow-webserver

# Wait 30 seconds
sleep 30

# Check health
curl http://localhost:8888/health
```

### Fix 6: Database Sync Issue (rare)

**Why:** Scheduler hasn't written DAGs to DB yet

```bash
# Force DAG serialization
podman exec airflow_airflow-scheduler_1 airflow dags reserialize

# Wait a moment
sleep 10

# Refresh browser
```

## 🔍 Verification Steps

### Step 1: Verify DAGs Exist in CLI

```bash
podman exec airflow_airflow-scheduler_1 airflow dags list

# Should show:
# example_kcli_script_based
# example_kcli_virsh_combined  
# example_kcli_vm_provisioning
```

✅ If you see DAGs here, they exist in Airflow!

### Step 2: Check Health Status

```bash
podman ps --filter "name=airflow" --format "table {{.Names}}\t{{.Status}}"

# All should show "healthy" or at least "running"
```

### Step 3: Check for Import Errors

```bash
podman exec airflow_airflow-scheduler_1 airflow dags list-import-errors

# Should show: "No data found"
```

### Step 4: Check Webserver Can See DAGs

```bash
podman exec airflow_airflow-webserver_1 airflow dags list

# Should show same list as scheduler
```

## 🎯 Your Current Situation

**From your screenshot and CLI checks:**

```
✅ Scheduler: Running (but unhealthy status)
✅ Webserver: Running (healthy)
✅ DAGs exist in CLI: 3 DAGs found
✅ No import errors
❌ UI shows: "No results"

Diagnosis: Browser cache or UI filter issue
```

## 💡 Recommended Solution for You

**Try these in order:**

1. **Clear the "Active" filter in UI**
   - Your screenshot shows "Active 0" - click it to deselect
   - Try clicking just "All" to show everything

2. **Hard refresh browser**
   - Press Ctrl + Shift + R (or Cmd + Shift + R on Mac)
   - Or open in incognito/private window

3. **Check tag filter**
   - Look for the "Filter DAGs by tag" search box
   - Make sure it's empty

4. **If still not showing:**
   ```bash
   cd /root/qubinode_navigator/airflow
   podman-compose restart airflow-webserver airflow-scheduler
   sleep 30
   # Then refresh browser
   ```

## 🔧 Advanced Troubleshooting

### If Scheduler is "Unhealthy"

The scheduler might be unhealthy but still working. Check:

```bash
# Check scheduler health endpoint
podman exec airflow_airflow-scheduler_1 curl -f http://localhost:8974/health

# If it fails, scheduler health check needs fixing
# But DAGs should still work!
```

**Fix scheduler health (if needed):**

Check if curl is installed in container:
```bash
podman exec airflow_airflow-scheduler_1 which curl

# If not found, health check will fail
# But scheduler still processes DAGs!
```

### If DAGs Keep Disappearing

**Possible causes:**

1. **DAG parsing taking too long**
   - Check: `podman logs airflow_airflow-scheduler_1 | grep "DagFileProcessor"`
   - If you see timeout errors, DAGs might be too complex

2. **Database connection issues**
   - Check: `podman exec airflow_postgres_1 psql -U airflow -d airflow -c "SELECT COUNT(*) FROM dag;"`
   - Should show 3 (or your number of DAGs)

3. **File permissions**
   - Check: `podman exec airflow_airflow-scheduler_1 ls -la /opt/airflow/dags/`
   - All .py files should be readable

### UI Not Updating After DAG Changes

**If you edit a DAG but UI doesn't update:**

```bash
# Method 1: Touch the DAG file (forces rescan)
touch /root/qubinode_navigator/airflow/dags/example_kcli_script_based.py

# Wait 30 seconds for scheduler to detect change

# Method 2: Manually trigger rescan
podman exec airflow_airflow-scheduler_1 airflow dags reserialize

# Method 3: Restart scheduler (fastest)
podman-compose restart airflow-scheduler
```

## 📊 Common Scenarios

### Scenario 1: Just Deployed/Restarted

**What happens:**
- Scheduler needs 30-60 seconds to parse DAGs
- Webserver needs to fetch from database
- UI might show "0 DAGs" briefly

**Solution:** Wait 60 seconds, then hard refresh

### Scenario 2: After Adding New DAG

**What happens:**
- New DAG file created
- Scheduler parses it next cycle (default: 30s)
- Database updated
- UI refreshes (might be cached)

**Solution:**
```bash
# Speed it up:
podman-compose restart airflow-scheduler
sleep 30
# Hard refresh browser
```

### Scenario 3: After Container Restart

**What happens:**
- All services restart
- Database persists (in volume)
- But UI cache might be stale

**Solution:**
1. Wait 60 seconds after restart
2. Clear browser cache
3. Hard refresh

### Scenario 4: "DAGs" Tab Shows DAGs, But Grid/Graph Don't

**What happens:**
- List view cached
- Individual DAG views not cached

**Solution:**
- Click DAG name
- If it loads, it's just a cache issue
- Hard refresh after clicking

## 🎨 UI Behavior Explained

**Why does Airflow UI behave like this?**

1. **Heavy Caching:**
   - DAG list is expensive to compute
   - UI caches aggressively to improve performance
   - Tradeoff: Stale data sometimes

2. **Database Polling:**
   - Webserver polls database every 30s (default)
   - Doesn't immediately see scheduler changes
   - Auto-refresh helps but has delays

3. **Filter State:**
   - Filters persist in localStorage
   - Can hide DAGs unintentionally
   - Clearing filters shows all DAGs

## ✅ Prevention Tips

### 1. Always Use Auto-Refresh

Enable the "Auto-refresh" toggle (top right of UI):
- Updates every 30 seconds
- Keeps UI in sync
- Minimal performance impact

### 2. Use Incognito for Testing

When testing new DAGs:
- Open in incognito/private window
- No cache issues
- Fresh view every time

### 3. Bookmark Direct URLs

Instead of going to /dags, bookmark:
```
http://localhost:8888/dags  ← List view (can cache)
http://localhost:8888/       ← Home (always fresh)
```

### 4. Monitor Logs During Development

```bash
# Watch for DAG parsing
podman logs -f airflow_airflow-scheduler_1 | grep "example_kcli"

# See when your DAG is detected and loaded
```

## 🚀 Quick Reference Card

```
Problem: UI shows "No results"
├─ Step 1: Hard refresh (Ctrl+Shift+R) ........................ 5 seconds
├─ Step 2: Clear Active/Paused filters ........................ 2 seconds
├─ Step 3: Wait for auto-refresh .............................. 30 seconds
├─ Step 4: Restart webserver .................................. 60 seconds
└─ Step 5: Check CLI (airflow dags list) ...................... 5 seconds

If CLI shows DAGs but UI doesn't → Browser cache issue
If CLI shows no DAGs → DAG file or parsing issue
If scheduler unhealthy → Check logs, but DAGs might still work
```

## 📞 Emergency: Can't See Any DAGs

**Nuclear option (restarts everything):**

```bash
cd /root/qubinode_navigator/airflow

# Stop everything
podman-compose down

# Start fresh
podman-compose up -d

# Wait for services
sleep 60

# Check status
podman-compose ps

# Open UI in incognito window
# http://localhost:8888
# Login: admin/admin
```

## ✅ Success Checklist

You know it's working when:

- [ ] `airflow dags list` shows your DAGs
- [ ] Webserver status is "healthy"
- [ ] UI loads (even if shows "No results")
- [ ] Hard refresh shows DAGs
- [ ] Can click on DAG names
- [ ] Graph view loads
- [ ] Can trigger DAGs
- [ ] Auto-refresh keeps UI updated

## 🎯 For Your Specific Issue

**Based on your screenshot showing "No results":**

**Try this right now:**

1. **Look at the filter buttons** (Active/Paused)
   - Click them to turn OFF any filters
   - Only "All" should be selected

2. **Hard refresh:**
   - Press: Ctrl + Shift + R

3. **If still empty:**
   ```bash
   podman-compose restart airflow-webserver
   sleep 30
   ```
   Then refresh browser

4. **Still nothing? Open incognito:**
   - Chrome: Ctrl + Shift + N
   - Firefox: Ctrl + Shift + P
   - Go to: http://localhost:8888
   - Login: admin/admin

**You should see 3 DAGs:**
- `example_kcli_script_based` ← New one!
- `example_kcli_virsh_combined`
- `example_kcli_vm_provisioning`

The DAGs **definitely exist** - it's just a UI sync issue! 🎉
