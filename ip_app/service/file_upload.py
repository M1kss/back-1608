from wand.image import Image
import hashlib
import time
import hmac
import copy
import os

from werkzeug.utils import secure_filename

# File saver
import ip_app


class FileLoader:
    defaultUploadOptions = {
        "fieldname": "file",
        "validation": {
            "allowedExts": ["txt", "pdf", "doc"],
            "allowedMimeTypes": ["text/plain", "application/msword", "application/x-pdf", "application/pdf"]
        }
    }

    @classmethod
    def upload(cls, req, fileRoute, options=None):
        """
        File upload to disk.
        Parameters:
          req: framework adapter to http request. See BaseAdapter.
          fileRoute: string
          options: dict optional, see defaultUploadOptions attribute
        Return:
          link: str
        """
        if options is None:
            options = cls.defaultUploadOptions
        else:
            options = Utils.merge_dicts(cls.defaultUploadOptions, options)

        # Get extension.
        filename = req.getFilename(options["fieldname"])
        extension = Utils.getExtension(filename)
        extension = "." + extension if extension else ""

        # Generate new random name.
        sha1 = hashlib.sha1(str(time.time()).encode("utf-8")).hexdigest()
        routeFilename = secure_filename(os.path.join(fileRoute, sha1 + extension))

        fullNamePath = os.path.join(Utils.getServerPath(), routeFilename)

        req.saveFile(options["fieldname"], fullNamePath)
        print(fullNamePath)
        # Check validation.
        if "validation" in options:
            if not Utils.isValid(options["validation"], fullNamePath, req.getMimetype(options["fieldname"])):
                FileLoader.delete(routeFilename)
                raise Exception("File does not meet the validation.")

        if "resize" in options and options["resize"] is not None:
            with Image(filename=fullNamePath) as img:
                img.transform(resize=options["resize"])
                img.save(filename=fullNamePath)

        # build and send response.
        return fullNamePath

    @staticmethod
    def delete(src):
        """
        Delete file from disk.
        Parameters:
          src: string
        """

        filePath = Utils.getServerPath() + src
        try:
            os.remove(filePath)
        except OSError:
            pass


class ImageLoader(FileLoader):
    defaultUploadOptions = {
        "fieldname": "file",
        "validation": {
            "allowedExts": ["gif", "jpeg", "jpg", "png", "svg", "blob"],
            "allowedMimeTypes": ["image/gif", "image/jpeg", "image/pjpeg", "image/x-png", "image/png",
                                 "image/svg+xml"]
        },
        # string resize param from http://docs.wand-py.org/en/0.4.3/guide/resizecrop.html#transform-images
        # Examples: "100x100", "100x100!".
        # Find more on http://www.imagemagick.org/script/command-line-processing.php#geometry
        "resize": None
    }


class FlaskAdapter:

    def __init__(self, request):
        self.request = request

    def checkFile(self, fieldname):
        if fieldname not in self.request.files:
            raise Exception("File does not exist.")

    def getFilename(self, fieldname):
        self.checkFile(fieldname)
        return self.request.files[fieldname].filename

    def getMimetype(self, fieldname):
        self.checkFile(fieldname)
        return self.request.files[fieldname].content_type

    def saveFile(self, fieldname, fullNamePath):
        self.checkFile(fieldname)
        file = self.request.files[fieldname]
        file.save(fullNamePath)


class Utils(object):
    @staticmethod
    def hmac(key, string, nobinary=False):
        """
        Calculate hmac.
        Parameters:
         key: string
         string: string
         nobinary: boolean optional, return in hex, else return in binary
        Return:
         string: hmax in hex or binary
        """
        try:
            hmac256 = hmac.new(key.encode() if isinstance(key, str) else key,
                               msg=string.encode("utf-8") if isinstance(string, str) else string,
                               digestmod=hashlib.sha256)  # v3
        except Exception as e:
            raise e
            # hmac256 = hmac.new(key, msg=string, digestmod=hashlib.sha256)  # v2

        return hmac256.hexdigest() if nobinary else hmac256.digest()

    @staticmethod
    def merge_dicts(a, b, path=None):
        """
        Deep merge two dicts without modifying them.
        Source: https://stackoverflow.com/questions/7204805/dictionaries-of-dictionaries-merge/7205107#7205107
        Parameters:
         a: dict
         b: dict
         path: list
        Return:
         dict: Deep merged dict.
        """

        aClone = copy.deepcopy(a)
        # Returns deep b into a without affecting the sources.
        if path is None:
            path = []
        for key in b:
            if key in a:
                if isinstance(a[key], dict) and isinstance(b[key], dict):
                    aClone[key] = Utils.merge_dicts(a[key], b[key], path + [str(key)])
                else:
                    aClone[key] = b[key]
            else:
                aClone[key] = b[key]
        return aClone

    @staticmethod
    def getExtension(filename):
        """
        Get filename extension.
        Parameters:
            filename: string
        Return:
            string: The extension without the dot.
        """
        return os.path.splitext(filename)[1][1:]

    @staticmethod
    def isFileValid(filename, mimetype, allowedExts, allowedMimeTypes):
        """
        Test if a file is valid based on its extension and mime type.
        Parameters:
            filename string
            mimeType string
            allowedExts list
            allowedMimeTypes list
        Return:
            boolean
        """

        # Skip if the allowed extensions or mime types are missing.
        if not allowedExts or not allowedMimeTypes:
            return False

        extension = Utils.getExtension(filename)
        return extension.lower() in allowedExts and mimetype in allowedMimeTypes

    @staticmethod
    def getServerPath():
        """
        Get the path where the server has started.
        Return:
         string: serverPath
        """
        return ip_app.app.config['UPLOAD_FOLDER']

    @staticmethod
    def isValid(validation, filePath, mimetype):
        """
        Generic file validation.
        Parameters:
         validation: dict or function
         filePath: string
         mimetype: string
        """

        # No validation means you dont want to validate, so return affirmative.
        if not validation:
            return True

        # Validation is a function provided by the user.
        if callable(validation):
            return validation(filePath, mimetype)

        if isinstance(validation, dict):
            return Utils.isFileValid(filePath, mimetype, validation["allowedExts"], validation["allowedMimeTypes"])

        # Else: no specific validating behaviour found.
        return False
