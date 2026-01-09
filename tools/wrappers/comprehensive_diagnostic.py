#!/bin/bash
# Wrapper script - maintains backward compatibility
cd "$(dirname "$0")"
./scripts/diagnostics/comprehensive_diagnostic.py "$@"
