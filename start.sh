#!/usr/bin/env bash
set -e

cd Backend-Test
gunicorn app:app --bind "0.0.0.0:${PORT:-5000}"
