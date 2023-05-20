import pika
import time
import random
import cv2
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import ffmpeg


client_connection_parameters = pika.ConnectionParameters('localhost')
client_connection = pika.BlockingConnection(client_connection_parameters)
client_channel = client_connection.channel()
#client_channel.queue_declare(queue='clientQueue')

def on_client_message(ch, method, properties, body):
    print("Received Message: ", body.decode())
    connection_parameters = pika.ConnectionParameters('localhost', heartbeat = 0)

    connection = pika.BlockingConnection(connection_parameters)

    channel = connection.channel()

    job_queue = channel.queue_declare(queue='job')

    messageId = 1

    conn = psycopg2.connect(
        host="localhost",
        database="postgres",
        user="postgres",
        password="my_db"
    )

    # Create a cursor object
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("DELETE FROM image")

    video_path = "C:\\Users\\HP\\OneDrive\\Desktop\\Shared_Video\\Test.mp4"
    video_capture = cv2.VideoCapture(video_path)

    frame_count = 0  # Initialize frame counter

    while True:
        success, frame = video_capture.read()  # Read the next frame

        if not success: 
            print("End of video or Video not found") # If the video has ended or cannot be read, break the loop
            break

        frame_count += 1  # Increment the frame counter

        # Convert the frame to binary format
        frame_bytes = cv2.imencode('.jpg', frame)[1].tobytes()

        # Insert the frame into the database
        insert_query = f"INSERT INTO image (id, img) VALUES ({frame_count}, {psycopg2.Binary(frame_bytes)})"
        cursor.execute(insert_query)
        conn.commit()
        job_id = str(frame_count) 

        channel.basic_publish(exchange='', routing_key='job', body=job_id)

        print(f"sent job id: {job_id}")
        
        #time.sleep(random.randint(1, 4))

        # Optionally, you can display the frames as well
        # cv2.imshow('Frame', frame)
        # if cv2.waitKey(1) & 0xFF == ord('q'):
        #     break

    # Release the video capture and close any open windows
    video_capture.release()
    cv2.destroyAllWindows()

    job_done = False
    while not job_done:
        job_queue = channel.queue_declare(queue='job')
        if(job_queue.method.message_count == 0):
            print("Job Done")
            job_done = True
            time.sleep(2)
        else:
            print("Still Working Will Check After 10 Secs")
            print("Message in queue: ", job_queue.method.message_count)
            time.sleep(10)
    
    fetch_query = "SELECT * FROM image"
    cursor.execute(fetch_query)
    data = cursor.fetchall()
    frame_count = 0

    for d in data:
        image_data = d['img']
        i_id = d['id']
        #print(type(image_data))
        file_path = f".\\mesh\\mesh_{i_id}.jpg"
        
        with open(file_path, "wb") as file:
            file.write(image_data)
        
        frame_count += 1

    fourcc = cv2.VideoWriter_fourcc(*"H264")
    output_file = "C:\\Users\HP\\OneDrive\\Desktop\\Video Upload\\video_upload\\src\\assets\\output_video.mp4"
    image = cv2.imread('.\\mesh\\mesh_1.jpg')
    height, width = image.shape[:2]
    video_writer = cv2.VideoWriter(output_file, fourcc, 30, (width, height))
    print("Creating Video")
    for i in range (1, frame_count + 1):
        frame_path = f".\\mesh\\mesh_{i}.jpg"  # Path to the frame
        frame = cv2.imread(frame_path)
        video_writer.write(frame)
        #cv2.imshow('Face Mesh', frame)
        #cv2.waitKey(1)
        # Specify the codec
    video_writer.release()

    
    print("Video Created")
    fetch_time = "SELECT * FROM worker"
    cursor.execute(fetch_time)
    data = cursor.fetchall()
    message = {
        "worker1" : data[0]['time'],
        "worker2" : data[1]['time']
    }
    message = json.dumps(message)
    cursor.close()
    channel.queue_declare(queue='masterQueue')
    channel.basic_publish(exchange='', routing_key='masterQueue', body = message)
    print("Message sent to backend")
    conn.close()
    channel.close()
    connection.close()


client_channel.basic_consume(queue='clientQueue', auto_ack = True,on_message_callback=on_client_message)
print("Starting Client Consume")

client_channel.start_consuming()