from flask import Flask, request
from deepface import DeepFace
import os
from mysqlConnector import mysqlConnector
from configs import backends, metrics, models
import time

app = Flask(__name__)

@app.post("/get-match")
def getMatch():
    try:
        album_code = request.form.get("code")

        if album_code == None:
            return {"status": False, "message": "This is not a valid album"}, 412

        album = mysqlConnector.findOne(
            query=f"SELECT album_id from album_links where code = '{album_code}'"
        )

        if album == None:
            return {"status": False, "message": "This is not a valid album"}, 412

        output_dir = f"faces/{str(album['album_id'])}"

        image = request.files.get("image")

        if image == None:
            return {"status": False, "message": "This is not a valid image"}, 412

        os.makedirs(os.path.dirname("./.files/"), exist_ok=True)

        # write image to a file
        tmp = "./.files/" + str(time.time()) + ".jpg"
        image.save(tmp)

        analysis = DeepFace.analyze(tmp, enforce_detection=False, silent=True)
        if len(analysis) == 0:
            raise RuntimeError("Please provide a valid face image!")
        
        if analysis[0] and analysis[0]['face_confidence'] < 1:
            raise RuntimeError("Look into the camera when taking a picture!")

        dfs = DeepFace.find(
            silent=False,
            img_path=tmp,
            db_path=output_dir,
            model_name=models[1],
            detector_backend=backends[4],
            enforce_detection=False,
            distance_metric=metrics[2],
            threshold=0.4,
            align=True,
        )

        if len(dfs) == 0:
            return {"status": False, "message": "No valid faces found"}, 400
        else:
            identities = []
            for d in dfs:
                if d.empty == False and d.get("identity").count() > 0:
                    for item in d.get("identity"):
                        identities.append(item)
            
            if len(identities) <= 0:
                return {"status": False, "message": "No matching faces found!"}, 412

            query = """
                SELECT ph.*
                FROM people_has_faces AS p
                JOIN people as ph on ph.id = p.people_id
                JOIN photo_has_people AS php ON php.people_id = ph.id
                WHERE p.image_path IN (%s)
            """
            # Assuming ids is a list of strings
            placeholders = ",".join(["%s" for _ in identities])
            formatted_query = query % placeholders
            print(formatted_query)
            identities = mysqlConnector.findAll(query=formatted_query, data=identities)


        # removing file
        os.remove(tmp)

        return {"status": True, "message": "", "payload": identities}, 200
    except ValueError as e:
        print(e)
        return {
            "status": False,
            "message": "Cannot match any photos in which you are present",
        }, 412
    except RuntimeError as e:
        print(e)
        return {
            "status": False,
            "message": str(e),
        }, 412
    except Exception as e:
        print(e)
        return {
            "status": False,
            "message": str(e),
        }, 500
