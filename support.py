import cv2
import numpy as np
import time
import configparser
import ast
config = configparser.ConfigParser()
config.read('config.ini')
#Style
color = ast.literal_eval(config.get('style' , 'color'))
font = getattr(cv2, config.get('style' , 'font'))
objectsDict =getattr(cv2.aruco, config.get('markers', 'ObjectsDictionary')) #slovnik desek a rezervoaru
workspaceDict = getattr(cv2.aruco, config.get('markers', 'WorkspaceDictionary')) #slovnik pracovnich plochy
def generate_markers(dict,number_of_markers):
    dictionary = cv2.aruco.getPredefinedDictionary(dict)
    for n in range(number_of_markers):
        marker = cv2.aruco.generateImageMarker(dictionary, n, 200, 0.5)
        cv2.imwrite(f"markers/marker{n}.png", marker);
def now():
    t = time.localtime()
    current_time = time.strftime("%H:%M:%S", t)
    return current_time

def sortptsClockwise(A):
    from scipy.spatial import distance
    # Usporada body podle Y souradnice
    sortedAc2 = A[np.argsort(A[:,1]),:]
    # Ziska 2 horni a 2 dolni body
    top2 = sortedAc2[0:2,:]
    bottom2 = sortedAc2[2:,:]
    #Usporada vrchni body podle X souradnice na leve a prave
    sortedtop2c1 = top2[np.argsort(top2[:,0]),:]
    top_left = sortedtop2c1[0,:]
    #Pouzije levy horni bod jako pivot a vypocita vzdalenost od boduu na spodni strane a tak ziska spodni pravy a levy bod
    sqdists = distance.cdist(top_left[None], bottom2, 'sqeuclidean')
    rest2 = bottom2[np.argsort(np.max(sqdists,0))[::-1],:]
    return np.concatenate((sortedtop2c1,rest2),axis =0)

def transformPoint(point, matrix):
    px = (matrix[0][0] * point[0] + matrix[0][1] * point[1] + matrix[0][2]) / ((matrix[2][0] * point[0] + matrix[2][1] * point[1] + matrix[2][2]))
    py = (matrix[1][0] * point[0] + matrix[1][1] * point[1] + matrix[1][2]) / ((matrix[2][0] * point[0] + matrix[2][1] * point[1] + matrix[2][2]))
    return [px, py]

def generateArucoBoard(dict, markerLength, filename):
    paperWidth, paperHeight = int(8.27 * 300), int(11.69 * 300)
    separation = int(0.3*markerLength)
    # pocet ctvercu na sirku a vysku
    squaresX = int((paperWidth-100) / (markerLength+ separation))
    squaresY = int((paperHeight-100) / (markerLength+ separation))
    print(squaresX, squaresY, markerLength, separation)
    #Vyber slovniku
    dictionary = cv2.aruco.getPredefinedDictionary(dict)
    #Vytvori desku
    board =cv2.aruco.GridBoard((squaresX, squaresY), markerLength, separation, dictionary)
    #Vykresli desku
    img = board.generateImage((int(paperWidth), int(paperHeight)))
    #Ulozi desku
    cv2.imwrite(filename, img)
    return board

def ShowCoordinates(frame, point, origin, prevod, font=font):
    X = point[0]*prevod
    Y = (origin[1] - point[1])*prevod
    point = int(point[0]), int(point[1])
    origin = int(origin[0]), int(origin[1])
    midpointX = ((origin[0] + point[0]) // 2 -20, point[1])
    midpointY = (point[0], (origin[1] + point[1]) // 2)
    cv2.arrowedLine(frame, (0, point[1]), point, (255, 0, 0), thickness=2, tipLength=0.02)
    cv2.arrowedLine(frame, (point[0], hh), point, (255, 0, 0), thickness=2, tipLength=0.02)

    cv2.circle(frame, point, radius=0, color=color, thickness=3)
    #cv2.putText(frame, f'Center', point, cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    cv2.putText(frame, f"{X :.2f}mm", midpointX, font, 0.5, (255, 0, 0), thickness=2)
    cv2.putText(frame, f"{Y :.2f}mm", midpointY, font, 0.5, (255, 0, 0), thickness=2)
def ShowSmallCoordinates(frame,point,origin,prevod):
    X = point[0]*prevod
    Y = (origin[1] - point[1])*prevod
    point = int(point[0]), int(point[1])
    origin = int(origin[0]), int(origin[1])
    cv2.circle(frame, point, radius=0, color=color, thickness=3)
    #cv2.putText(frame, f'Center', point, cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    cv2.putText(frame, f"X:{X :.2f}mm", (point[0],point[1]-40),font, 0.5, (255, 0, 0), thickness=2)
    cv2.putText(frame, f"Y:{Y :.2f}mm", (point[0],point[1]-20),font, 0.5, (255, 0, 0), thickness=2)

def DrawCoordinateSystemSymbol(image):
    image_width, image_height = image.shape[1], image.shape[0]
    padding = 0.04  # Percentage of padding around the image
    arrow_size = 0.05  # Percentage of arrow size relative to image width
    # Compute coordinate system dimensions
    axis_length = int((0.15) * min(image_width, image_height))
    axis_thickness = 2

    arrow_size = 0.1
    arrow_length = int(arrow_size * axis_length)
    arrow_thickness = 2
    # Compute coordinate system positions
    x_axis_start = int(padding * image_width)
    x_axis_end = x_axis_start + axis_length
    y_axis_start = image_height - int(padding * image_height)
    y_axis_end = y_axis_start - axis_length

    # Draw x-axis
    cv2.line(image, (x_axis_start, y_axis_start), (x_axis_end, y_axis_start), (0, 0, 255), axis_thickness)

    # Draw y-axis
    cv2.line(image, (x_axis_start, y_axis_start), (x_axis_start, y_axis_end), (255, 0, 0), axis_thickness)

    # Draw arrowheads for x-axis
    cv2.line(image, (x_axis_end, y_axis_start), (x_axis_end - arrow_length, y_axis_start - arrow_length), (0, 0, 255),
             arrow_thickness)
    cv2.line(image, (x_axis_end, y_axis_start), (x_axis_end - arrow_length, y_axis_start + arrow_length), (0, 0, 255),
             arrow_thickness)

    # Draw arrowheads for y-axis
    cv2.line(image, (x_axis_start, y_axis_end), (x_axis_start - arrow_length, y_axis_end + arrow_length), (255, 0, 0),
             arrow_thickness)
    cv2.line(image, (x_axis_start, y_axis_end), (x_axis_start + arrow_length, y_axis_end + arrow_length), (255, 0, 0),
             arrow_thickness)

    # Add labels
    cv2.putText(image, 'x', (x_axis_end - 3*arrow_length, y_axis_start - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    cv2.putText(image, 'y', (x_axis_start + 10, y_axis_end + 3*arrow_length), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)