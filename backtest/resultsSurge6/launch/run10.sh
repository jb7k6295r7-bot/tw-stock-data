#!/bin/bash
cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchSurge6_launch10 "$@" > backtest/resultsSurge6/launch/stdout10$1.log 2>&1
tail -3 backtest/resultsSurge6/launch/stdout10$1.log
