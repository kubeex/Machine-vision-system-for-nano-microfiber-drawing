import cv2
import numpy as np
import configparser
import ast
config = configparser.ConfigParser()
config.read('config.ini')
color = ast.literal_eval(config.get('style' , 'color'))
font = getattr(cv2, config.get('style' , 'font'))
def generateChArUcoBoard(squaresX, squaresY, filename=None):
    #definuje velikost A4 pri 300 dpi
    paperWidth, paperHeight = int(8.27 * 300), int(11.69 * 300)
    #velikost ctvercu a markeru
    squareLength = int((paperWidth-100) / squaresX)
    markerLength = int(squareLength * 0.7)
    #Vyber slovniku
    dict = cv2.aruco.DICT_6X6_250
    dictionary = cv2.aruco.getPredefinedDictionary(dict)
    #Vytvori desku
    board =cv2.aruco.CharucoBoard((squaresX, squaresY), squareLength, markerLength, dictionary)
    if filename is not None:
        #Vykresli desku
        img = board.generateImage((paperWidth, paperHeight))
        #Ulozi desku
        cv2.imwrite(filename, img)
        print("Board generated")

    return board
def charlibration(board,cap):
    #Vyber slovniku
    dict = cv2.aruco.DICT_6X6_250
    dictionary = cv2.aruco.getPredefinedDictionary(dict)
    charucoCorners = []
    charucoIds = []
    #Pokud je video otevreno
    while cap.isOpened():
        #Cte zaznam
        ret, frame = cap.read()
        # Detekce markeru
        corners, ids, _ = cv2.aruco.detectMarkers(frame, dictionary)
        # Pokud je nalezen aspon jeden marker --> len(corners) > 0 --> True
        if len(corners) > 0:
            ret, charuco_corners, charuco_ids = cv2.aruco.interpolateCornersCharuco(corners, ids, frame, board)
            # Pokud je deska nalezena(vic jak 15 rohů)
            if ret > 15:
                cv2.aruco.drawDetectedCornersCharuco(frame, charuco_corners,charuco_ids)
                #Vypise text ze deska byla nalezena
                cv2.putText(frame, 'Kalibracni vzor detekovan', (10, 50),font, 1, color, 2)
                #Pokud je stisknuta klavesa 0
                if cv2.waitKey(1) == ord('+'):

                    charucoCorners.append(charuco_corners)
                    charucoIds.append(charuco_ids)
                    #cv2.imwrite(f"frame{len(charucoCorners)}.jpg", frame)
                #Vykreslii detekovane rohy desky

            else:
                #Vypise text ze deska nebyla nalezena
                cv2.putText(frame, 'No charuco board detected', (10, 50),font, 1, color, 2)

        # Pokud neni nalezen zadny marker vypise text
        else:
            print("No obrazky detected")
            cv2.putText(frame, 'No obrazky detected', (10, 50),font, 1, color, 2)

        cv2.putText(frame, f'Pocet snimku{len(charucoCorners)}', (10, 100), font, 1, color, 2)
        #Zobrazeni vysledneho obrazku
        cv2.imshow('Calibration', frame)
        #Pokud je stisknuta klavesa + ukonci se program
        if cv2.waitKey(1) == ord('q'):
            print('pressed')
            break
    cap.release()
    cv2.destroyAllWindows()

    if len(charucoCorners) >2:
        print("Calibrating camera...")
        #Ziskani matice kamery
        h, w = frame.shape[:2]
        ret, mtx, dist,R,T = cv2.aruco.calibrateCameraCharuco(charucoCorners, charucoIds, board, (w,h),None,None)
        newmtx, roi = cv2.getOptimalNewCameraMatrix(mtx, dist, (w,h), 1, (w,h))
        # Ulozeni matice kamery, distorze a novy matice kamery
        np.savez('calibration.npz', mtx=mtx, dist=dist, newmtx=newmtx)
        print("Calibration computation complete!")
    else:
        print("Not enough calibration data")
    return

squaresX = ast.literal_eval(config.get('calibration' , 'squaresX'))
squaresY = ast.literal_eval(config.get('calibration' , 'squaresY'))
filename = config.get('calibration' , 'filename')
if filename == 'None':
    filename = None
else:
    filename = filename
board = generateChArUcoBoard(squaresX,squaresY, filename)
cap = cv2.VideoCapture(0)
charlibration(board,cap)