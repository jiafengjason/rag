import asyncio
import os
from multiprocessing.managers import BaseManager
from flask import Flask, request
from werkzeug.utils import secure_filename

app = Flask(__name__)

manager = BaseManager(('', 5602), b'password')
manager.register('query_index')
manager.register('insert_into_index')
manager.connect()

@app.route("/")
def home():
    return "Hello World!"

@app.route("/query", methods=["GET"])
def query_index():
    query_text = request.args.get("text", None)
    if query_text is None:
        return "No text found, please include a ?text=blah parameter in the URL", 400
    response = manager.query_index(query_text)._getvalue()
    return str(response), 200

@app.route("/uploadFile", methods=["POST"])
def upload_file():
    if 'file' not in request.files:
        return "Please send a POST request with a file", 400

    filepath = None
    try:
        uploaded_file = request.files["file"]
        filename = os.path.basename(uploaded_file.filename)
        filepath = os.path.join('data', filename)
        uploaded_file.save(filepath)

        if request.form.get("filename_as_doc_id", None) is not None:
            manager.insert_into_index(filepath, doc_id=filename)
        else:
            manager.insert_into_index(filepath)
    except Exception as e:
        return "Error: {}".format(str(e)), 500

    return "File inserted!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5601)
    #asyncio.run(main())
