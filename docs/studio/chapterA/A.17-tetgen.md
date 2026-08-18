# A.17 TETGEN

File format used by the TetGen software. TetGen typically splits the mesh into two separate files, a .node file, which contains the nodal coordinates and .ele file, which contains the element connectivity. The TetGen file reader expects the .ele file and will automatically look for a .node file that has the same file name. So, for example, if the .ele file is called “mymesh.ele”, then the file reader will look for a .node file called “mymesh.node” in the same file folder.
