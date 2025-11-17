#!/bin/bash
# Check GitHub Actions deployment status for AI Assistant

echo "🔍 Checking GitHub Actions deployment status..."
echo ""

# Get the latest commit hash
COMMIT_HASH=$(git rev-parse HEAD)
echo "📝 Latest commit: $COMMIT_HASH"

# Repository info
REPO_URL="https://github.com/tosin2013/qubinode_navigator"
ACTIONS_URL="$REPO_URL/actions"

echo ""
echo "🔗 GitHub Actions Dashboard:"
echo "   $ACTIONS_URL"
echo ""
echo "🔗 Commit on GitHub:"
echo "   $REPO_URL/commit/$COMMIT_HASH"
echo ""

# Check if gh CLI is available for more detailed status
if command -v gh &> /dev/null; then
    echo "📊 GitHub CLI Status:"
    gh run list --limit 5 --repo tosin2013/qubinode_navigator
else
    echo "💡 Install GitHub CLI (gh) for detailed workflow status"
    echo "   Visit the Actions URL above to monitor deployment progress"
fi

echo ""
echo "🎯 What to look for:"
echo "   ✅ AI Assistant CI/CD Pipeline workflow should be running"
echo "   ✅ Container build should succeed with llama.cpp fix"
echo "   ✅ Integration tests should pass"
echo "   ✅ Container should be pushed to registry"
