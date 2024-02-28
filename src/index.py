from deepface import DeepFace
import os, shutil
from PIL import Image
from datetime import datetime
from PIL import Image
from pillow_heif import register_heif_opener
from mysqlConnector import mysqlConnector
import s3upload
import time
from configs import backends, metrics, models

register_heif_opener()

def emptyFolder(folder):
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print("Failed to delete %s. Reason: %s" % (file_path, e))

    # os.rmdir(folder)


def convert_heif_to_jpeg(heif_file_path):
    image = Image.open(heif_file_path)
    image.convert("RGB").save(heif_file_path + ".jpg")
    os.remove(heif_file_path)
    return heif_file_path + ".jpg"


def resize(file_path, album_id, photo_id):
    im = Image.open(file_path)

    # save thumbs
    width, height = im.size  # Get dimensions
    new_width = height if width > height else width
    new_height = new_width
    left = (width - new_width) / 2
    top = (height - new_height) / 2
    right = (width + new_width) / 2
    bottom = (height + new_height) / 2

    # Crop the center of the image
    im = im.crop((left, top, right, bottom))
    local_path = (
        os.getenv("BUCKET_NAME")
        + "/.thumbs/"
        + album_id
        + '/'
        + str(int(time.time()))
        + str(photo_id)
        + '.jpg'
    )

    mysqlConnector.insert(
        "UPDATE photos set thumb_path = %s WHERE id = %s",
        (local_path, photo_id),
    )

    local_path = (
        os.getenv("DEV_UPLOAD_PATH")
        + "/"
        + local_path
    )

    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    im.save(local_path)

    # Open the original file again
    im = Image.open(file_path)
    size = 2000, 2000

    if (im.width > im.height and im.width > 1000) or (
        im.width < im.height and im.height > 1000
    ):
        im.thumbnail(size, Image.Resampling.LANCZOS)
        im.save(file_path, "JPEG")


def folder_has_files(folder_path):
    # Get a list of items in the folder
    folder_contents = os.listdir(folder_path)

    # Filter out directories, keeping only files
    return (
        len(
            [
                item
                for item in folder_contents
                if os.path.isfile(os.path.join(folder_path, item)) and item[0] != "."
            ]
        )
        > 0
    )


def extract_faces(image, output_dir="output", body={}):
    """
    Extract faces from a given image using DeepFace and save them to separate image files.

    Args:
    image (numpy array): The image from which to extract faces.
    output_dir (str): The directory where the extracted faces will be saved.

    Returns:
    list of numpy arrays: A list of numpy arrays, each containing a single
                          face extracted from the input image.
    """
    # Initialize DeepFace with the 'Facenet' model
    if image.lower().endswith("heic"):
        image = convert_heif_to_jpeg(image)

    resize(image, body["album_id"], body['id'])

    faces = DeepFace.extract_faces(
        image,
        target_size=(500, 500),
        detector_backend=backends[4],
        align=True,
        enforce_detection=False,
    )

    # Extract the faces
    for face in faces:

        if face['confidence'] < 0.9:
            continue

        dfs = []
        x, y, w, h = face["facial_area"].values()

        img = Image.open(image)
        face_img = img.crop((x, y, x + w, y + h))
        if img.width == w and img.height == h:
            continue

        # Save the face to the output folder
        tmp = os.path.join(".temp", f"face_{datetime.now()}.png")
        face_img.save(tmp)

        if folder_has_files(output_dir) == True:

            dfs = DeepFace.find(
                silent=True,
                img_path=tmp,
                db_path=output_dir,
                model_name=models[1],
                detector_backend=backends[4],
                enforce_detection=False,
                distance_metric=metrics[2],
                align=True,
            )
        
        found = False
        for f in dfs:
            if f.empty == False:
                found = True

        # Save the face to the output folder
        face_filename = os.path.join(output_dir, f"face_{datetime.now()}.png")

        # save face to s3
        face_img.save(face_filename)

        s3File = f"{face_filename}"
        s3upload.upload(face_filename, s3File)

        # No occurances found
        if found == False:
            # save people
            people_id = mysqlConnector.insert(
                "INSERT INTO people (album_id, image_path, created_at, updated_at) VALUES (%s, %s, %s, %s)",
                (body["album_id"], s3File, datetime.now(), datetime.now()),
            )

            mysqlConnector.insert(
                "INSERT INTO people_has_faces (people_id, image_path, created_at, updated_at) VALUES (%s, %s, %s, %s)",
                (people_id, s3File, datetime.now(), datetime.now()),
            )

            # save photo has people
            mysqlConnector.insert(
                "INSERT INTO photo_has_people (photo_id, people_id) VALUES (%s, %s)",
                (body["id"], people_id),
            )

        # Occurances found
        else:
            for d in dfs:
                if d.empty == False and d.get("identity").count() > 0:
                    item = d.get('identity')[0]
                    people_has_face = mysqlConnector.findOne(
                        f"SELECT people_id from people_has_faces where image_path = '{item}'",
                    )

                    if people_has_face != None:
                        mysqlConnector.insert(
                            "INSERT INTO people_has_faces (people_id, image_path, created_at, updated_at) VALUES (%s, %s, %s, %s)",
                            (people_has_face['people_id'], s3File, datetime.now(), datetime.now()),
                        )

                        # save photo has people
                        mysqlConnector.insert(
                            "INSERT INTO photo_has_people (people_id, photo_id) VALUES (%s, %s)",
                            (people_has_face['people_id'], body['id']),
                        )
