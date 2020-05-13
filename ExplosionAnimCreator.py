# ExplosionAnimCreator

from maya import cmds
import sys
import maya.OpenMaya as OpenMaya
import maya.api.OpenMaya as om
import random
import math


class AnimExplode(object):

    def __init__(self):
        self.srcObject = None
        self.srcDagPath = None
        self.minArea = None
        self.maxArea = None
        self.getSelectedShaders = []

    '''
    select the object and record important information
    '''
    def selectTarget(self):
        result = cmds.ls(orderedSelection=True)
        if len(result) == 0:
            print 'Please select one object'
            return
        else:
            print 'result: %s' % (result)

        self.srcObject = result[0]

        # get the object
        selection = OpenMaya.MSelectionList()
        OpenMaya.MGlobal.getActiveSelectionList(selection)
        mDagPath = OpenMaya.MDagPath()
        selection.getDagPath(0, mDagPath)

        # record the DagPath
        self.srcDagPath = self.getSelectedDagPath()

        component = OpenMaya.MObject()
        polyIter = OpenMaya.MItMeshPolygon(self.srcDagPath, component)

        facesNum = polyIter.count()

        # get the area of current face
        self.minArea = self.getFaceArea(polyIter)
        self.maxArea = self.getFaceArea(polyIter)

        polyIter.next()

        # Iterate over each face
        for i in range(0, facesNum):
            tmpArea = self.getFaceArea(polyIter)
            if tmpArea <= self.minArea:
                self.minArea = tmpArea
            elif tmpArea > self.maxArea:
                self.maxArea = tmpArea

            polyIter.next()

        print 'self.minArea: %s' % (self.minArea)
        print 'self.maxArea: %s' % (self.maxArea)

    '''
    create instances by Geometry shape
    '''
    def createInstanceByGeometry(self, radius, center = [0.0, 0.0, 0.0]):

        result = cmds.ls(orderedSelection=True)[0]

        # create a group
        insGrpName = cmds.group(empty=True, name='mySphere_grp')

        # create a sphere
        #cmds.polySphere( n='mySphere', r=radius)

        self.createInstanceBasedOnFaceCenter(insGrpName, result)

    '''
    create instances at every face center
    '''
    def createInstanceBasedOnFaceCenter(self, grpName, src):
        mDagPath = self.srcDagPath

        component = OpenMaya.MObject()
        polyIter = OpenMaya.MItMeshPolygon(mDagPath, component)

        facesNum = polyIter.count()
        print facesNum

        for i in range(0, facesNum):
            instanceResult = cmds.instance(src, name=src + '_instance#')
            _center = polyIter.center(OpenMaya.MSpace.kWorld)
            cmds.move(_center[0], _center[1], _center[2], instanceResult)

            #scalingFactor = random.uniform(0.3, 1.0)
            #cmds.scale(scalingFactor, scalingFactor, scalingFactor, instanceResult)

            cmds.parent(instanceResult, grpName)

            print (float(i) / float(facesNum)) * 100
            polyIter.next()


    '''
    translate objects to the self.srcObject's pivot
    '''
    def translationToPivot(self):
        insGrpName = cmds.ls(selection=True)[0]
        cmds.select(cmds.listRelatives(insGrpName, children=True))

        selectionList = cmds.ls(selection=True, type='transform')

        #centers = self.faceCenter(self.srcDagPath)

        objNum = 0
        pivot = cmds.xform(self.srcObject, query=True, worldSpace=True, pivots=True)
        ori = OpenMaya.MVector(pivot[0], pivot[1], pivot[2])

        for objectName in selectionList:
            objNum += 1

            pos = cmds.xform(objectName, query=True, worldSpace=True, translation=True)
            v0 = OpenMaya.MVector(pos[0], pos[1], pos[2])
            #v1 = OpenMaya.MVector(centers[0], centers[1], centers[2])

            component = OpenMaya.MObject()
            polyIter = OpenMaya.MItMeshPolygon(self.srcDagPath, component)
            #points = OpenMaya.MPointArray()
            #polyIter.getPoints(points, OpenMaya.MSpace.kWorld)

            randID = -1

            tc = [float("inf")]
            t = [0.0]
            points = [None]*4
            rayDir = (ori - v0).normal()

            while not polyIter.isDone():
                i = polyIter.index()

                vertexCount = polyIter.polygonVertexCount()
                for i in range(0, vertexCount):
                    points[i] = polyIter.point(i, OpenMaya.MSpace.kWorld)

                normal = OpenMaya.MVector()
                polyIter.getNormal(normal, OpenMaya.MSpace.kWorld)
                if self.intersectRayWithSquare(ori, v0, points[0], points[1], points[3], normal, t) == True:
                    if (normal * rayDir) <= 0:
                        totalFactor = 0.0
                        placePos = OpenMaya.MVector(0.0, 0.0, 0.0)

                        for verNum in range(0, vertexCount-1):
                            vertFactor = random.uniform(0, (float(1)/vertexCount))
                            placePos = placePos + (OpenMaya.MVector(points[verNum]) * vertFactor)
                            totalFactor += vertFactor
                        placePos = placePos + (OpenMaya.MVector(points[vertexCount-1]) * (1 - totalFactor))

                        tc[0] = t[0]
                        randID = i
                        break
                    '''
                    if t[0]>0 and t[0] < tc[0]:
                        tc[0] = t[0]
                        randID = i
                    '''

                polyIter.next()

            print (float(objNum) / float(len(selectionList))) * 100
            if randID is not -1:
                #dir = (ori - v0).normal()
                #collPos = dir * tc[0]
                #cen = OpenMaya.MVector(centers[randID * 4 + 0], centers[randID * 4 + 1], centers[randID * 4 + 2])
                cmds.move(placePos[0], placePos[1], placePos[2], objectName)

    '''
    ray-square intersection
    '''
    def intersectRayWithSquare(self, r1, r2, _s1, _s2, _s3, _n, t):
        # 1.
        s1 = OpenMaya.MVector(_s1[0], _s1[1], _s1[2])
        s2 = OpenMaya.MVector(_s2[0], _s2[1], _s2[2])
        s3 = OpenMaya.MVector(_s3[0], _s3[1], _s3[2])
        ds21 = (s2 - s1)
        ds31 = (s3 - s1)

        # 2.
        dR = (r1 - r2).normal()

        ndotdR = _n * dR

        if abs(ndotdR) < 0.0000006:
            return False

        _t = (-_n) * (r1 - s1) / ndotdR
        t[0] = _t
        _M = r1 + (dR * _t)

        # 3.
        dMS1 = _M - s1
        u = dMS1 * ds21
        v = dMS1 * ds31

        # 4.
        return (u >= 0.0 and u <= (ds21*ds21) and v >= 0.0 and v <= (ds31*ds31))

    '''
    get DagPath from selected object
    '''
    def getSelectedDagPath(self):
        selection = OpenMaya.MSelectionList()
        OpenMaya.MGlobal.getActiveSelectionList(selection)
        _dagPath = OpenMaya.MDagPath()
        selection.getDagPath(0, _dagPath)
        return _dagPath

    '''
    return face area
    '''
    def getFaceArea(self, iter):
        face_area = OpenMaya.MScriptUtil()
        face_area_double = face_area.asDoublePtr()
        iter.getArea(face_area_double)
        return face_area.getDouble(face_area_double)

    '''
    record selected shaders
    '''
    def bakeShaders(self):
        shaders = cmds.ls(sl=True)
        # delete all elements
        del self.getSelectedShaders[:]
        for item in shaders:
            self.getSelectedShaders.append(item)
        print self.getSelectedShaders

    '''
    select a group, and assign shaders for its children
    '''
    def randomizeAssignShader(self):
        insGrpName = cmds.ls(selection=True)[0]
        cmds.select(cmds.listRelatives(insGrpName, children=True))

        selectedObjects = cmds.ls(selection=True, type='transform')

        shaderCount = len(self.getSelectedShaders)
        for item in selectedObjects:
            randNumber = random.random()
            roundNumber = math.floor(randNumber*(shaderCount))
            intNumber = int(roundNumber)
            cmds.select(item)
            shaderName = self.getSelectedShaders[intNumber]
            cmds.hyperShade(assign = shaderName)
        cmds.select(clear = True)


    '''
    select a group, and create explosion(sphere) animation for its children
    '''
    def createExplosionAnim(self):
        insGrpName = cmds.ls(selection=True)[0]
        radius = 25
        center = cmds.getAttr('%s.translate' % (insGrpName))[0]

        cmds.select(cmds.listRelatives(insGrpName, children=True))

        selectionList = cmds.ls(selection=True, type='transform')

        objNum = 0
        for objectName in selectionList:
            objNum = 1 + objNum
            # coords = cmds.getAttr('%s.translate' % (objectName))[0]
            trans = cmds.xform(objectName, query=True, worldSpace=True, translation=True)
            v0 = om.MVector(center)
            v1 = om.MVector(trans)

            # length = (v1 - v0).length()
            dir = (v1 - v0).normal()
            p = radius * dir

            cmds.move(p.x, p.y, p.z, objectName)

            print 'objectName: %s' % (p)

            startTime = cmds.playbackOptions(query=True, minTime=True)
            endTime = cmds.playbackOptions(query=True, maxTime=True)

            isDelay = objNum % 3
            self.keyFullTranslation(objectName, startTime, endTime, v1, p, isDelay, True)

    '''
    select a group, and create tail effect animation for its children
    '''
    def createTailEffectAnim(self):
        insGrpName = cmds.ls(selection=True)[0]
        cmds.select(cmds.listRelatives(insGrpName, children=True))
        selectionList = cmds.ls(selection=True, type='transform')

        objNum = 0
        for objectName in selectionList:
            objNum += 1
            if objNum % 25 == 0:
                startTime = cmds.playbackOptions(query=True, minTime=True)
                endTime = cmds.playbackOptions(query=True, maxTime=True)
                pos = cmds.xform(objectName, query=True, worldSpace=True, translation=True)
                des = OpenMaya.MVector(pos[0], pos[1], pos[2] - 5.0)
                self.keyFullTranslation(objectName, startTime, endTime, pos, des, 0, False)
                #self.randomizeAssignShader()

    '''
    select a group, and create rotation animation for the group
    '''
    def createRotationAimate(self, reverse):

        selectionList = cmds.ls(selection=True, type='transform')

        if len(selectionList) >= 1:

            startTime = cmds.playbackOptions(query=True, minTime=True)
            endTime = cmds.playbackOptions(query=True, maxTime=True)
            # print 'Selected items: %s' % (selectionList)

            for objectName in selectionList:
                self.keyFullRotation(objectName, startTime, endTime, 'rotateY', reverse)

    '''
    key translation animation for the object
    '''
    def keyFullTranslation(self, pObjectName, pStartTime, pEndTime, ori, tar, isDelay, isTangent):

        if isDelay == 1:
            pStartTime = 7 + pStartTime
        if isDelay == 2:
            pStartTime = 12 + pStartTime

        cmds.cutKey(pObjectName, time=(pStartTime, pEndTime), attribute='translateX')
        cmds.cutKey(pObjectName, time=(pStartTime, pEndTime), attribute='translateY')
        cmds.cutKey(pObjectName, time=(pStartTime, pEndTime), attribute='translateZ')
        print 'cutKey'

        cmds.setKeyframe(pObjectName, time=pStartTime, attribute='translateX', value=ori[0])
        cmds.setKeyframe(pObjectName, time=pStartTime, attribute='translateY', value=ori[1])
        cmds.setKeyframe(pObjectName, time=pStartTime, attribute='translateZ', value=ori[2])
        print 'setKeyframe1'

        cmds.setKeyframe(pObjectName, time=pEndTime, attribute='translateX', value=tar[0])
        cmds.setKeyframe(pObjectName, time=pEndTime, attribute='translateY', value=tar[1])
        cmds.setKeyframe(pObjectName, time=pEndTime, attribute='translateZ', value=tar[2])
        print 'setKeyframe2'

        if isTangent == True:
            cmds.selectKey(pObjectName, time=(pStartTime, pEndTime), attribute='translateX', keyframe=True)
            cmds.keyTangent(inTangentType='linear', outTangentType='linear')
            cmds.selectKey(pObjectName, time=(pStartTime, pEndTime), attribute='translateY', keyframe=True)
            cmds.keyTangent(inTangentType='linear', outTangentType='linear')
            cmds.selectKey(pObjectName, time=(pStartTime, pEndTime), attribute='translateZ', keyframe=True)
            cmds.keyTangent(inTangentType='linear', outTangentType='linear')
            print 'keyTangent'

    '''
    key rotation animation for the object
    '''
    def keyFullRotation(self, pObjectName, pStartTime, pEndTime, pTargetAttribute, reverse=False, isTangent=False):

        if reverse == False:
            startValue = 0
            endValue = 360
        else:
            startValue = 360
            endValue = 0

        cmds.cutKey(pObjectName, time=(pStartTime, pEndTime), attribute=pTargetAttribute)

        cmds.setKeyframe(pObjectName, time=pStartTime, attribute=pTargetAttribute, value=startValue)

        cmds.setKeyframe(pObjectName, time=pEndTime, attribute=pTargetAttribute, value=endValue)

        cmds.selectKey(pObjectName, time=(pStartTime, pEndTime), attribute=pTargetAttribute, keyframe=True)
        cmds.keyTangent(inTangentType='linear', outTangentType='linear')


    def explodeHumanFace(self):
        # get the source object
        result = cmds.ls(orderedSelection=True)[0]

        if len(result) == 0:
            print 'Please select one object'
            return
        else:
            print 'result: %s' % (result)

        # query the number of faces
        faces = cmds.polyEvaluate(result, f = True)
        triangles = cmds.polyEvaluate(result, t = True)

        selection = OpenMaya.MSelectionList()
        OpenMaya.MGlobal.getActiveSelectionList(selection)
        mDagPath = OpenMaya.MDagPath()
        selection.getDagPath(0, mDagPath)

        centers = self.faceCenter(mDagPath)

        for i in range(0, len(centers)/4):
            instanceResult = cmds.instance(self.srcObject, name=self.srcObject + '_instance#')

            cmds.move(centers[i*4], centers[i*4+1], centers[i*4+2], instanceResult)

    '''
    Iterate over faces, and get center and put them into a list
    '''
    def faceCenter(self, _dagpath):

        faceCenter = []

        component = OpenMaya.MObject()
        polyIter = OpenMaya.MItMeshPolygon(_dagpath, component)

        face_area = OpenMaya.MScriptUtil()
        face_area_double = face_area.asDoublePtr()

        while not polyIter.isDone():

            i = 0
            i = polyIter.index()
            faceInfo = [0]
            faceInfo[0] = ("The center point of face %s is:" %i)
            #print faceInfo[0]

            polyIter.getArea(face_area_double)
            _area = face_area.getDouble(face_area_double)

            center = polyIter.center(OpenMaya.MSpace.kWorld)
            point = [0.0, 0.0, 0.0, 0.0]
            point[0] = center.x
            point[1] = center.y
            point[2] = center.z
            point[3] = _area
            faceCenter += point

            polyIter.next()

        return faceCenter
