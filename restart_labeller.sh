#!/bin/bash

echo "🔄 Restarting Labeller..."

# Kill existing labeller processes
pkill -f "labeller/app.py"
sleep 2

# Start labeller with correct path
echo "🚀 Starting labeller on port 5000..."
cd /home/olise/Projects/nexus
python labeller/app.py --data labeller/nestvision > logs/labeller.log 2>&1 &

sleep 3

# Check if it's running
if curl -s http://localhost:5000/health > /dev/null 2>&1; then
    echo "✅ Labeller is running!"
    echo "📝 Check logs: tail -f logs/labeller.log"
    echo "🌐 Homepage: http://localhost:5000"
else
    echo "❌ Labeller failed to start. Check logs/labeller.log"
fi
