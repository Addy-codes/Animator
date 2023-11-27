from flask import Flask, render_template, request, redirect, url_for, jsonify
import requests
import time
import os
from google.cloud import storage
from werkzeug.utils import secure_filename
import tempfile

app = Flask(__name__)

# Replace with your Meshy API key
MESHY_API_KEY = 'msy_GMasRRdOXAdcBT6rfnSGfV2aEuLoaAlabqkQ'

BASE_PATH = os.getcwd()
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}

# Initialize Google Cloud Storage client
os.environ[
    "GOOGLE_APPLICATION_CREDENTIALS"
] = f"{BASE_PATH}/key/clever-obelisk-402805-a6790dbab289.json"
storage_client = storage.Client()
bucket_name = "threed-model"
bucket = storage_client.get_bucket(bucket_name)

def upload_to_gcs(file, folder_name):
    filename = secure_filename(file.filename)
    folder_name = "".join(folder_name.split())
    blob = bucket.blob(f"{folder_name}/{filename}")

    # Create a temporary file
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, filename)
    file.save(temp_path)

    # Upload the file
    blob.upload_from_filename(temp_path)

    # Optionally, make the blob publicly accessible
    blob.make_public()

    # Delete the temporary file
    os.remove(temp_path)

    return blob.public_url

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return redirect(request.url)

    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)

    if file and allowed_file(file.filename):  # Implement 'allowed_file' to check file extensions
        image_url = upload_to_gcs(file, "Uploaded_images")
        print(image_url)

        payload = {
            "image_url": image_url,
            "enable_pbr": True
        }
        headers = {
            "Authorization": f"Bearer {MESHY_API_KEY}"
        }

        print("Sending Image to API")

        # First, create the 3D task
        response = requests.post(
            "https://api.meshy.ai/v1/image-to-3d",
            headers=headers,
            json=payload
        )
        response.raise_for_status()

        task_id = response.json().get('result')

        print("Task ID: ",task_id)

        # Now, periodically check the status of the task
        while True:
            task_response = requests.get(
                f"https://api.meshy.ai/v1/image-to-3d/{task_id}",
                headers=headers
            )
            task_response.raise_for_status()
            task_data = task_response.json()

            # task_data = {'id': '018c011c-def2-7e02-80e8-6d9b3b3b71bf', 'name': '', 'art_style': '', 'object_prompt': '', 'style_prompt': '', 'negative_prompt': '', 'status': 'SUCCEEDED', 'created_at': 1700825718523, 'progress': 100, 'started_at': 1700825746216, 'finished_at': 1700825835934, 'expires_at': 1701085035934, 'task_error': None, 'model_url': 'https://assets.meshy.ai/google-oauth2%7C114462251513498782179/tasks/018c011c-def2-7e02-80e8-6d9b3b3b71bf/output/model.glb?Expires=1701085035&Signature=lSDznXTVL9p3HeoKx5OGHhXBqyAaS~~q39uia7O829Y3WN5vzEthxO3xf7Kr9-1evfDM2DZtxDBIppnAYiLkWl5fg4uxE-t0kY97ln8M3nFGnA01vZkqn6S8peubUpK6EdgwYCtH4EnrJJC3Xs3I~MK9sS8NrpeF2FW7LpCmEIQcS5opfNCcSfCAm0uWWs2L56Z2fklmtBjHkQp~AFZNaYda0B8MEZerLn-Giy1~u0Kils6p4vXxu9wpU1SQkVMu3In-B-ZrZDL-BNDic7RC2WOfiolT7SAOTOF8p8s0Y5KLk0ibU~ZFy~uNUMRahn2YyLU5GwbMGmjRb9NaJlskNw__&Key-Pair-Id=KL5I0C8H7HX83', 'model_urls': {'glb': 'https://assets.meshy.ai/google-oauth2%7C114462251513498782179/tasks/018c011c-def2-7e02-80e8-6d9b3b3b71bf/output/model.glb?Expires=1701085035&Signature=lSDznXTVL9p3HeoKx5OGHhXBqyAaS~~q39uia7O829Y3WN5vzEthxO3xf7Kr9-1evfDM2DZtxDBIppnAYiLkWl5fg4uxE-t0kY97ln8M3nFGnA01vZkqn6S8peubUpK6EdgwYCtH4EnrJJC3Xs3I~MK9sS8NrpeF2FW7LpCmEIQcS5opfNCcSfCAm0uWWs2L56Z2fklmtBjHkQp~AFZNaYda0B8MEZerLn-Giy1~u0Kils6p4vXxu9wpU1SQkVMu3In-B-ZrZDL-BNDic7RC2WOfiolT7SAOTOF8p8s0Y5KLk0ibU~ZFy~uNUMRahn2YyLU5GwbMGmjRb9NaJlskNw__&Key-Pair-Id=KL5I0C8H7HX83', 'fbx': 'https://assets.meshy.ai/google-oauth2%7C114462251513498782179/tasks/018c011c-def2-7e02-80e8-6d9b3b3b71bf/output/model.fbx?Expires=1701085035&Signature=rBU6B4vtwiEbsXI6Y4SbKvmy013poW6nTLJaa0lbuJRv832zJHnXznem5i3whJC39g3gKSw4qJ19d3ojM7xBM25COH0EHbPZluNt9Bm1bPisX8K4KsWRe2VQPhoeX-fe0xkfkMUsTfhg-qiAoGrPk8z4ZWicbbIX-awE2Vq~MUsYyFwGUtgvAQDaPTW~-lo-bmocBf3o5eFb7uz3PitoEqlFJJP1WL1zF-0nCoJei-bxR9SIRaF9tFU9gAcTOfF6FQvqVSREPdy6SzsK~p5zXnyj3SxFrQevMhSCXWaNXw85i5snPHithFy13~3bVIC2TN~AjZIrhMNo1ujv3zG~YA__&Key-Pair-Id=KL5I0C8H7HX83', 'usdz': 'https://assets.meshy.ai/google-oauth2%7C114462251513498782179/tasks/018c011c-def2-7e02-80e8-6d9b3b3b71bf/output/model.usdz?Expires=1701085035&Signature=k9nfxQoKRDP82Yrp2~acaXF~IZASnskwWLw5nU9xVM1dQpSzAE~vDRNXTz38tpDWPmGLe5ikG0UhEkW0L3ENu5eSrNrD~wI-UZxAa-vfqWLdC0iafwzAmb53738IucjKi-5hYNM2C3Q79pzGDJRHp-Lxl-BQhLlvQSwvapkAC6uvrmVx4wTNXEoiDAg0Rw0MTCtDab3Zhi6BLhlUt-8qacOZuC9KmqzijSiyyx2AA9qQ8tOhfidugWOgI-tyVFmk~~xTryHL-FhPkDyoksRKLV4xzehjzwQ0P1jMyhh5ape3ddKxwblmF9lDniiU1t9lA5h-3klP4uxUymVcpwOreA__&Key-Pair-Id=KL5I0C8H7HX83'}, 'thumbnail_url': 'https://assets.meshy.ai/google-oauth2%7C114462251513498782179/tasks/018c011c-def2-7e02-80e8-6d9b3b3b71bf/output/preview.png?Expires=1701085035&Signature=eDMwIXHyOImXziv2HsN5~h1izxQXLl1LcJ2gmGVTyu7omxpDOs-Cmfy~cQAC~gJtUFQ4BLU7pwugRzXD0QO0~toAOT8dyJJtbZ-hGQSlCukPnsWfyEz5l4mQLTqw~-d0lpT8CKWqaXPXawKOK6vz-2nsWQdlR6gZJfTFQ88iYz4i8DjPeAo8v3vbMxbwz0ImBc3WeXsk9R22GbwLFuv1BL0u9XOQdC9vM6LIXyotXLhZE0LXtvdlSnxcdlkYzRSfgQlSzY7wP0IhPLgRFPXAS4r44Oa~4oDqWecl25sWz07-DvvbzUmcWrJ2NtvCM~u12GnQSI0KDUgsD2Zx765TSA__&Key-Pair-Id=KL5I0C8H7HX83', 'texture_urls': [{'base_color': 'https://assets.meshy.ai/google-oauth2%7C114462251513498782179/tasks/018c011c-def2-7e02-80e8-6d9b3b3b71bf/output/texture_0.png?Expires=1701085035&Signature=hlIEMIcpiNdO8gvqWd-uPWy42cEz16lkwJrFb3YKsP6ebmwDBwCw2yislFWmdqzBMhV1vV1cPJq~c1GFCuFRB21f0uJ9HnwSw3He0gW5sKkq2vyRTJZJy76wUM-GJrVhuhmC44pmqk5FnD-dxn3z06aTwwNIMLBRf1EZNiZL7hKOSPYiljXsYNvh5MYePW5-S3n0zPPPnVOjRG4YJldrj5sK3iLBbW-A8-3x9I9MfACtxGvO7igbWv7GGRk40QrVKdG7p9nDD6PiC2ky3bKriGn5H0DDh8lyQfYtoNXKvb2bCloyGJtsqNvONWITsJwxROy7LXvuT8DV5dT-42cIoQ__&Key-Pair-Id=KL5I0C8H7HX83', 'metallic': 'https://assets.meshy.ai/google-oauth2%7C114462251513498782179/tasks/018c011c-def2-7e02-80e8-6d9b3b3b71bf/output/texture_0_metallic.png?Expires=1701085035&Signature=UfbQzRGTnhyON5ImhMrk6ucKTYIUJGdxagBzL~~twDhkupa56-PezYc7NrpOFAk-9Q-1VI9TvE2n2ylV2bXcIZYp6aSnXHtUDl-9v6gHZ~9yIhFBwygeLh2k0BiDrcx3Pe8Y5V1GJxX8wcmD8zp-bGVg34IFFVdyiW9FbPF5YHbUQs0m~3rHZIRP9GBnAx2Hug4VrtWeZLoH7RxH~ZmHf9Qqw5gX4KJAH5itocxzQImQBmgcXu9-FrtzUFUSNL4JKhKacHvOOKCW1kAeFbzzLVS7FZJkiqvg~LO~JDoWHIDW2wXqVgAXqhaDFb5DVoeFABlUHHu2EFssZblQrDCcmQ__&Key-Pair-Id=KL5I0C8H7HX83', 'roughness': 'https://assets.meshy.ai/google-oauth2%7C114462251513498782179/tasks/018c011c-def2-7e02-80e8-6d9b3b3b71bf/output/texture_0_roughness.png?Expires=1701085035&Signature=jAe5RHpg9ZZoXS~V~Xz~O03Q68X9XalyzRcn-x11YpAsTYYOfaRLOix1Et4~HTv2i30vtbGIVrjY-eYEChKBIy-fTQsk6CRVON3l0n3loRia7TLa39zddLVipIRrpbNpK2Vv-nW6qFVkaNop03QS0SjHo1KQWYCMRQlwhdyxPtmPc6mrd6apiShB5ZDGLeyne3Ki1an4boh1kFPnimVaxh3X5RmOs3pUEYCqa98SN5uyBVeUVBDrBrOnL688TJIlldxBgimDc-RNzLcGUIGJunPFCKSjp8qyBcB8O6b5baOmrCJHwsZQi-Xnuc2XDqYiopY5q7TXL144rEDxvJy~4Q__&Key-Pair-Id=KL5I0C8H7HX83', 'normal': 'https://assets.meshy.ai/google-oauth2%7C114462251513498782179/tasks/018c011c-def2-7e02-80e8-6d9b3b3b71bf/output/texture_0_normal.png?Expires=1701085035&Signature=mjXJICDPnnm77mKzWmilEgIazDULTuuaNtVkxE5YL9ocO4ISiMES9r-JE70~bBeeHPyu6O0mXNxiU2k-7shfkWNCnWv3vDRa3Fr45wByaZQzNLEbJGBrFGZhO~TdJgiahtZA5Di7VHb1qMJcoby~ZXPpxlL~daTr~pljNym4nks~h~BoPIak5sQ8GP8MvCXBkP6iV0UpXGHqkjWEKmQLgikMtM5hc1CeJ8WvryExRksLbd3lF991iejyUQXQu1hqVhd94Bj6RCTxAgU44wfJjTKSq3G2Xgq5wQHUhW3I0XsAnNI9cdzKXjXCmZW3adEmS84NNIwlwf0R0lfvNDb0cQ__&Key-Pair-Id=KL5I0C8H7HX83'}]}


            print("Attempting")

            if task_data['status'] == 'SUCCEEDED':
                model_url = task_data['model_urls']['glb']  # Example, using the GLB format
                print(task_data)
                return render_template('download.html', model_url=model_url)
            elif task_data['status'] == 'FAILED':
                return "3D model generation failed", 500

            time.sleep(5)  # Adjust the sleep time as needed

    return "Invalid request", 400

if __name__ == '__main__':
    app.run(debug=True)
