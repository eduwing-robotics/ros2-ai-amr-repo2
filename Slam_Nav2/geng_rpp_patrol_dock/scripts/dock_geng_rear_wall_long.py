#!/usr/bin/env python3
"""Run the existing rear-wall docker with enough time for a slow approach."""

import dock_geng_rear_wall as docker


docker.DOCK_TIMEOUT = 15.0


if __name__ == "__main__":
    raise SystemExit(docker.main())
