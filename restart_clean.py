#!/usr/bin/env python
"""
Quick restart script for DashApp - stops old processes and starts fresh
"""
import subprocess
import time
import os
import signal

# Kill any existing python DashApp processes
try:
    result = subprocess.run(['taskkill', '/F', '/IM', 'python.exe'], 
                          capture_output=True, text=True)
    print("✓ Killed existing Python processes")
except:
    pass

# Wait for processes to fully terminate
time.sleep(3)

# Start fresh server
print("\n🚀 Starting Dash server...")
print("=" * 60)

os.chdir(r'd:\Hire Q Project\Modeling _2')
subprocess.run([r'python', 'DashApp.py'])
