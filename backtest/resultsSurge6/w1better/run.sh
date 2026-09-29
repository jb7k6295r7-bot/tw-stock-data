#!/bin/bash
cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchSurge6_w1better "$@" > backtest/resultsSurge6/w1better/stdout_$1.log 2>&1
