#!/bin/bash
# Wrapper script - maintains backward compatibility
cd "$(dirname "$0")"
./scripts/diagnostics/run_diagnostic.sh "$@"
