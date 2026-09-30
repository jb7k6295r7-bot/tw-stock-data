#!/bin/bash
cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchSurge6_launch "$@" > backtest/resultsSurge6/launch/stdout$1.log 2>&1
