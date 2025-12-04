#!/bin/bash
# Comprehensive Airflow Deployment Test Script
# Tests all components after fresh deployment

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 Airflow Deployment Test Suite"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Track test results
TESTS_PASSED=0
TESTS_FAILED=0

# Test function
run_test() {
    local test_name="$1"
    local test_command="$2"

    echo "📋 Test: $test_name"
    if eval "$test_command" > /dev/null 2>&1; then
        echo "   ✅ PASS"
        ((TESTS_PASSED++))
    else
        echo "   ❌ FAIL"
        ((TESTS_FAILED++))
    fi
    echo ""
}

# Test with output
run_test_with_output() {
    local test_name="$1"
    local test_command="$2"

    echo "📋 Test: $test_name"
    if output=$(eval "$test_command" 2>&1); then
        echo "   ✅ PASS"
        echo "$output" | sed 's/^/   /'
        ((TESTS_PASSED++))
    else
        echo "   ❌ FAIL"
        echo "$output" | sed 's/^/   /'
        ((TESTS_FAILED++))
    fi
    echo ""
}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  Container Health Tests"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

run_test "Postgres container running" \
    "podman ps | grep -q airflow_postgres"

run_test "Webserver container running" \
    "podman ps | grep -q airflow_airflow-webserver"

run_test "Scheduler container running" \
    "podman ps | grep -q airflow_airflow-scheduler"

run_test "Postgres is healthy" \
    "podman ps --filter 'name=airflow_postgres' --format '{{.Status}}' | grep -q healthy"

run_test "Webserver is healthy" \
    "podman ps --filter 'name=airflow_airflow-webserver' --format '{{.Status}}' | grep -q healthy"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  Network Connectivity Tests"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

run_test "Webserver health endpoint" \
    "curl -sf http://localhost:8888/health > /dev/null"

run_test "AI Assistant on network" \
    "podman network inspect airflow_default | grep -q qubinode-ai-assistant"

run_test "Scheduler can reach postgres" \
    "podman exec airflow_airflow-scheduler_1 pg_isready -h postgres -U airflow -d airflow"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣  Airflow Component Tests"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

run_test_with_output "DAGs loaded (count)" \
    "podman exec airflow_airflow-scheduler_1 airflow dags list 2>/dev/null | grep -E '^example_kcli' | wc -l"

run_test "No DAG import errors" \
    "podman exec airflow_airflow-scheduler_1 airflow dags list-import-errors 2>&1 | grep -q 'No data found'"

run_test_with_output "Plugins loaded" \
    "podman exec airflow_airflow-scheduler_1 ls /opt/airflow/plugins/qubinode/"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4️⃣  Volume Mount Tests"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

run_test "DAGs directory mounted" \
    "podman exec airflow_airflow-scheduler_1 test -d /opt/airflow/dags"

run_test "Scripts directory mounted" \
    "podman exec airflow_airflow-scheduler_1 test -d /opt/airflow/scripts"

run_test "Plugins directory mounted" \
    "podman exec airflow_airflow-scheduler_1 test -d /opt/airflow/plugins"

run_test "Libvirt socket mounted" \
    "podman exec airflow_airflow-scheduler_1 test -S /var/run/libvirt/libvirt-sock"

run_test_with_output "Test scripts accessible" \
    "podman exec airflow_airflow-scheduler_1 ls /opt/airflow/scripts/test-*.sh | wc -l"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5️⃣  kcli Integration Tests"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

run_test_with_output "kcli installed" \
    "podman exec airflow_airflow-scheduler_1 which kcli"

run_test_with_output "kcli version" \
    "podman exec airflow_airflow-scheduler_1 python -m pip list | grep kcli"

run_test "genisoimage installed" \
    "podman exec airflow_airflow-scheduler_1 which genisoimage > /dev/null"

run_test "virsh accessible" \
    "podman exec airflow_airflow-scheduler_1 virsh -c qemu:///system uri > /dev/null"

run_test_with_output "libvirt images available" \
    "podman exec airflow_airflow-scheduler_1 virsh -c qemu:///system vol-list default 2>/dev/null | grep -c stream"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6️⃣  kcli VM Creation Test (Full Workflow)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

VM_TEST_NAME="test-deploy-$(date +%s)"

echo "📋 Test: Create VM using kcli"
if podman exec airflow_airflow-scheduler_1 kcli create vm "$VM_TEST_NAME" -i centos10stream -P memory=1024 -P numcpus=1 -P disks=[5] 2>&1 | grep -q "created on local"; then
    echo "   ✅ PASS - VM created"
    ((TESTS_PASSED++))

    sleep 5

    echo ""
    echo "📋 Test: Verify VM exists in virsh"
    if podman exec airflow_airflow-scheduler_1 virsh -c qemu:///system dominfo "$VM_TEST_NAME" > /dev/null 2>&1; then
        echo "   ✅ PASS - VM visible in virsh"
        ((TESTS_PASSED++))
    else
        echo "   ❌ FAIL - VM not in virsh"
        ((TESTS_FAILED++))
    fi

    echo ""
    echo "📋 Test: Verify VM exists in kcli list"
    if kcli list vms 2>/dev/null | grep -q "$VM_TEST_NAME"; then
        echo "   ✅ PASS - VM visible in kcli"
        ((TESTS_PASSED++))
    else
        echo "   ❌ FAIL - VM not in kcli list"
        ((TESTS_FAILED++))
    fi

    echo ""
    echo "📋 Test: Delete VM"
    if kcli delete vm "$VM_TEST_NAME" -y 2>&1 | grep -q "deleted"; then
        echo "   ✅ PASS - VM deleted"
        ((TESTS_PASSED++))
    else
        echo "   ❌ FAIL - VM deletion failed"
        ((TESTS_FAILED++))
    fi

    echo ""
    echo "📋 Test: Verify VM removed"
    sleep 2
    if ! virsh -c qemu:///system dominfo "$VM_TEST_NAME" > /dev/null 2>&1; then
        echo "   ✅ PASS - VM removed from virsh"
        ((TESTS_PASSED++))
    else
        echo "   ❌ FAIL - VM still exists"
        ((TESTS_FAILED++))
        # Cleanup
        virsh -c qemu:///system destroy "$VM_TEST_NAME" 2>/dev/null || true
        virsh -c qemu:///system undefine "$VM_TEST_NAME" --remove-all-storage 2>/dev/null || true
    fi
else
    echo "   ❌ FAIL - VM creation failed"
    ((TESTS_FAILED++))
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "7️⃣  DAG Operations Tests"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📋 Test: Unpause script-based DAG"
if podman exec airflow_airflow-scheduler_1 airflow dags unpause example_kcli_script_based 2>&1 | grep -q "example_kcli_script_based"; then
    echo "   ✅ PASS - DAG unpaused"
    ((TESTS_PASSED++))
else
    echo "   ❌ FAIL - Could not unpause DAG"
    ((TESTS_FAILED++))
fi

echo ""
echo "📋 Test: Verify DAG is unpaused"
if podman exec airflow_airflow-scheduler_1 airflow dags list 2>/dev/null | grep "example_kcli_script_based" | grep -q "False"; then
    echo "   ✅ PASS - DAG is active"
    ((TESTS_PASSED++))
else
    echo "   ❌ FAIL - DAG still paused"
    ((TESTS_FAILED++))
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Test Results Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "   ✅ Passed: $TESTS_PASSED"
echo "   ❌ Failed: $TESTS_FAILED"
echo "   📊 Total:  $((TESTS_PASSED + TESTS_FAILED))"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo "🎉 All tests passed! Deployment is healthy!"
    echo ""
    echo "🚀 Next steps:"
    echo "   1. Open UI: http://localhost:8888"
    echo "   2. Login: admin / admin"
    echo "   3. Trigger DAG: example_kcli_script_based"
    echo ""
    exit 0
else
    echo "⚠️  Some tests failed. Review output above."
    echo ""
    echo "Common fixes:"
    echo "   • Wait 60s for scheduler to fully start"
    echo "   • Check logs: podman logs airflow_airflow-scheduler_1"
    echo "   • Restart if needed: podman-compose restart"
    echo ""
    exit 1
fi
