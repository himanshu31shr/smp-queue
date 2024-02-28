#!/usr/bin/env python
import sys, os
import json
from mysqlConnector import mysqlConnector
import requests
from datetime import datetime
import os, shutil
from index import extract_faces, emptyFolder
from dotenv import load_dotenv
import mqClient
import traceback


def _downloadFile(filename, output):
    response = requests.get(filename)
    filePath = os.path.join(".temp", output)
    with open(filePath, "wb") as f:
        f.write(response.content)
    return filePath


def _handleIncomingImage(ch, method, properties, body):
    try:
        body = json.loads(body)
        query = f'SELECT * from albums where id = {body["album_id"]}'
        result = mysqlConnector.findOne(query)

        if result != None:
            print("Data found!")
            fi = f"face_{datetime.now()}{os.path.splitext(body['image_path'])[1]}"
            path = _downloadFile(body["signedUrl"], fi)
            if os.path.exists(f'faces/{body["album_id"]}') == False:
                os.makedirs(f'faces/{body["album_id"]}')
            extract_faces(path, f'faces/{body["album_id"]}', body)
            emptyFolder(".temp")
            print('File processed:', fi)

    except:
        traceback.print_exc()



def _handleCleanupAlbum(ch, method, properties, body):
    try:
        body = json.loads(body)
        folder = f'faces/{body["album_id"]}'

        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print("Failed to delete %s. Reason: %s" % (file_path, e))

        os.remove(folder)
        print(f'Removed {folder}')

    except:
        traceback.print_exc()


def main():

    NUM_THREADS_PER_QUEUE = 1
    QUEUE_CALLBACKS = {
        os.getenv("MQ_CLEANUP_QUEUE"): _handleCleanupAlbum,
        os.getenv("MQ_IMAGE_QUEUE"): _handleIncomingImage,
    }
    mqClient.start_consumer_threads(NUM_THREADS_PER_QUEUE, QUEUE_CALLBACKS)


if __name__ == "__main__":
    try:
        load_dotenv()
        folders = [".temp", "faces"]
        for folder in folders:
            di = os.path.exists(folder)
            if di == False:
                os.mkdir(folder)
        main()
        result = mysqlConnector.findOne('select 1+1 as success from users')
        print(result)

    except KeyboardInterrupt:
        print("Interrupted")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
    except:
        traceback.print_exc()
