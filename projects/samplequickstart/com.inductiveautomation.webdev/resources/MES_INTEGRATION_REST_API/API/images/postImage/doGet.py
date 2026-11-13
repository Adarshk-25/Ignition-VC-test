def doGet(request, session):


    import system
    import base64
    import traceback

    logger = system.util.getLogger("POSTIMAGE")

    try:

        logger.info(
            "POST Image API Called"
        )

        # Get request payload safely
        data = request.get("data", {})

        logger.info(
            "Payload received"
        )

        # Read fields safely
        machineId = str(
            data.get("machineId", "")
        ).strip()

        imageName = str(
            data.get("imageName", "")
        ).strip()

        imageType = str(
            data.get("imageType", "")
        ).strip()

        createdAt = str(
            data.get("createdAt", "")
        ).strip()

        imageBase64 = str(
            data.get("imageData", "")
        ).strip()

        logger.info(
            "machineId = %s , imageName = %s" %
            (machineId, imageName)
        )

        # Validation
        missingFields = []

        if machineId == "":
            missingFields.append("machineId")

        if imageName == "":
            missingFields.append("imageName")

        if imageType == "":
            missingFields.append("imageType")

        if createdAt == "":
            missingFields.append("createdAt")

        if imageBase64 == "":
            missingFields.append("imageData")

        if len(missingFields) > 0:

            logger.warn(
                "Missing fields : %s" %
                str(missingFields)
            )

            return {

                "json": {

                    "status": "error",

                    "message":
                        "Missing required fields",

                    "missingFields":
                        missingFields

                }

            }

        # Decode Base64 Image
        logger.info(
            "Decoding Base64 image"
        )

        try:

            imageBytes = base64.b64decode(
                imageBase64
            )

        except Exception as decodeError:

            logger.error(
                "Invalid Base64 image"
            )

            return {

                "json": {

                    "status": "error",

                    "message":
                        "Invalid Base64 image data"

                }

            }

        # SQL Query
        query = """
        INSERT INTO Images
        (
            machineId,
            imageName,
            imageData,
            imageType,
            createdAt
        )
        VALUES
        (
            ?, ?, ?, ?, ?
        )
        """

        logger.info(
            "Executing SQL Insert"
        )

        # Execute Insert
        rowsAffected = system.db.runPrepUpdate(
            query,
            [
                machineId,
                imageName,
                imageBytes,
                imageType,
                createdAt
            ],
            "Dev_MSSQL_Server"
        )

        logger.info(
            "Rows Inserted = %s" %
            str(rowsAffected)
        )

        # Success response
        response = {

            "status": "success",

            "message":
                "Image stored successfully",

            "machineId":
                machineId,

            "imageName":
                imageName,

            "rowsAffected":
                rowsAffected

        }

        logger.info(
            "Returning success response"
        )

        # IMPORTANT FOR WEBDEV
        return {

            "json": response

        }

    except Exception as e:

        logger.error(
            traceback.format_exc()
        )

        return {

            "json": {

                "status": "error",

                "message":
                    str(e)

            }

        }