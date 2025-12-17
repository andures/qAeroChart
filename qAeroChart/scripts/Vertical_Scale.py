'''
Vertical Scale
'''
myglobals = set(globals().keys())

# Parameters all need to be in meters
offset = -50


#map_srid
map_srid = iface.mapCanvas().mapSettings().destinationCrs().authid()


''' Creation Vertical Scale '''
# List of fields 
vyField = []
vyField.append(QgsField( 'id', QVariant.String, len=255))
vyField.append(QgsField( 'symbol', QVariant.String, len=25))

#Create memory layer
v_layer = QgsVectorLayer("Linestring?crs="+map_srid, "Vertical Scale", "memory")
v_layer.dataProvider().addAttributes(vyField)
v_layer.updateFields()
#v_layer.setDefaultValueDefinition(v_layer.fields().lookupField('id'), default_val1)

layer = iface.activeLayer()
selection = layer.selectedFeatures()
geom=selection[0].geometry().asPolyline()
start_point = QgsPoint(geom[0])
end_point = QgsPoint(geom[-1])
angle=start_point.azimuth(end_point)
print ("angle:",angle)

#Change style of layer 
v_layer.renderer().symbol().setColor(QColor("red"))
v_layer.renderer().symbol().setWidth(0.25)
v_layer.triggerRepaint()


# Calculate points 
basepoint = start_point.project(offset,angle-90)
print (basepoint)

# meter scale 
mslist = []
melist = []
for i in range (0,101,25):
    ms_point = basepoint.project(i*10,angle)
    me_point = ms_point.project(15,angle+90)
    mslist.append(ms_point)
    melist.append(me_point)
    
#print (mslist)
#print (melist)

baseProfileLine= mslist
lineFeat = QgsFeature()
lineFeat.setGeometry(QgsGeometry.fromPolyline(baseProfileLine))
lineFeat.setAttributes([6,"profile"])
v_layer.dataProvider().addFeatures( [lineFeat] )

for i in range (0,len(mslist)):
    vline = []
    vline.append(mslist[i])
    vline.append(melist[i])
    lineFeat = QgsFeature()
    lineFeat.setGeometry(QgsGeometry.fromPolyline(vline))
    lineFeat.setAttributes([6,"profile"])
    v_layer.dataProvider().addFeatures( [lineFeat] )
    
# ft scale 
fslist = []
felist = []
for i in range (0,301,50):
    print (i*.3048)
    fs_point = basepoint.project((i*.3048)*10,angle)
    fe_point = fs_point.project(15,angle-90)
    fslist.append(fs_point)
    felist.append(fe_point)
    
print (fslist)
print (felist)

for i in range (0,len(fslist)):
    vline = []
    vline.append(fslist[i])
    vline.append(felist[i])
    lineFeat = QgsFeature()
    lineFeat.setGeometry(QgsGeometry.fromPolyline(vline))
    lineFeat.setAttributes([7,"profile"])
    v_layer.dataProvider().addFeatures( [lineFeat] )

lineFeat = QgsFeature()
vline = []
vline.append(mslist[-1])
vline.append(fslist[-1])
lineFeat.setGeometry(QgsGeometry.fromPolyline(vline))
lineFeat.setAttributes([8,"profile"])
v_layer.dataProvider().addFeatures( [lineFeat] )



''' Add layers'''
QgsProject.instance().addMapLayers([v_layer])


iface.messageBar().pushMessage("QPANSOPY:", "Finished Creating Layer", level=Qgis.Success)

set(globals().keys()).difference(myglobals)

for g in set(globals().keys()).difference(myglobals):
    if g != 'myglobals':
        del globals()[g]