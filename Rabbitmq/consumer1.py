import pika
import time
import random
import psycopg2
import cv2
import numpy as np
import mediapipe as mp
from psycopg2.extras import RealDictCursor

def on_message_received(ch, method, properties, body):
    decoded_body = body.decode('utf-8')
    print(f'received: {decoded_body}')
    fetch_query = f"SELECT * from image WHERE image.id = {decoded_body}"
    cursor.execute(fetch_query)
    data = cursor.fetchall()

    for d in data:
        image_data = d['img']
        i_id = d['id']
        with open(".\\imgs\\temp.jpg",'wb') as file:
            file.write(image_data)
            frame_path = ".\\imgs\\temp.jpg"
            frame = cv2.imread(frame_path)
            #cv2.imshow('Face Mesh', frame)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(frame_rgb)
            if results.multi_face_landmarks:
                for face_landmarks in results.multi_face_landmarks:
                    mp_drawing.draw_landmarks(
                        image=frame,
                        landmark_list=face_landmarks,
                        connections=mp_face_mesh.FACEMESH_TESSELATION,
                        landmark_drawing_spec=None,
                        connection_drawing_spec=mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=1, circle_radius=1),
                    )
            cv2.imshow('Face Mesh', frame)
            cv2.waitKey(1)
            
            frame_bytes = cv2.imencode('.jpg', frame)[1].tobytes()
            update_query = f"UPDATE image set img = {psycopg2.Binary(frame_bytes)} WHERE image.id = {decoded_body}"
            cursor.execute(update_query)
    

    ch.basic_ack(delivery_tag=method.delivery_tag)
    print(f'finished processing and acknowledged message')
    conn.commit()
    

connection_parameters = pika.ConnectionParameters('localhost')

connection = pika.BlockingConnection(connection_parameters)

channel = connection.channel()

channel.queue_declare(queue='job')

channel.basic_qos(prefetch_count=1)

channel.basic_consume(queue='job', on_message_callback=on_message_received)

print('Starting Consuming')




conn = psycopg2.connect(
    host="localhost",
    database="postgres",
    user="postgres",
    password="my_db"
)


mp_drawing = mp.solutions.drawing_utils
mp_face_mesh = mp.solutions.face_mesh 

# Initialize the face mesh model
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=False, max_num_faces=1, min_detection_confidence=0.5)

cursor = conn.cursor(cursor_factory=RealDictCursor)



channel.start_consuming()
face_mesh.close()
cv2.destroyAllWindows()
cursor.close()
conn.close()

