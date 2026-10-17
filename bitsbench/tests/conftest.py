import os
import tempfile

# Hypothesis spaces are cached on disk; keep the test cache out of the user's home directory.
os.environ.setdefault("BITSBENCH_CACHE", os.path.join(tempfile.gettempdir(), "bitsbench-test-cache"))
