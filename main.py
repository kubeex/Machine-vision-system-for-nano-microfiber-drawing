import cv2
import numpy as np
import math
import configparser
from support import sortptsClockwise, ShowSmallCoordinates, ShowCoordinates,DrawCoordinateSystemSymbol
from worksapce import workspace
import ast
import json
import time
import os
#Nacte data pro undisort
try:
    data = np.load('calibration.npz')
    mtx, newmtx, dist = [data[i] for i in ('mtx', 'newmtx', 'dist')]
except:
    print("Error reading calibration file")
    exit()
#Nacteni dat z config souboru
config = configparser.ConfigParser()
try:
    config.read('config.ini')
    capInt = int(config.get('camera', 'cameraId')) #camera
    objectIds =  ast.literal_eval(config.get('IDS' , 'objectIds'))      #Ids desek
    reservoirIds = ast.literal_eval(config.get('IDS' , 'reservoirIds')) #Ids rezervoaru
    objectsDict =getattr(cv2.aruco, config.get('markers', 'ObjectsDictionary')) #slovnik desek a rezervoaru
except:
    print("Error reading config file")
    exit()
#style
color = ast.literal_eval(config.get('style' , 'color'))
font = getattr(cv2, config.get('style' , 'font'))
def TransformToRealCoordiantes(point,origin,prevod):
    X = round(point[0]*prevod,2)
    Y = round((origin[1] - point[1])*prevod,2)
    return [X,Y]

prev_frame_time = 0
new_frame_time = 0
if __name__ == "__main__":
    #Získání videa z kamery
    cap = cv2.VideoCapture(capInt)
    #Dokud je zaznamenávání spuštěno:
    while cap.isOpened():
        #nacteni snimku
        ret, frame = cap.read()
        #odstraneni distorzice kamery
        frame = cv2.undistort(frame, mtx, dist, None, newmtx)
        #Získání snímků z funkce workspace
        warpedCroppedFrame, wholeFrame, prevod, warped = workspace(frame)
        #Zobrazí původní upravený snímek
        cv2.imshow('Zaznam z kamery', wholeFrame)

        #if warped is not None:
        #   cv2.imshow('Warped Image', warped)
        if warpedCroppedFrame is not None:
            frame = warpedCroppedFrame
            raw_frame = frame.copy()

            hh, ww = frame.shape[:2]
            origin = (0,hh)

            # Detekovani Aruco markeru
            arucoDict = cv2.aruco.getPredefinedDictionary(objectsDict)  # Nahraje directory s pouzivanyma markermaa
            corners, ids, rejected = cv2.aruco.detectMarkers(frame, arucoDict)  # Samotna detekce markeru
            # Pokud je nalezen aspon jeden marker --> len(corners) > 0 --> True
            # Dostaneme MarkerCenters, MarkerIds, MarkerCorners
            MarkerCenters = []
            MarkerIds = []
            MarkerCorners = []
            reservoirs = []
            boards = []
            boardIDs = []
            if len(corners) > 0:
                for markerCorners, markerId in zip(corners, ids):
                    if markerId in objectIds or markerId in reservoirIds:
                        markerCorners = markerCorners.reshape((4, 2))
                        tl, tr, br, bl = markerCorners
                        cors = sortptsClockwise(np.array([tl, tr, br, bl]))
                        # bottom_right,top_left
                        br = (int(br[0]), int(br[1]))
                        tl = (int(tl[0]), int(tl[1]))
                        # souradnice stredu markeru
                        CX = (tl[0] + br[0]) / 2
                        CY = (tl[1] + br[1]) / 2

                        if markerId[0] in reservoirIds:
                            # Ulozeni informaci o rezervoaru do slovniku a pak do seznamu rezervoaru
                            dct = {"center": [CX, CY],
                                   "id": int(markerId[0])}
                            reservoirs.append(dct)
                            # Nakresleni kontury rezervoaru, vypise ID rezervoaru a nakresli jeho stred
                            cv2.circle(frame, (int(CX), int(CY)), 5, (0, 0, 255), -1)
                            cv2.putText(frame, f"ID:{markerId[0]}",  (int(CX), int(CY)),font, 0.5, (0, 0, 250), 2)
                            a = np.array(markerCorners).reshape((-1, 1, 2)).astype(np.int32)
                            cv2.drawContours(frame, [a], 0, color, 2)
                        else:
                            Marker

                            Centers.append([CX, CY])
                            MarkerIds.append(markerId[0])
                            MarkerCorners.append(cors)


                # Detekce kontur uvnitr pracovni plochy
                # Zmeni snimek na cerno bily
                imgrey = cv2.cvtColor(raw_frame, cv2.COLOR_BGR2GRAY)
                #Tresholding cernobileho snimku
                ret, thresh = cv2.threshold(imgrey, 110, 255, 0)
                #Nalezne kontury
                contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                #cv2.drawContours(frame, contours, -1, (0, 255, 0), 3)

                # Nalezne nejvyssi kontury pracovni plochy
                highestParentContours = []
                if hierarchy is not None:
                    hierarchy = hierarchy[0]
                    for i in range(len(contours)):

                        if hierarchy[i][3] == -1:
                            highestParentContours.append(i)
                        else:
                            continue
                if len(contours) > 0 and len(MarkerCenters)>0:
                    parentContours = []
                    corespondingMarkers = []
                    #Nalezne vsechny kontury okolo ArUco markeru
                    for i in range(len(contours)):
                        for j in range(len(MarkerCenters)):
                            if cv2.pointPolygonTest(contours[i], tuple(MarkerCenters[j]), False) >= 0:
                                parentContours.append(hierarchy[i][3])
                                corespondingMarkers.append(MarkerIds[j])
                                #cv2.drawContours(frame, contours, i, (0, 0, 255), 3)
                                break
                            else:
                                continue
                    # Nalezne nejvyssi rodice ArUco markeru, uvnitr pracovni plochy
                    markerParentContourIds = []
                    conturedMarkerIds = []
                    for i, id in zip(parentContours, corespondingMarkers):
                        if hierarchy[i][3] in highestParentContours:
                            if i != -1:
                                markerParentContourIds.append(i)
                                conturedMarkerIds.append(id)
                        else:
                            continue

                    # Nakresli kontury nejvyssiho rodice ArUco markeru
                    if markerParentContourIds != []:
                        for i,marker_id in zip(markerParentContourIds, conturedMarkerIds):
                            #aproximace kontury
                            #cv2.drawContours(frame, contours, i, (0, 255, 255), 3)
                            approx = cv2.approxPolyDP(contours[i], 0.04 * cv2.arcLength(contours[i], True), True)
                            #Pokud je kontura(okolo ArUco markeru) 4-uhelnikem --> jde o desku
                            if len(approx) == 4:
                                rect = cv2.minAreaRect(contours[i])
                                box = cv2.boxPoints(rect)
                                box = np.int0(box)
                                center = np.mean(box, axis=0)
                                index = MarkerIds.index(marker_id)
                                markerCenter = MarkerCenters[index]
                                def distance(p1, p2):
                                    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)
                                # Determine midpoint between two points
                                def midpoint(p1, p2):
                                    return [(p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2]
                                # Spocita velikost stran obdelniku
                                a = distance(box[0], box[1])
                                b = distance(box[1], box[2])

                                # Zjisti, ktera strana je delsi
                                if a < b:
                                    center1 = midpoint(box[0], box[1])
                                    center2 = midpoint(box[2], box[3])
                                else:
                                    center1 = midpoint(box[1], box[2])
                                    center2 = midpoint(box[3], box[0])

                                #Spocta vzdalenost stredu stran od stredu markeru
                                c1c = distance(center1, markerCenter)
                                c2c = distance(center2, markerCenter)
                                #porovna vzdalenost stredu stran od stredu markeru
                                if c1c < c2c:
                                    start_point = center1
                                    end_point = center2
                                else:
                                    start_point = center2
                                    end_point = center1
                                # Ulozeni informaci o desce do slovniku
                                dct = {"start_point": start_point,
                                       "end_point": end_point,
                                       "marker_id": marker_id,
                                       "marker_center": markerCenter,
                                       "box": box}
                                # Ulozeni informaci o desce do seznamu desek
                                boards.append(dct)
                                boardIDs.append(marker_id)

                                # # Nakresleni kontury desky
                                cv2.drawContours(frame, [box], 0, (0, 255, 0), 2)
                                # # vypise ID desky
                                cv2.putText(frame, f"ID:{marker_id}", (int(center[0]), int(center[1])),cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                                # # Vykresli startovaci a koncovy bod
                                cv2.circle(frame, (int(start_point[0]), int(start_point[1])), 5, (0, 0, 255), -1)
                                cv2.circle(frame, (int(end_point[0]), int(end_point[1])), 5, (0, 255, 0), -1)

                            else:
                                cv2.drawContours(frame, contours, i, (0, 0, 255), 3)
            else:
                pass

            coupleIDs = []
            singleIDs = []
            couples = []
            # Pokud je stisknuta klavesa s

            savedframe = frame.copy()

            # Pokud jsou nalezeny desky
            if boards != []:
                if len(boards) >1:
                    #print(f"Found {len(boards)} boards")
                    boardIDs = list(set(boardIDs))
                    i = 0
                    # Rozdeleni desek na dvojice a jednotlive desky
                    for id in boardIDs:
                        #pokud je ID sude --> partner je ID + 1
                        if id % 2 == 0:
                            partner = id + 1
                        #pokud je ID liche --> partner je ID - 1
                        else:
                            partner = id - 1
                        # Pokud je nalezen partner v boardIDs
                        if partner in boardIDs:
                            couple  = tuple(sorted([id, partner]))
                            # Pokud dvojice desek jeste neni v seznamu dvojic
                            if couple not in coupleIDs:
                                #prida dvojici do seznamu dvojic
                                coupleIDs.append(couple)
                        # Pokud neni nalezen partner v boardIDs
                        # prida ID desky do seznamu single desek
                        elif id not in singleIDs:
                            singleIDs.append(id)


                # Ziskani informaci o dvojici desek ze seznamu desek, prostrednictvim ID desek
                # Pokud je nalezena alespon dvojice desek
                if len(coupleIDs) > 0:
                    #print(f"Found {len(coupleIDs)} couples")
                    for couple in coupleIDs:
                        for board in boards:
                            # Pokud je ID desky v dvojici stejne jako ID desky v seznamu desek jde o desku z dvojice
                            if board["marker_id"] == couple[0]:
                                board1 = board
                            elif board["marker_id"] == couple[1]:
                                board2 = board
                        # Prevod startovacich a koncovych bodu desek z pixelu do realnych souradnic
                        start_point1= TransformToRealCoordiantes(board1["start_point"], origin, prevod)
                        start_point2 = TransformToRealCoordiantes(board2["start_point"], origin, prevod)
                        end_point1 = TransformToRealCoordiantes(board1["end_point"], origin, prevod)
                        end_point2 = TransformToRealCoordiantes(board2["end_point"], origin, prevod)

                        ShowSmallCoordinates(savedframe,board1["start_point"],origin,prevod)
                        ShowSmallCoordinates(savedframe, board1["end_point"], origin, prevod)
                        ShowSmallCoordinates(savedframe, board2["start_point"], origin, prevod)
                        ShowSmallCoordinates(savedframe, board2["end_point"], origin, prevod)
                        # Ulozeni informaci o dvojici desek do slovniku a pak do seznamu dvojic desek
                        coupleDict = {
                            "board1": {
                                "start_point":start_point1,
                                "end_point": end_point1,
                                "id": int(board1["marker_id"]),
                            },
                            "board2": {
                                "start_point": start_point2,
                                "end_point":end_point2,
                                "id": int(board2["marker_id"]),
                            }
                        }
                        couples.append(coupleDict)


                else:
                    print("No couples found")
                # Pokud jsou nalezeny desky, ktere nejsou soucasti dvojice
                if len(singleIDs) > 0:
                   print(f"No partner found for these boards: {singleIDs}")
            else:
                print("No boards found")

            # Pokud jsou nalezeny rezervoary
            if reservoirs != []:
                #print(f"Found {len(reservoirs)} reservoirs")
                for reservoir in reservoirs:
                    # Prevod stredu rezervoaru z pixelu do realnych souradnic
                    ShowSmallCoordinates(savedframe, reservoir["center"], origin, prevod)
                    reservoir["center"] = TransformToRealCoordiantes(reservoir["center"], origin, prevod)



            # Ulozeni infromaci o rezervoarech do slovniku
            data = {
                        "couples": couples,
                        "reservoirs": reservoirs
                    }
            if cv2.waitKey(1) & 0xFF == ord('s'):
                with open('data.json', 'w') as json_file:
                    json.dump(data, json_file, indent=4)
                DrawCoordinateSystemSymbol(savedframe)
                cv2.putText(savedframe, f"Desky:{len(boards)}", (10, 60), font, 0.8, color, 2)
                cv2.putText(savedframe, f"Pary:{len(couples)}", (10, 30), font, 0.8, color, 2)
                cv2.putText(savedframe, f"Bez dvojice:{singleIDs}", (10, 90), font, 0.8, color, 2)
                cv2.imshow('Ulozeny snimek', savedframe)
                print("Saved")
            else:
                pass

            #frame = cv2.resize(frame, (0,0), fx=1.5, fy=1.5)
            cv2.putText(frame, f"Sirka:{int(ww * prevod)}", (10, 30), font, 0.8, color, 2)
            cv2.putText(frame, f"Vyska:{int(hh * prevod)}", (10, 60), font, 0.8, color, 2)
            cv2.putText(frame, f"Desky:{len(boards)}", (10, 120), font, 0.8, color, 2)
            cv2.putText(frame, f"Pary:{len(couples)}", (10, 90), font, 0.8, color, 2)
            # cv2.putText(frame, f"Singles:{singleIDs}", (10, 150), font, 0.8, color, 2)
            #cv2.aruco.drawDetectedMarkers(frame, corners, ids)

            new_frame_time = time.time()
            fps = 1 / (new_frame_time - prev_frame_time)
            prev_frame_time = new_frame_time
            fps = int(fps)
            cv2.putText(frame, f"FPS:{fps}", (ww-100, 30), font, 0.8, color, 2)
            cv2.imshow('Rotatated&Cropped', frame)

            #Ukonci cyklus
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
cap.release()
cv2.destroyAllWindows()

