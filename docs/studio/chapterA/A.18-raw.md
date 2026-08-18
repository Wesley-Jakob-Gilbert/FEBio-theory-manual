# A.18 RAW

The RAW format is used to define a 3D stack of image data. The RAW file reader will import the image data and generate a hexahedral mesh that has the same number of elements in x, y, and z as the image dimensions. The elements are partitioned based on the grayscale levels in the image. For instance, for a black-and-white image, two parts will be created, one for all the elements that correspond to the black part of the image, and one for all the elements that correspond to the white part of the image.
