#!/bin/bash
# Simple demonstration of pipe functionality with vibe

echo "🚀 VAgents Pipe Functionality Demo"
echo "=================================="

# Test 1: Simple echo through pipe
echo ""
echo "📝 Test 1: Echo text through pipe"
echo "Command: echo 'Hello from pipe!' | ./vibe run demo-package"
echo "Sample output:"
echo "📥 Received 18 characters from stdin"
echo "🔍 Preview: 'Hello from pipe!'"
echo "✅ Package executed successfully!"

# Test 2: Cat file through pipe
echo ""
echo "📁 Test 2: File content through pipe"
echo "Command: cat myfile.txt | ./vibe run text-analyzer --format summary"
echo "Sample output:"
echo "📥 Received 245 characters from stdin"
echo "Processed 12 lines, 45 words, 245 characters"

# Test 3: Command output through pipe
echo ""
echo "📊 Test 3: Command output through pipe"
echo "Command: ls -la | ./vibe run log-analyzer --verbose"
echo "Sample output:"
echo "📥 Received 456 characters from stdin"
echo "🔍 Preview: 'total 24\\ndrwxr-xr-x 3 user user 4096...'"
echo "Analyzed directory listing: 8 files found"

# Test 4: JSON processing
echo ""
echo "🔧 Test 4: JSON data processing"
echo "Command: curl -s https://api.github.com/repos/user/repo | ./vibe run json-processor"
echo "Sample output:"
echo "📥 Received 1234 characters from stdin"
echo "Processed JSON data: repository 'repo' with 15 stars"

# Test 5: Chain operations
echo ""
echo "⛓️  Test 5: Chained operations"
echo "Command: cat logs.txt | grep ERROR | ./vibe run error-analyzer --severity high"
echo "Sample output:"
echo "📥 Received 89 characters from stdin"
echo "Found 3 error entries, severity: high"

echo ""
echo "💡 Key Features:"
echo "- Automatic stdin detection"
echo "- Content preview in stderr"
echo "- Flexible parameter passing (--stdin-as)"
echo "- Compatible with all VAgents packages"
echo "- Seamless integration with shell pipelines"

echo ""
echo "📖 Usage Examples:"
echo "  cat data.txt | vibe run summarize"
echo "  echo 'test' | vibe run process --verbose"
echo "  curl api.com/data | vibe run analyze --format json"
echo "  ./vibe help <package-name>  # See package-specific help"
