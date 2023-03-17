import sys
import ast
from utils.router_utils import AllRouterModules


all_rm = AllRouterModules([sys.argv[1]])
rm = all_rm.get_router_module(sys.argv[1])

pose_1=ast.literal_eval(sys.argv[2])
pose_2=ast.literal_eval(sys.argv[3])

rl = rm.get_route_length(pose_1, pose_2)

print(f"Route length between {pose_1}, {pose_2}: {rl}")

