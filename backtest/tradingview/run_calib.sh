#!/bin/bash
cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python backtest/tradingview/calib.py > backtest/tradingview/calib.log 2>&1
