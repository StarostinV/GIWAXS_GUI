# giwaxs-gui
### A graphical tool for GIWAXS data analysis.

giwaxs-gui contains all the basic functionality for 
the analysis of 2D diffraction images with circular symmetry. 
In particular, it focuses on grazing-incidence wide-angle scattering
data analysis and its specific needs.

### Dependencies

* PyQt5
* numpy 
* scipy
* opencv-python
* pyqtgraph
* h5py

## Install
### Pip install 

To install the current release via pip, you should have python installed 
on your computer. The minimum required version is 3.6.0. Install package via pip:

```sh
pip install giwaxs-gui
```

After installation you can launch the program:

```sh
python
>>>from giwaxs_gui import run
>>>run()
```

## Usage
### Overview

![overview](giwaxs_gui/static/readme/gui-overview-2.png)

The program provides different tools for visualizing, detecting and fitting 
Bragg reflections with circular or rotational symmetry on diffraction images. 
The corresponding angular and radial positions and sizes of 
detected diffraction reflections can be saved
for further analysis.

The graphical interface consists of several functional widgets that can be dragged 
over the window,
resized and hidden to optimize the analysis. One can show/hide widgets by clicking on corresponding 
icons on the top left toolbar. Main widgets are:

* File manager (left)
* Image viewer (top center)
* Radial and angular profiles (bottom right)
* Control widget (top right)
* Interpolation widget (not shown)

In the following some of these widgets are described in detail.

### File manager

![file-manager](giwaxs_gui/static/readme/file-manager.png)

File manager allows to add files and folders to the file tree. Image viewer 
automatically updates image based on selected file. It also shows Properties item containing
info about measurement geometry and added segments. All the changes are held by
file widget which allows processing many images simultaneously. The data and 
found segments can be saved to .h5 file.

#### Available extensions

Available files extensions to read from:

* .tif(f)
* .edf
* .h5

Please note that the currently used .edf reader is written for 
specific extension of .edf files used on some x-ray facilities. h5 file
reading is powered by h5py library, and .tiff files are read via opencv-python
package. Hence, the current list can be easily extended by the number of 
image extensions supported by opencv library.

Both H5 files parsing and folder parsing are designed in a way that they
read only the content of groups/folders which are selected. It may accelerate reading huge 
h5 files if they are well structured.

### Image viewer

![image-viewer](giwaxs_gui/static/readme/image-viewer.png)

Image viewer provides options for setting geometry (beam center, 
axes scale, image transformations - geometry toolbar on top left) 
and adopting the view by changing the colormap
and its bounds (histogram widget on the right). An added segment 
immediately appears on the image viewer. Currently this widget does not 
support moving segments by dragging, but provides its visualization.

### Radial profile

![radial-profile](giwaxs_gui/static/readme/radial-profile.png)
