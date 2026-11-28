#!/usr/bin/env bash
set -euo pipefail
prefix="$HOME/.local/share/rsec/inkling-compiler"
mkdir -p "$prefix/packages" "$prefix/bin"
cd "$prefix/packages"
apt-get -o Acquire::Retries=2 download \
  gcc-13-x86-64-linux-gnu cpp-13-x86-64-linux-gnu g++-13-x86-64-linux-gnu \
  libgcc-13-dev libstdc++-13-dev libc6-dev linux-libc-dev libpython3.12-dev \
  libisl23 libmpc3 libmpfr6
for deb in ./*.deb; do dpkg-deb -x "$deb" "$prefix"; done
[[ -e "$prefix/lib" ]] || ln -s /lib "$prefix/lib"
[[ -e "$prefix/lib64" ]] || ln -s /lib64 "$prefix/lib64"
standard="$prefix/usr/lib/x86_64-linux-gnu/libstdc++.so.6"
[[ -e "$standard" ]] || ln -s /usr/lib/x86_64-linux-gnu/libstdc++.so.6 "$standard"
cat > "$prefix/bin/cc" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
prefix="$(cd -- "$(dirname -- "$0")/.." && pwd)"
export LD_LIBRARY_PATH="$prefix/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec "$prefix/usr/bin/x86_64-linux-gnu-gcc-13" --sysroot="$prefix" \
  -B "$prefix/usr/lib/gcc/x86_64-linux-gnu/13/" \
  -B "$prefix/usr/lib/x86_64-linux-gnu/" \
  -isystem "$prefix/usr/include/python3.12" "$@"
EOF
cat > "$prefix/bin/c++" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
prefix="$(cd -- "$(dirname -- "$0")/.." && pwd)"
export LD_LIBRARY_PATH="$prefix/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec "$prefix/usr/bin/x86_64-linux-gnu-g++-13" --sysroot="$prefix" \
  -B "$prefix/usr/lib/gcc/x86_64-linux-gnu/13/" \
  -B "$prefix/usr/lib/x86_64-linux-gnu/" \
  -isystem "$prefix/usr/include/python3.12" "$@"
EOF
chmod u+x "$prefix/bin/cc" "$prefix/bin/c++"
printf '#include <Python.h>\nint rsec_test(void) { return PY_MAJOR_VERSION; }\n' |
  "$prefix/bin/cc" -shared -fPIC -x c -o "$prefix/compiler-probe.so" -
printf 'Isolated Ubuntu compiler verified.\n'
