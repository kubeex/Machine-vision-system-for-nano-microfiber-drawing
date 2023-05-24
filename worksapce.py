import cv2
import numpy as np
import math
from support import sortptsClockwise, transformPoint
import configparser
import ast
#Nacteni dat z config souboru
try:
    config = configparser.ConfigParser()
    config.read('config.ini')
    workspaceIds =  ast.literal_eval(config.get('IDS' , 'workspaceIds'))
    RealMarkerSize = ast.literal_eval(config.get('markers' , 'realMarkerSize'))
    workspaceDict = getattr(cv2.aruco, config.get('markers', 'WorkspaceDictionary'))
    #Style
    color = ast.literal_eval(config.get('style' , 'color'))
    font = getattr(cv2, config.get('style' , 'font'))
except:
    print("Error while reading config file")
    exit()
try:
    #Nacte data z kalibrace
    data = np.load('calibration.npz')
    mtx, newmtx, dist = [data[i] for i in ('mtx', 'newmtx', 'dist')]
except:
    print("Error while reading calibration data")
    exit()

def GetConversionCoeficient(MultipleMarkersCorners, MarkerSize,TransformationMatrix):
    obvod_list = []
    for corners in MultipleMarkersCorners:
        #trasformace souradnic rohu markeru
        transformed_corners = [transformPoint(p, TransformationMatrix) for p in corners]
        tl, tr, br, bl = transformed_corners
        #vypocet delek stran markeru
        tltr = math.hypot(tl[0] - tr[0], tl[1] - tr[1])
        trbr = math.hypot(tr[0] - br[0], tr[1] - br[1])
        blbr = math.hypot(bl[0] - br[0], bl[1] - br[1])
        bltl = math.hypot(bl[0] - tl[0], bl[1] - tl[1])
        #vypocet obvodu markeru
        obvod = tltr + trbr + blbr + bltl
        obvod_list.append(obvod)
    avrg_obvod = sum(obvod_list) / len(obvod_list)
    a = avrg_obvod / 4
    prevod = MarkerSize / a # prevod z pixelu na mm [mm/px]
    return prevod

def workspace(frame):
    #Pro pripad ze neni detekovan zadny marker --> vraci None
    warpedFrame = None
    warpedCroppedFrame = None
    conversion = 0
    #Velikost obrazu
    hh, ww = frame.shape[:2]
    #Detekovani Aruco markeru
    arucoDict = cv2.aruco.getPredefinedDictionary(workspaceDict) #Nahraje directory s pouzivanyma markermaa
    corners, ids, rejected = cv2.aruco.detectMarkers(frame, arucoDict)     #Samotna detekce markeru
    raw_frame = frame.copy()
    #Pokud je nalezen aspon jeden marker --> len(corners) > 0 --> True
    tvecs = []
    MarkerCenters = []
    MarkerIds = []
    MarkerCorners = []
    if len(corners)>0:
        cv2.aruco.drawDetectedMarkers(frame, corners, ids)
        for markerCorners, markerId in zip(corners,ids):
            if markerId in workspaceIds:
                markerCorners = markerCorners.reshape((4, 2))
                markerId = markerId[0]
                tl, tr, br, bl = markerCorners
                #cors = sortptsClockwise(np.array([tl, tr, br, bl]))
                #bottom_right,top_left
                br = (int(br[0]), int(br[1]))
                tl = (int(tl[0]), int(tl[1]))
                #souradnice stredu markeru
                CX = (tl[0] + br[0]) / 2
                CY = (tl[1] + br[1]) / 2
                # Ulozeni dat
                MarkerCenters.append([CX, CY])
                MarkerIds.append(markerId)
                MarkerCorners.append(markerCorners)
        sortedCenters = [x for _, x in sorted(zip(MarkerIds, MarkerCenters), key=lambda pair: pair[0])]
        sortedCorners = [x for _, x in sorted(zip(ids, corners), key=lambda pair: pair[0])]
        # Ohadne posunuti a rotaci kazdeho markeru vuci kamere
        for i in range(0, len(ids)):
            rvec, tvec, markerPoints = cv2.aruco.estimatePoseSingleMarkers(sortedCorners[i], 24, mtx, dist)
            tvecs.append(tvec)
            # Draw Axis
            cv2.drawFrameAxes(frame, mtx, dist, rvec, tvec, 30, 2)
    else:
        print('Pracovní prostor nenalezen.')
        cv2.putText(frame, "No obrazky found.", (10, 30), font, 0.5, color, 2)

    #Pokud je detekovano vice jak 3 body ...vytvori prac prostor tvaru obdelnik dany 4ma body
    if len(MarkerCenters)>3:
        # Usporada list bodu ve smeru hodinovych rucicek od tl po bl
        boundaryPoints = sortptsClockwise(np.array(MarkerCenters)) #Seradi rohu tl, tr, br, bl ve smeru hod rucicek
        corners_tvecs = []
        for corner in boundaryPoints:
            # nalezne index odpovidajiciho tvec v sortedcenters
            i = np.where((sortedCenters == corner).all(axis=1))[0][0]
            # append odpovídající tvec do corners_tvecs
            corners_tvecs.append(tvecs[i])

        #Vykresli ohraniceni kolem pracovni plochy a popise body na puvodnim obrazku
        a = np.array(boundaryPoints).reshape((-1,1,2)).astype(np.int32)
        cv2.drawContours(frame,[a], 0, color, 2)
        #popise body na puvodnim  obrazku
        labels = ['tl', 'tr', 'br', 'bl']
        for corner, label in zip(boundaryPoints, labels):
            cv2.circle(frame, (int(corner[0]), int(corner[1])), radius=0, color=(0,0,250), thickness=3)
            cv2.putText(frame, label, (int(corner[0] + 20), int(corner[1])), font, 0.8, (0,0,250), 2)
        # Vypocet delky stran
        #sirka obdelniku
        blbr = np.linalg.norm(corners_tvecs[1] - corners_tvecs[0])
        #vyska obelniku
        brtr = np.linalg.norm(corners_tvecs[2] - corners_tvecs[1])
        aspect_ratio = blbr / brtr  # pomer stran:sirka/vyska

        new_width = int(ww) #sirka transformovaneho a oriznteho obrazku
        new_height = int(new_width / aspect_ratio) #vyska transformovaneho a oriznteho obrazku
        # vstupni body pro transformaci
        input = np.float32(boundaryPoints[0:4])
        # Transformuje a orizne obrazek tak aby byl zobrazeny pouze pracovni plocha z ptacich pohledu
        #vystupni body pro transformaci
        output = np.float32([[0, 0], [new_width, 0], [new_width, new_height], [0, new_height]])
        matrix = cv2.getPerspectiveTransform(input, output)
        warpedCroppedFrame = cv2.warpPerspective(raw_frame, matrix, (new_width, new_height),cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
        #Funkce pro vypocet prevodu pixelu na mm viz. funkce
        conversion = GetConversionCoeficient(MarkerCorners,RealMarkerSize,matrix)


        # Transformuje obrazek do ptaciho pohledu pomoci transformacni matice ziskane ze 4 viditelnych ArUco markeru
        koef =  0.5
        offset = 50
        output = np.float32([[0+offset, 0+offset], [ww*koef, 0+offset], [ww*koef, ww*koef/aspect_ratio], [0+offset, ww*koef/aspect_ratio]])
        matrix = cv2.getPerspectiveTransform(input,output)
        warpedFrame = cv2.warpPerspective(frame, matrix, (ww, hh), cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,borderValue=(0, 0, 0))
    #Konec funkce
    return warpedCroppedFrame,frame,conversion, warpedFrame
