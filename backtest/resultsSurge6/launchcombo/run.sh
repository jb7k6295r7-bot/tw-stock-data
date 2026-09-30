#!/bin/bash
cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchSurge6_launchcombo "$@" > backtest/resultsSurge6/launchcombo/stdout$1.log 2>&1
tail -3 backtest/resultsSurge6/launchcombo/stdout$1.log
