# Step 1. 圖層、函式及變數設定
route = 672
direction = 0

# 函式:製作圖層屬性欄位
def add_fld(output_lyr):
    route = QgsField('route', QVariant.String)
    direction_field = QgsField('direction', QVariant.Int)
    start_stp = QgsField('start_stop',QVariant.Int)
    stop_info = QgsField('Stops',QVariant.String)
    
    output_lyr.dataProvider().addAttributes([route,
                                             direction_field,
                                             start_stp,
                                             stop_info])
    output_lyr.updateFields()
    
    return output_lyr 

# 函式:輸入屬性至屬性欄位
def insert_fld(output_lyr, direction, key_list_elem, feature_name, start_pnt, end_pnt):
    output_lyr.startEditing()
    for ftr in output_lyr.getFeatures():
        output_lyr.changeAttributeValue(ftr.id(), 3, route)
        output_lyr.changeAttributeValue(ftr.id(), 4, direction)
        output_lyr.changeAttributeValue(ftr.id(), 5, int(key_list_elem))
        output_lyr.changeAttributeValue(ftr.id(), 6, feature_name)
    output_lyr.commitChanges() 

# 從圖層名稱取得圖層物件
shape_lyr = QgsProject.instance().mapLayersByName('672_fullShape_2')[0]
stop_lyr_0 = QgsProject.instance().mapLayersByName('672-0_seq_raw')[0]

# Step 2. 爆炸(explode)路線圖層
network_ex = processing.run("native:explodelines",
                    {"INPUT": shape_lyr,
                     "OUTPUT":"memory:exploded"
                    })
QgsProject.instance().addMapLayer(network_ex['OUTPUT'])


# Step 3. 將站點位移置圖層至線型圖層上
snapped = processing.run("qgis:snapgeometries",
                         {'INPUT':stop_lyr_0,
                          'REFERENCE_LAYER':shape_lyr,
                          'TOLERANCE':0.0002,
                          'BEHAVIOR':1,
                          'OUTPUT':'memory:snapped'
                         })
snapped_stop_lyr = snapped['OUTPUT']
QgsProject.instance().addMapLayer(snapped_stop_lyr)


# Step 4. 製作站路段

# Step 4.1: 從站點圖層取得各站座標
stop_dict = {}
for ftr in snapped_stop_lyr.getFeatures():
    stop_dict[ ftr['StopSequen'] ] = (ftr['Lat'], ftr['Lon'])
    
    
#Step 4.2: 使用最短路徑(Shortest path)製作站路段，並儲存圖徵存於segment_list
segment_list = {}

stop_dict_sort = {k: v for k, v in sorted(stop_dict.items(), key=lambda item: item[0])}
key_list = list(stop_dict_sort.keys()) 

for i in range(len(key_list)):
    if i < len(stop_dict_sort.keys())-1:
        #print('processing shortest path station {} to {}'.format(i, i+1))
        feature_name = '{}_{}'.format(key_list[i],key_list[i+1])
        path = processing.run("native:shortestpathpointtopoint",
                              {"INPUT": network_ex['OUTPUT'],
                               "STRATEGY":0,
                               "START_POINT":"{},{}".format(stop_dict_sort[key_list[i]][1],stop_dict_sort[key_list[i]][0]),
                               "END_POINT":"{},{}".format(stop_dict_sort[key_list[i+1]][1],stop_dict_sort[key_list[i+1]][0]),
                               "OUTPUT":'memory:{}'.format(feature_name),
                               "TOLERANCE":0
                              }

        )
        #QgsProject.instance().addMapLayer(path['OUTPUT'])
        
        ## Add Fields
        output_lyr = path['OUTPUT']
        output_lyr = add_fld(output_lyr)
        
        ## Insert value into added fields
        start_loc = QgsPointXY(stop_dict_sort[key_list[i]][1], stop_dict_sort[key_list[i]][0])
        end_loc = QgsPointXY(stop_dict_sort[key_list[i+1]][1],stop_dict_sort[key_list[i+1]][0])
        insert_fld(output_lyr, direction, key_list[i], feature_name, start_loc, end_loc)
        segment_list[feature_name] = output_lyr
        
#Step 4.3: 將各路段圖徵合併
inputCRS = 'EPSG:4326'
shape_output = QgsVectorLayer('Multilinestring?crs={}'.format(inputCRS),
                   'result_{}_{}'.format(route, direction), 
                   'memory')
input_fields = None
features = []
for k,v in segment_list.items():
    if input_fields == None:
        input_fields = v.fields()
    for ftr in v.getFeatures():
        features.append(ftr)
        
dp = shape_output.dataProvider()
dp.addAttributes(input_fields)
dp.addFeatures(features)
shape_output.updateFields()

QgsProject.instance().addMapLayer(shape_output)

print('{}路線、方向{}處理完畢'.format(route, direction))