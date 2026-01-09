#!/bin/bash
# Wrapper script - maintains backward compatibility
cd "$(dirname "$0")"
./scripts/validation/validate_portable.py "$@"
