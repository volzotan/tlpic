import numpy as np
import open3d as o3d
import matplotlib.pyplot as plt

# data = []

# with open("p.xyz", "r") as f:
#     for line in f:
#         d = line.split(" ")
#         point = []
#         for i in range(0, len(d)):
#             point.append(float(d[i]))
#         data.append(point)

# print(data)

pcd = o3d.io.read_point_cloud("p.xyz", format='xyz')

print(pcd)

pcd.normals = o3d.utility.Vector3dVector(np.zeros((1, 3)))  # invalidate existing normals

pcd.estimate_normals()

# o3d.visualization.draw_geometries([pcd], point_show_normal=True)
# exit()

with o3d.utility.VerbosityContextManager(o3d.utility.VerbosityLevel.Debug) as cm:
    mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd, depth=9)
    print(mesh)
    # o3d.visualization.draw_geometries([mesh])

    print('visualize densities')
    densities = np.asarray(densities)
    density_colors = plt.get_cmap('plasma')((densities - densities.min()) / (densities.max() - densities.min()))
    density_colors = density_colors[:, :3]
    density_mesh = o3d.geometry.TriangleMesh()
    density_mesh.vertices = mesh.vertices
    density_mesh.triangles = mesh.triangles
    density_mesh.triangle_normals = mesh.triangle_normals
    density_mesh.vertex_colors = o3d.utility.Vector3dVector(density_colors)
    o3d.visualization.draw_geometries([density_mesh])