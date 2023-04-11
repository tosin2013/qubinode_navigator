import os
import sys

if not os.environ.get('SSH_PASSWORD'):
    print("Environment variable SSH_PASSWORD is not set. Exiting.", file=sys.stderr)
    sys.exit(1)

if not os.environ.get('SSH_HOST'):
    print("Environment variable SSH_HOST is not set. Exiting.", file=sys.stderr)
    sys.exit(1)