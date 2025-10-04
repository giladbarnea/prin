
"""
bench_detect.py
----------------
Tiny CLI to exercise fastsig.py on a directory tree.
Usage:
    python bench_detect.py /path/to/dir
"""
import sys, os, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastsig import detect_file

def iter_files(root):
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            yield os.path.join(dirpath, name)

def main():
    if len(sys.argv) != 2:
        print("Usage: python bench_detect.py <directory>")
        sys.exit(2)
    root = sys.argv[1]
    paths = list(iter_files(root))
    t0 = time.perf_counter()
    results = {}
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as ex:
        futs = {ex.submit(detect_file, p): p for p in paths}
        for fut in as_completed(futs):
            p = futs[fut]
            try:
                results[p] = fut.result()
            except Exception as e:
                results[p] = None
    dt = time.perf_counter() - t0
    n = len(paths)
    print(f"Scanned {n} files in {dt:.3f}s  ({(n/dt) if dt>0 else 0:.1f} files/s)")
    # print a quick summary
    from collections import Counter
    c = Counter(m.kind if m else "unknown" for m in results.values())
    for k, v in c.most_common():
        print(f"{k:12} {v}")

if __name__ == "__main__":
    main()
