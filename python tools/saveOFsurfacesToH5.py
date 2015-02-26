#! /usr/bin/env python

# -*- coding: utf-8 -*-

#=============================================================================#
# Import modules
#=============================================================================#

import re
import os
import sys
import h5py
import argparse

# math modules
import numpy as np

#=============================================================================#
# Functions
#=============================================================================#
def is_number(string):
    try:
        float(string)
        return True
    except ValueError:
        return False


def get_immediate_SubDirList(a_dir):
    '''
    Get the list of direct subFolder included in "a_dir"
    
    Arguments:
        *a_dir*: python string
    '''
    return [name for name in os.listdir(a_dir)
            if os.path.isdir(os.path.join(a_dir, name))]


def get_immediate_SubFileList(a_dir):
    '''
    Get the list of direct subFile included in "a_dir"
    
    Arguments:
        *a_dir*: python string
    '''
    return [name for name in os.listdir(a_dir)
            if os.path.isfile(os.path.join(a_dir, name))]
                
def findVariables(surfPath,variables=[]):
    '''
    Find a variable in a surface folder
    '''
    def findTypeField(surfPath,typeField):
        typeFields = []
        typePaths = []
        typeFieldAbsPath = os.path.abspath(os.path.join(surfPath,typeField))
        if os.path.exists(typeFieldAbsPath):
            typeFields = [f for f in os.listdir(typeFieldAbsPath) if os.path.isfile(os.path.join(typeFieldAbsPath,f))==True]
            typePaths = [os.path.join(typeFieldAbsPath,f) for f in typeFields]
        return typeFields, typePaths
        
    #find typeField if exist
    scalarFields, scalarPaths = findTypeField(surfPath,'scalarField')
    vectorFields, vectorPaths = findTypeField(surfPath,'vectorField')
    symmTenFields, symmTenPaths = findTypeField(surfPath,'symmTensorField')
    tensorFields, tensorPaths = findTypeField(surfPath,'tensorField')
    
    #concatenate the list and remove the unwanded variables
    allFields = scalarFields+vectorFields+symmTenFields+tensorFields
    allFieldsPath = scalarPaths+vectorPaths+symmTenPaths+tensorPaths    
    selectFields = []
    selectFieldsPath = []
    if len(variables)==0:
        selectFields = allFields
        selectFieldsPath = allFieldsPath
    else:
        for var in variables:
            if var in allFields:
                idx = allFields.index(var)
                selectFields.append(allFields[idx])
                selectFieldsPath.append(allFieldsPath[idx])
                
    return selectFields, selectFieldsPath
            

def parseFoamFile_sampledSurface(foamFile):
    '''
    Parse a foamFile generated by the OpenFOAM sample tool or sampling library.
    
    Note:
        * It's a primitiv parser, do not add header in your foamFile!
        * Inline comment are allowed only from line start. c++ comment style.
        * It's REALLY a primitive parser!!!
        
    Arguments:
        *foamFile*: python string
         Path of the foamFile.

    Returns:
        *output*: numpy array
         Data store in foamFile.
    '''
    output = []
    catchFirstNb = False
    istream = open(foamFile, 'r')
    for line in istream: 
        # This regex finds all numbers in a given string.
        # It can find floats and integers writen in normal mode (10000) or
        # with power of 10 (10e3).
        match = re.findall('[-+]?\d*\.?\d+e*[-+]?\d*', line)
        if (line.startswith('//')):
            pass
        if (catchFirstNb==False and len(match)==1):
            catchFirstNb = True
        elif (catchFirstNb==False and len(match)==2): #case for a constant scalar field
            catchFirstNb = True
            matchfloat = [float(nb) for nb in match]
            output.append(matchfloat[1])
        elif (catchFirstNb==False and len(match)>2): #case for a constant <type other than scalar> field
            catchFirstNb = True
            matchfloat = [float(nb) for nb in match]
            output.append(matchfloat)
        elif (catchFirstNb==True and len(match)>0):
            matchfloat = [float(nb) for nb in match]
            if len(matchfloat)==1:
                output.append(matchfloat[0])
            else:
                output.append(matchfloat)
        else:
            pass
    istream.close()
    return np.array(output)


def parseVTK_ugly_sampledSurface(vtkfile):
    '''
    Parse a VTK file generate by the surface sampling tool of OpenFOAM. The
    surface has N grid points and M triangles. The data stored at each grid
    points has a dimension D.
    
    Warnings: This is a VERY primitive and ugly parser!! the python-to-vtk
    binding should be used instead of the following shitty code! 
    Nevertheless, this shit works :-)!!
    
    Arguments:
        *vtkfile*: python string
         Path to the vtk file
         
    Returns:
        *points*: numpy array of shape (N,3)
         List of points composing the grid.
         
        *polygon*: numpy array of shape (M,3)
         List of triangles. Technically, this parser can return a List of any
         type of ploygon, e.g: triangle, square, pentagon...
 
        *pointData* numpy array of shape (N,D)
         List of data associate with each point of the grid.
    '''
    pointsOut = []
    polyOut = []
    pointDataOut = []
    
    istream = open(vtkfile, 'r')
    line = istream.readline()

    # catch the begin of the list of points
    # -------------------------------------
    catchLine = False
    while catchLine==False:
        if (line.startswith('DATASET POLYDATA')):
            catchLine = True
        line = istream.readline()
        
    # catch the number of points
    nbpoints = int(re.findall('[-+]?\d*\.?\d+e*[-+]?\d*', line)[0])
    pti = 0
    line = istream.readline()
    
    #store the points in pointsOut
    while (pti<nbpoints):
        match = re.findall('[-+]?\d*\.?\d+e*[-+]?\d*', line)
        pointsOut.append(match)
        line = istream.readline()
        pti = pti+1
    pointsOut = np.asarray(pointsOut,dtype=float)
    
    # catch the begin of the list of polygons and the number of polygon
    # -----------------------------------------------------------------
    catchLine = False
    nbpoly = 0
    while catchLine==False:
        if (line.startswith('POLYGONS')):
            catchLine = True
            nbpoly = int(re.findall('[-+]?\d*\.?\d+e*[-+]?\d*', line)[0])
        line = istream.readline()
    polyi = 0
    
    #store the polygons in polyOut
    while polyi<nbpoly:
        match = re.findall('[-+]?\d*\.?\d+e*[-+]?\d*', line)
        polyOut.append(match[1:])
        line = istream.readline()
        polyi = polyi+1
    polyOut = np.asarray(polyOut,dtype=float)
    
    # catch the begin of the list of point data
    # -----------------------------------------
    catchLine = False
    nbptdata = 0
    while catchLine==False:
        if (line.startswith('POINT_DATA')):
            catchLine = True
            nbptdata = int(re.findall('[-+]?\d*\.?\d+e*[-+]?\d*', line)[0])
        line = istream.readline()
    ptdatai = 0
    
    # jump the line starting with "FIELD attributes"
    line = istream.readline()
    
    # catch the dimension of point data and the number of point data
    match = re.findall('[-+]?\d*\.?\d+e*[-+]?\d*', line)
    dimptdata = int(match[0])
    line = istream.readline()
    
    #store the point data in pointDataOut
    if dimptdata==1:
        pointDataOut = re.findall('[-+]?\d*\.?\d+e*[-+]?\d*', line)
    else: 
        while ptdatai<nbptdata:
            match = re.findall('[-+]?\d*\.?\d+e*[-+]?\d*', line)
            pointDataOut.append(match)
            line = istream.readline()
            ptdatai = ptdatai+1
    pointDataOut = np.asarray(pointDataOut,dtype=float)
    
    istream.close()
    
    return pointsOut, polyOut, pointDataOut

    
def saveMeshToHDF5(faces,points,hdf5parser):
    '''
    '''
    gName = 'mesh'
    gMesh = hdf5parser.create_group(gName)

    gMesh.create_dataset('points',data=points)
    gMesh.create_dataset('faces',data=faces)
    
    

def saveTsToHDF5(time,varDict,hdf5parser):
    '''
    Save timestep "time" in "hdf5parser".
    
    Arguments
        *time*: python string.
        
        *varDict*:python dict.
         Dictonary with the variable name as key and data as data
         
        *hdf5parser*: HDF5 parser.
    '''
    gName = time
    gTs = hdf5parser.create_group(gName)
    gTs.create_dataset('time',data=float(time))
    for key in varDict:
        gTs.create_dataset(key,data=varDict[key])

        
def saveFoamFileSurfaceToHDF5(surfLocAbsPath,tsList,surfName,var,hdf5parser):
    '''
    Save foamFile surfaces in the HDF5 file.
    
    Arguments:
        *surfLocAbsPath*: python string.
         Location of the surfaces. This folder contains timesteps folders.
      
        *tsList*: python list of string.
     
        *surfName*: python string
         Name of the surface
      
        *hdf5parser*: hdf5 parser object (from module pyh5)
     
    Returns:
        none
    '''
    #save the mesh
    points = parseFoamFile_sampledSurface(os.path.join(surfLocAbsPath,tsList[0],surfName,'points'))
    faces = parseFoamFile_sampledSurface(os.path.join(surfLocAbsPath,tsList[0],surfName,'faces'))
    saveMeshToHDF5(faces[:,1:],points,hdf5parser)
    
    # loop through all timestep in tsList and save variables
    for ts in tsList:
        print('')
        print('for surface = '+surfName)
        print('timeStep = '+ts)
        # test if the surface exists in ts
        surfAbsPath = os.path.abspath(os.path.join(surfLocAbsPath,ts,surfName))
        if os.path.exists(surfAbsPath):
            # find variables to save according flag -vars
            selectFields, selectFieldsPath = findVariables(surfAbsPath,var)
            print('   field saved = '+str(selectFields)) 
            if len(selectFields)==0:
                pass
            else:
                # load variables in a dict
                selectDict = dict()
                for i in range(len(selectFields)):
                    key = selectFields[i]
                    data = parseFoamFile_sampledSurface(selectFieldsPath[i])
                    if len(data)==len(points):
                        pass
                    else:
                        if len(data.shape)==1: #scalar const field
                            data = data[0]*np.ones(len(points))
                        else:
                            data = data*np.ones(data.shape)
                    selectDict[key] = data
                saveTsToHDF5(ts,selectDict,hdf5parser)
        else:
            print('Surface "'+surfName+'" does not exist in timestep '+ts+'. Skip timestep '+ts)
        

def saveVtkSurfaceToHDF5(surfLocAbsPath,tsList,surfName,var,hdf5parser):
    '''
    Save vtk surfaces in the HDF5 file.
    
    Arguments:
        *surfLocAbsPath*: python string.
         Location of the surfaces. This folder contains timesteps folders.
      
        *tsList*: python list of string.
     
        *surfName*: python string
         Name of the surface
      
        *hdf5parser*: hdf5 parser object (from module pyh5)
     
    Returns:
        none
    '''    
    # loop through all timestep in tsList and save all variables
    surfNameVtk = surfName+'.vtk'
    for ts in tsList:
        print('')
        print('timeStep = '+ts)
        
        tsAbsPath = os.path.abspath(os.path.join(surfLocAbsPath,ts))
        allVtkList = get_immediate_SubFileList(tsAbsPath)
#        print('allVtkList = '+str(allVtkList))
        vtkList = [] 
        varList = []
        for vtk in allVtkList:
            surfStartIdx = vtk.find(surfNameVtk)
            #print(surfStartIdx)
            if surfStartIdx!=-1:
                varName = vtk[:surfStartIdx-1]
                vtkList.append(vtk)
                varList.append(varName)
#        print('vtkList = '+str(vtkList))
#        print('varList = '+str(varList))
        validVtkList = [] 
        validVarList = [] 
        if len(var)>0:      
            for i in range(len(var)):
                try:
                    idx = varList.index(var[i])
                    validVtkList.append(vtkList[idx])
                    validVarList.append(varList[idx])
                except:
                    pass
        else:
            validVtkList = vtkList
            validVarList = varList
        
        selectDict = dict()        
        for i,vtkf in enumerate(validVtkList):
            vkfPath = os.path.abspath(os.path.join(surfLocAbsPath,ts,vtkf))
            #save the mesh
            if (ts==tsList[0] and vtkf==validVtkList[0]):
                points, faces, data = parseVTK_ugly_sampledSurface(vkfPath)
                saveMeshToHDF5(faces,points,hdf5parser)
            points, faces, data = parseVTK_ugly_sampledSurface(vkfPath)
            selectDict[validVarList[i]] = data
        saveTsToHDF5(ts,selectDict,hdf5parser)
            
#=============================================================================#
# parser arguments
#=============================================================================#
parser = argparse.ArgumentParser(description='Convert an OpenFOAM surfaces in a HDF5 file. '
                                             'Be default, the script is launch in the surfaces '
                                             'folder. Use -surfLoc if started from an other location')

parser.add_argument('-loc',
                    dest='surfLoc',
                    type=str,
                    required=False,
                    default=os.getcwd(),
                    help='Path to the surfaces. The surfaces folder contains '
                         'a list of timestep. Default: execution path.'
                    )
parser.add_argument('-name',
                    dest='surfName',
                    type=str,
                    required=True,
                    help='Name of the surface. '
                    )
parser.add_argument('-format',
                    dest='surfFormat',
                    type=str,
                    required=True,
                    help='file format of the surface. choice: "foamFile", "vtk".'
                    )
parser.add_argument('-output',
                    dest='output',
                    type=str,
                    required=False,
                    default=None,
                    help='Name of the HDF5 output. The default name is "surfName.h5" '
                         'located in "OFcase/postProcessing/surfaces".'
                    )
parser.add_argument('-vars',
                    dest='vars',
                    type=str,
                    required=False,
                    default=[],
                    nargs='+',
                    help='Specify which variables to save in the HDF5. If not specified, all '
                         'available variables are saved.'
                    )
parser.add_argument('-overwrite',
                    dest="overwrite",
                    action="store_true",
                    default=False,
                    help='If the hdf5 file already exist, delete it and recreate it. '
                         'Default behavior: if the file already exists, nothing is done '
                         'and the execution is aborded.' 
                    )
args = parser.parse_args()


#=============================================================================#
# Main
#=============================================================================#
workingDir = os.getcwd()
  
print('Save surface "'+args.surfName+'"')
print('')

# Create the absolut path of surfLoc and check if it exists
surfLocAbsPath = os.path.abspath(args.surfLoc)
if os.path.exists(surfLocAbsPath):
    pass
else:
    sys.exit('The surface location "'+surfLocAbsPath+'" does not exist. Exit')  

# get the list of timestep, check if it is a number and sort them
tsListAll = get_immediate_SubDirList(surfLocAbsPath)
tsList = []
for ts in tsListAll:
    if is_number(ts)==True:
        tsList.append(ts)  
tsList.sort()

# define the absolut path of the HDF5 file
hdf5file = None
if args.output==None:
    hdf5file = os.path.join(surfLocAbsPath,args.surfName+'.h5')
else:
    hdf5file = os.path.join(surfLocAbsPath,args.output)

# save the surface in the HDF5.    
if args.overwrite==True and os.path.exists(hdf5file)==True:
    os.remove(hdf5file)

if os.path.exists(hdf5file)==False:
    h5w = h5py.File(hdf5file, 'w-')
    if args.surfFormat=='foamFile':
        saveFoamFileSurfaceToHDF5(surfLocAbsPath,
                                  tsList,
                                  args.surfName,
                                  args.vars,
                                  h5w)
    elif args.surfFormat=='vtk':
        saveVtkSurfaceToHDF5(surfLocAbsPath,
                             tsList,
                             args.surfName,
                             args.vars,
                             h5w)
    else:
        sys.exit('Wrong surface format. Exit.')        
    h5w.close()
else:
    sys.exit('the HDF5 file already exist. Exit.')

print('')
