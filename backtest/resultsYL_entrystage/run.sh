#!/bin/bash
cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYL_entrystage "$@" > backtest/resultsYL_entrystage/stdout$1.log 2>&1
