-- Gen.G arena — Cartographer pure localization (pbstream 필요)
include "cartographer_arena_mapping.lua"

TRAJECTORY_BUILDER.pure_localization_trimmer = {
  max_submaps_to_keep = 3,
}
POSE_GRAPH.optimize_every_n_nodes = 20

return options
