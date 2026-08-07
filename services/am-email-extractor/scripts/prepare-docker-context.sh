#!/usr/bin/env bash
set -euo pipefail

service_root="$(cd "$(dirname "$0")/.." && pwd)"
platform_security="${service_root}/../../../am-platform/libraries/am-platform-security"
target="${service_root}/third_party/am-platform-security"

if [[ ! -d "${platform_security}" ]]; then
  echo "am-platform-security not found at ${platform_security}" >&2
  exit 1
fi

mkdir -p "${service_root}/third_party"
rm -rf "${target}"
cp -r "${platform_security}" "${target}"
echo "Staged am-platform-security at ${target}"
