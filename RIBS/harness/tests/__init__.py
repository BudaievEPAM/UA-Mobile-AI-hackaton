"""Self-tests for the ios2ribs harness. Stdlib `unittest` only — no third-party deps.

Run from the RIBS/ directory:

    python3 -m unittest discover -s harness/tests -t .

Each module bootstraps ``sys.path`` so it also works under a bare
``python3 -m unittest discover harness/tests``.
"""
